#!/usr/bin/env python3
"""Benennt die Vorlage in dein Plugin um.

    python3 umbenennen.py wetter            # Paket fyos_plugin_wetter, Plugin und Werkzeuge wetter.*
    python3 umbenennen.py wetter --trocken  # nur zeigen, was sich ändern würde

Ersetzt in allen Textdateien und in den Datei- und Ordnernamen:

    fyos-plugin-vorlage   ->  fyos-plugin-<name>   (Paketname auf PyPI/Git; Unterstriche werden zu Bindestrichen)
    fyos_plugin_vorlage   ->  fyos_plugin_<name>   (Python-Paket)
    FYOS_VORLAGE          ->  FYOS_<NAME>          (Umgebungsvariablen)
    VorlagePlugin         ->  <Name>Plugin         (Klasse)
    Vorlage               ->  <Name>               (Titel; bei Unterstrichen mit Leerzeichen)
    vorlage               ->  <name>               (Plugin-Name, Werkzeug-IDs, ui://, Skill, Katalog-ID)

`<name>`: Kleinbuchstaben, Ziffern und Unterstriche, beginnt mit einem Buchstaben (zum Beispiel `wetter` oder
`haus_licht`). Er wird zum Präfix aller Werkzeuge (`wetter.hallo`) und zum Namen der App (`wetter__hallo`).
Danach die Beschreibungstexte (pyproject, Katalog, README, Skill) von Hand an dein Plugin anpassen.

Nur die Standardbibliothek. Das Skript ändert sich selbst, `tools/sauber.py` und `.sauber/` nicht.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ALT = "vorlage"

#: Namen, die der Hub schon vergeben hat (Kern-Plugins und Hilfsnamen).
RESERVIERT = {
    "echo", "math", "audit", "event_bus_publisher", "skills", "werkstatt", "mcp", "shell", "beispiel_app",
    "hub", "agent", "kern",
}

ORDNER_UEBERSPRINGEN = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "build", "dist", "node_modules"}
DATEIEN_UEBERSPRINGEN = {"umbenennen.py", "tools/sauber.py"}
PRAEFIXE_UEBERSPRINGEN = (".sauber/",)
TEXT_ENDUNGEN = {".py", ".toml", ".md", ".yaml", ".yml", ".html", ".svg", ".json", ".txt", ".cfg", ".sh", ".js", ".css", ""}

NAME = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


def ersetzungen(neu: str) -> list[tuple[str, str]]:
    """Geordnete Paare (alt, neu); das Längste zuerst, sonst äße `vorlage` die längeren Namen auf."""
    teile = neu.split("_")
    camel = "".join(t.capitalize() for t in teile)
    titel = " ".join(t.capitalize() for t in teile)
    return [
        (f"fyos-plugin-{ALT}", f"fyos-plugin-{neu.replace('_', '-')}"),
        (f"fyos_plugin_{ALT}", f"fyos_plugin_{neu}"),
        (f"FYOS_{ALT.upper()}", f"FYOS_{neu.upper()}"),
        (f"{ALT.capitalize()}Plugin", f"{camel}Plugin"),
        (ALT.capitalize(), titel),
        (ALT, neu),
    ]


def anwenden(text: str, paare: list[tuple[str, str]]) -> str:
    # Ein Durchgang über alle Muster zugleich, damit ein Ersatz nicht vom nächsten Muster erneut getroffen wird.
    muster = re.compile("|".join(re.escape(a) for a, _ in paare))
    tabelle = dict(paare)
    return muster.sub(lambda m: tabelle[m.group(0)], text)


def pruefe_name(neu: str) -> str | None:
    if not NAME.match(neu) or not 2 <= len(neu) <= 30:
        return "Name: Kleinbuchstaben, Ziffern und einzelne Unterstriche, beginnt mit einem Buchstaben, 2 bis 30 Zeichen"
    if neu == ALT:
        return f"Der Name darf nicht '{ALT}' bleiben"
    if neu in RESERVIERT:
        return f"'{neu}' ist schon vom Hub vergeben"
    return None


def textdateien(wurzel: Path) -> list[Path]:
    ergebnis = []
    for pfad in sorted(wurzel.rglob("*")):
        rel = pfad.relative_to(wurzel)
        if not pfad.is_file() or ORDNER_UEBERSPRINGEN & set(rel.parts) or any(t.endswith(".egg-info") for t in rel.parts):
            continue
        if rel.as_posix() in DATEIEN_UEBERSPRINGEN or rel.as_posix().startswith(PRAEFIXE_UEBERSPRINGEN):
            continue
        if pfad.suffix.lower() in TEXT_ENDUNGEN:
            ergebnis.append(pfad)
    return ergebnis


def umbenennen(wurzel: Path, neu: str, trocken: bool = False) -> list[str]:
    """Führt die Umbenennung aus; liefert die Meldungen. Wirft ValueError bei einem falschen Namen oder Ordner."""
    fehler = pruefe_name(neu)
    if fehler:
        raise ValueError(fehler)
    if not (wurzel / f"fyos_plugin_{ALT}").is_dir():
        raise ValueError(f"{wurzel}: Ordner fyos_plugin_{ALT} fehlt (schon umbenannt?)")
    paare = ersetzungen(neu)
    meldungen: list[str] = []

    for pfad in textdateien(wurzel):
        try:
            alt = pfad.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        neu_text = anwenden(alt, paare)
        if neu_text != alt:
            meldungen.append(f"Inhalt   {pfad.relative_to(wurzel).as_posix()}")
            if not trocken:
                pfad.write_text(neu_text, encoding="utf-8")

    # Namen von Ordnern und Dateien, tiefste zuerst, damit übergeordnete Pfade beim Umbenennen noch stimmen.
    pfade = [
        p for p in wurzel.rglob("*")
        if not (ORDNER_UEBERSPRINGEN & set(p.relative_to(wurzel).parts))
        and not any(t.endswith(".egg-info") for t in p.relative_to(wurzel).parts)
        and p.relative_to(wurzel).as_posix() not in DATEIEN_UEBERSPRINGEN
    ]
    for pfad in sorted(pfade, key=lambda p: len(p.parts), reverse=True):
        neuer_name = anwenden(pfad.name, paare)
        if neuer_name != pfad.name:
            ziel = pfad.with_name(neuer_name)
            meldungen.append(f"Name     {pfad.relative_to(wurzel).as_posix()} -> {ziel.name}")
            if not trocken:
                pfad.rename(ziel)
    return meldungen


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("name", help="neuer Plugin-Name, z. B. wetter")
    p.add_argument("--wurzel", default=str(Path(__file__).resolve().parent), help="Ordner des Repos (Vorgabe: dieser)")
    p.add_argument("--trocken", action="store_true", help="nur anzeigen, nichts ändern")
    a = p.parse_args(argv)
    try:
        meldungen = umbenennen(Path(a.wurzel).resolve(), a.name, a.trocken)
    except ValueError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 2
    print("\n".join(meldungen))
    print(f"\n{len(meldungen)} Änderung(en){' (trocken, nichts geschrieben)' if a.trocken else ''}.")
    if not a.trocken:
        print(
            "Weiter: uv pip install -e '.[test]' && python3 -m pytest -q\n"
            "        Beschreibungstexte in pyproject.toml, fyos-katalog.yaml, README.md und skills/ anpassen."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
