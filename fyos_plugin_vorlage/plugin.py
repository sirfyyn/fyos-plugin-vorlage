"""vorlage — Muster für ein Hub-Plugin mit Werkzeugen und Oberfläche.

Werkzeuge:
    vorlage.hallo         lesend    Begrüßung und die gespeicherte Notiz; öffnet die App
    vorlage.notiz_setzen  schreibend  Notiz speichern (ersetzt die bisherige); mit Trockenlauf,
                          der echte Lauf nur mit `bestaetigt: true`

Was hier zu sehen ist (und in docs/ERWEITERN.md der Distribution erklärt wird):

  * Konfiguration: Plugin-`config:` vor Umgebung vor Vorgabe (`begruessung`, `notiz_max`); ein Geheimnis kommt
    nur aus der Umgebung (`FYOS_VORLAGE_TOKEN`, im Hub über `secrets:` eingetragen) und wird nie ausgegeben.
  * Eingaben prüft das Plugin selbst. Ein `ValueError` heißt für den Hub „falsches Argument“ (kind
    `bad_arguments`, HTTP 400) und zählt nicht gegen den Schutzschalter; alles andere ist ein Ausfall.
  * Trockenlauf: `__dry_run__: true` in den Argumenten liefert den Plan, ohne etwas zu ändern.
  * Anfrage statt Aktion: Ein echter Lauf von `notiz_setzen` braucht zusätzlich `bestaetigt: true`. Die App stellt
    dafür eine Anfrage (Plan zeigen, Rückfrage, erst nach „Ja“ der echte Lauf); ein Skript gibt die Bestätigung
    ausdrücklich. Das schützt vor Versehen und ersetzt keine Berechtigung (ERWEITERN.md §3.6).
  * Oberfläche: `describe_resources` liefert `ui/vorlage.html`; Name, Symbol und Farbton stehen in der
    Anmeldung der App (`registriere_app`). Die Shell zeigt sie dann von selbst als Fenster und Kachel.

Die Notiz liegt in `mcp_hub.kv` (Redis, wenn `REDIS_URL` gesetzt ist, sonst im Speicher des Prozesses).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from mcp_hub import kv
from mcp_hub.plugin import HubPlugin, ResourceDescriptor, ToolDescriptor, build_dry_run_result, is_dry_run
from mcp_hub.plugins import _identitaet
from mcp_hub.plugins._identitaet import identitaet
from mcp_hub.plugins._oberflaeche import oberflaeche

UI_URI = "ui://vorlage/vorlage.html"
UI_DATEI = "vorlage.html"
SCHLUESSEL = "fyos:vorlage:notiz"
NAME_MAX = 60
VORGABE_BEGRUESSUNG = "Hallo"
VORGABE_NOTIZ_MAX = 280

# Die App anmelden: Titel, Untertitel, Symbol (Lucide-Name aus ui/_symbole.json des Hubs), Farbton 0-359, Kategorie.
_identitaet.registriere_app(
    "vorlage",
    {
        "titel": "Vorlage",
        "untertitel": "Begrüßung und eine Notiz, Muster für eigene Plugins",
        "symbol": "puzzle",
        "ton": 150,
        "kategorie": "Beispiele",
    },
    datei=UI_DATEI,
    hauptwerkzeug="vorlage__hallo",
)


class VorlagePlugin(HubPlugin):
    name = "vorlage"
    description = "Vorlage: Begrüßung und eine Notiz mit kleiner Oberfläche (zeigt, wie ein Plugin gebaut ist)."
    version = "0.1.0"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__()
        self.config = dict(config or {})
        self._r: Any = None  # Tests setzen einen Speicher-Ersatz

    # ── Konfiguration (config: vor Umgebung vor Vorgabe) ─────────────────────
    def _wert(self, schluessel: str, umgebung: str, vorgabe: str) -> str:
        return str(self.config.get(schluessel) or os.getenv(umgebung) or vorgabe)

    @property
    def begruessung(self) -> str:
        return self._wert("begruessung", "FYOS_VORLAGE_BEGRUESSUNG", VORGABE_BEGRUESSUNG).strip() or VORGABE_BEGRUESSUNG

    @property
    def notiz_max(self) -> int:
        try:
            n = int(self._wert("notiz_max", "FYOS_VORLAGE_NOTIZ_MAX", str(VORGABE_NOTIZ_MAX)))
        except ValueError:
            return VORGABE_NOTIZ_MAX
        return n if 1 <= n <= 5000 else VORGABE_NOTIZ_MAX

    def redis(self) -> Any:
        return self._r if self._r is not None else kv.klient()

    # ── Lebenslauf ───────────────────────────────────────────────────────────
    def register(self) -> None:
        # Einmal beim Start. Nur Leichtes: Verbindungen aufbauen, nicht auf andere Dienste warten.
        return None

    def health(self) -> dict[str, Any]:
        # Das Geheimnis selbst steht nie in der Antwort, nur ob es da ist.
        return {"ok": True, "status": "healthy", "token": bool(os.getenv("FYOS_VORLAGE_TOKEN"))}

    def shutdown(self) -> None:
        return None

    # ── Daten ────────────────────────────────────────────────────────────────
    def _lesen(self) -> dict[str, Any] | None:
        roh = self.redis().get(SCHLUESSEL)
        try:
            daten = json.loads(roh) if roh else None
        except ValueError:
            return None
        return daten if isinstance(daten, dict) and isinstance(daten.get("text"), str) else None

    # ── Beschreibung ─────────────────────────────────────────────────────────
    @staticmethod
    def _meta() -> dict[str, Any]:
        # `ui.resourceUri` verbindet das Werkzeug mit der Oberfläche; `app` ist ihre Identität.
        return {"ui": {"resourceUri": UI_URI}, "app": identitaet("vorlage")}

    def describe_tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="hallo",
                title="Vorlage",
                description=(
                    "Begrüßt mit dem eingestellten Gruß und zeigt die gespeicherte Notiz; öffnet die Vorlage-App. "
                    "`name` ist optional. Nur lesend."
                ),
                input_schema={
                    "type": "object",
                    "properties": {"name": {"type": "string", "maxLength": NAME_MAX, "description": "Wen begrüßen (optional)"}},
                    "additionalProperties": False,
                },
                tags=["vorlage", "read", "flaeche"],
                meta=self._meta(),
            ),
            ToolDescriptor(
                name="notiz_setzen",
                title="Notiz setzen",
                description=(
                    "Speichert eine kurze Notiz und ersetzt die bisherige. Schreibend, aber umkehrbar (neu setzen). "
                    "Mit `__dry_run__: true` kommt nur der Plan zurück; ein echter Lauf braucht `bestaetigt: true`."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "minLength": 1, "description": "Die Notiz (bis `notiz_max` Zeichen)"},
                        "bestaetigt": {
                            "type": "boolean",
                            "description": "Echter Lauf: vorher den Plan (`__dry_run__`) ansehen und bestätigen lassen",
                        },
                    },
                    "required": ["text"],
                    "additionalProperties": False,
                },
                tags=["vorlage", "write", "flaeche"],
                meta=self._meta(),
            ),
        ]

    def describe_resources(self) -> list[ResourceDescriptor]:
        return [
            ResourceDescriptor(
                uri=UI_URI,
                name="Vorlage",
                description="Begrüßung und Notiz der Vorlage",
                # Das UI-Verzeichnis ist `<Paket>/ui/`; `__package__` ist der Paketname und übersteht ein Umbenennen.
                read=lambda: oberflaeche(UI_DATEI, __package__),
                meta={"ui": {"prefersBorder": True}},
            )
        ]

    # ── Aufrufe ──────────────────────────────────────────────────────────────
    def call(self, method: str, args: dict[str, Any]) -> Any:
        args = args or {}
        if method == "hallo":
            return self.hallo(args.get("name"))
        if method == "notiz_setzen":
            return self.notiz_setzen(args.get("text"), trocken=is_dry_run(args), bestaetigt=args.get("bestaetigt") is True)
        raise ValueError(f"vorlage hat kein Werkzeug {method!r}")

    def hallo(self, name: Any = None) -> dict[str, Any]:
        if name is None or name == "":
            name = "du"
        if not isinstance(name, str):
            raise ValueError("name muss ein Text sein")
        name = " ".join(name.split())
        if len(name) > NAME_MAX:
            raise ValueError(f"name ist zu lang (höchstens {NAME_MAX} Zeichen)")
        notiz = self._lesen()
        return {
            "satz": f"{self.begruessung}, {name}!",
            "begruessung": self.begruessung,
            "name": name,
            "notiz": notiz["text"] if notiz else None,
            "gesetzt_am": notiz.get("zeit") if notiz else None,
            "notiz_max": self.notiz_max,
            "zeit": int(time.time()),
        }

    def notiz_setzen(self, text: Any, trocken: bool = False, bestaetigt: bool = False) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text fehlt")
        text = text.strip()
        if len(text) > self.notiz_max:
            raise ValueError(f"text ist zu lang ({len(text)} Zeichen, höchstens {self.notiz_max})")
        if trocken:
            alt = self._lesen()
            return build_dry_run_result(
                would_execute=f"Notiz mit {len(text)} Zeichen speichern" + (" und die bisherige ersetzen" if alt else ""),
                expected_side_effects=[f"{SCHLUESSEL}: {'ersetzt' if alt else 'neu angelegt'}"],
                estimated_cost=1,
                plugin=self.name,
                method="notiz_setzen",
                args_preview={"text": text[:40]},
            )
        if not bestaetigt:
            # Anfrage statt Aktion: geschrieben wird nur, was jemand als Plan gesehen und bestätigt hat.
            raise ValueError(
                "Nichts geändert: ein echter Lauf braucht bestaetigt: true — erst mit __dry_run__ den Plan ansehen "
                "und bestätigen lassen."
            )
        zeit = int(time.time())
        self.redis().set(SCHLUESSEL, json.dumps({"text": text, "zeit": zeit}, ensure_ascii=False))
        return {"ok": True, "satz": "Notiz gespeichert.", "notiz": text, "gesetzt_am": zeit}
