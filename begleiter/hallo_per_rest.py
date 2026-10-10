#!/usr/bin/env python3
"""Begleitskript: ein Hub-Werkzeug von außen aufrufen (zum Beispiel von einem Mac oder einem Server aus).

Zeigt den Weg, den jedes Begleitskript nimmt: ein POST an `/hub/call` des Hubs im eigenen Netz. Der Weg ist nur
innen offen, nie aus dem Internet (siehe docs/HUB-VERTRAG.md). Das Skript braucht nur die Standardbibliothek.

    python3 begleiter/hallo_per_rest.py --hub http://localhost:8080 --name Alex
    python3 begleiter/hallo_per_rest.py --hub http://localhost:8080 --notiz "Milch kaufen"        # zeigt nur den Plan
    python3 begleiter/hallo_per_rest.py --hub http://localhost:8080 --notiz "Milch kaufen" --ja   # speichert wirklich

Auch das Skript stellt eine Anfrage statt einer Aktion: `vorlage.notiz_setzen` ändert nur mit `bestaetigt: true` etwas,
und das setzt das Skript erst auf ausdrückliches `--ja`. Ohne `--ja` zeigt es den Plan (Trockenlauf).

Die Adresse des Hubs steht in der Umgebung (`FYOS_HUB_BASIS`) oder in `--hub`, nie im Skript. Zugangsdaten gehören
nicht in dieses Repo, sondern in eine Datei außerhalb (Rechte 600) oder in die Umgebung.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Any


def anfrage_bauen(hub: str, werkzeug: str, argumente: dict[str, Any]) -> urllib.request.Request:
    """Die Anfrage an `/hub/call`; ohne Netz prüfbar."""
    if not hub.startswith(("http://", "https://")):
        raise ValueError("hub muss mit http:// oder https:// beginnen")
    return urllib.request.Request(
        hub.rstrip("/") + "/hub/call",
        data=json.dumps({"tool": werkzeug, "arguments": argumente}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Hub-Caller": "begleiter-vorlage"},
        method="POST",
    )


def notiz_argumente(text: str, ja: bool = False) -> dict[str, Any]:
    """Argumente für `vorlage.notiz_setzen`: ohne `ja` der Trockenlauf (der Plan), erst mit `ja` der echte Lauf."""
    return {"text": text, "bestaetigt": True} if ja else {"text": text, "__dry_run__": True}


def aufrufen(hub: str, werkzeug: str, argumente: dict[str, Any], frist_s: float = 10.0) -> dict[str, Any]:
    with urllib.request.urlopen(anfrage_bauen(hub, werkzeug, argumente), timeout=frist_s) as antwort:  # noqa: S310
        return json.loads(antwort.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--hub", default=os.getenv("FYOS_HUB_BASIS", ""), help="Adresse des Hubs, z. B. http://localhost:8080")
    p.add_argument("--name", default="", help="wen begrüßen")
    p.add_argument("--notiz", default="", help="Notiz speichern")
    p.add_argument("--trocken", action="store_true", help="bei --notiz nur den Plan zeigen (ohne --ja ohnehin so)")
    p.add_argument("--ja", action="store_true", help="bei --notiz wirklich speichern (bestaetigt: true)")
    a = p.parse_args(argv)
    if a.ja and a.trocken:
        p.error("--ja und --trocken schließen sich aus")
    if not a.hub:
        print("Adresse des Hubs fehlt (--hub oder FYOS_HUB_BASIS)", file=sys.stderr)
        return 2
    if a.notiz:
        ergebnis = aufrufen(a.hub, "vorlage.notiz_setzen", notiz_argumente(a.notiz, a.ja))
        if not a.ja and ergebnis.get("ok"):
            print("Nichts gespeichert, das war der Plan. Zum Speichern --ja anhängen.", file=sys.stderr)
    else:
        ergebnis = aufrufen(a.hub, "vorlage.hallo", {"name": a.name} if a.name else {})
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    return 0 if ergebnis.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
