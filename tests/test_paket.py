"""Alles um das Plugin herum: Katalogeintrag, Skill, Begleitskript und das Umbenennen der Vorlage."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from mcp_hub.plugins.skills import SkillsPlugin

from fyos_plugin_vorlage import katalog_pfad

WURZEL = Path(__file__).resolve().parent.parent


# ── Katalogeintrag ────────────────────────────────────────────────────────────────────────────────


def test_katalog_hat_die_pflichtfelder_und_ein_bild():
    pfad = katalog_pfad()
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    (b,) = daten["bausteine"]
    for feld in ("id", "titel", "kurz", "was_daraus_wird", "art", "bilder", "quelle", "konfiguration"):
        assert b[feld], feld
    assert b["art"] == "plugin" and "\n" not in b["kurz"].strip()
    for bild in b["bilder"]:
        assert (pfad.parent / "bilder" / bild).is_file(), bild
    # jedes Feld wird zu einer Umgebungsvariable, die das Plugin liest
    quelltext = (WURZEL / "fyos_plugin_vorlage" / "plugin.py").read_text(encoding="utf-8")
    for feld in b["konfiguration"]:
        assert feld["umgebung"] in quelltext, feld["umgebung"]
    # Reifegrad im Installer: die Vorlage bringt eine App und Werkzeuge für den Agenten (Stufe 1 bis 3 je Schicht)
    assert b["reife"] == {"oberflaeche": 2, "agent": 2}


def test_katalog_besteht_die_pruefung_des_installers():
    katalog = pytest.importorskip("fyos_installer.katalog", reason="fyos-os/installer nicht installiert")
    bausteine = katalog.lade_datei(katalog_pfad())
    assert [b.id for b in bausteine] == ["vorlage"]
    assert katalog.bilder_von(bausteine[0]), "Bild nicht gefunden"


# ── Skill ─────────────────────────────────────────────────────────────────────────────────────────


def test_skill_ist_fuer_das_hub_plugin_skills_auffindbar():
    skills = SkillsPlugin(config={"quellen": [str(WURZEL / "fyos_plugin_vorlage" / "skills")]})
    treffer = skills.call("suchen", {"q": "notiz"})
    assert [s["name"] for s in treffer["skills"]] == ["vorlage"]
    gelesen = skills.call("lesen", {"name": "vorlage"})
    assert "vorlage.notiz_setzen" in gelesen["text"] and gelesen["fuer"] == ["agent"]


def test_skill_reist_im_paket_mit():
    """Entry-Point `fyos.skills` zeigt auf das Paket, dessen Unterordner `skills/` als package-data mitgeht."""
    import tomllib

    daten = tomllib.loads((WURZEL / "pyproject.toml").read_text(encoding="utf-8"))
    assert daten["project"]["entry-points"]["fyos.skills"]["vorlage"] == "fyos_plugin_vorlage"
    assert "skills/*/*.md" in daten["tool"]["setuptools"]["package-data"]["fyos_plugin_vorlage"]
    assert (WURZEL / "fyos_plugin_vorlage" / "skills" / "vorlage" / "SKILL.md").is_file()


# ── Begleitskript ─────────────────────────────────────────────────────────────────────────────────


def test_begleitskript_baut_die_anfrage():
    sys.path.insert(0, str(WURZEL / "begleiter"))
    try:
        import hallo_per_rest as skript
    finally:
        sys.path.remove(str(WURZEL / "begleiter"))
    req = skript.anfrage_bauen("http://hub.example.com:8080/", "vorlage.hallo", {"name": "Alex"})
    assert req.full_url == "http://hub.example.com:8080/hub/call" and req.get_method() == "POST"
    assert json.loads(req.data) == {"tool": "vorlage.hallo", "arguments": {"name": "Alex"}}
    with pytest.raises(ValueError):
        skript.anfrage_bauen("hub", "vorlage.hallo", {})


def test_begleitskript_speichert_nur_auf_ausdruecklichen_wunsch():
    """Anfrage statt Aktion auch im Skript: ohne `--ja` nur der Plan, mit `--ja` der bestätigte Lauf."""
    sys.path.insert(0, str(WURZEL / "begleiter"))
    try:
        import hallo_per_rest as skript
    finally:
        sys.path.remove(str(WURZEL / "begleiter"))
    assert skript.notiz_argumente("Milch") == {"text": "Milch", "__dry_run__": True}
    assert skript.notiz_argumente("Milch", ja=True) == {"text": "Milch", "bestaetigt": True}
    with pytest.raises(SystemExit):  # --ja und --trocken zugleich ist ein Widerspruch
        skript.main(["--hub", "http://hub.example.com", "--notiz", "x", "--ja", "--trocken"])


# ── Umbenennen ────────────────────────────────────────────────────────────────────────────────────


def _kopie(ziel: Path) -> Path:
    shutil.copytree(
        WURZEL, ziel,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.egg-info", ".venv", "build", "dist"),
    )
    return ziel


def _umbenennen(wurzel: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(wurzel / "umbenennen.py"), "--wurzel", str(wurzel), *args],
        capture_output=True, text=True, timeout=60,
    )


def test_umbenennen_trocken_aendert_nichts(tmp_path):
    k = _kopie(tmp_path / "k")
    r = _umbenennen(k, "wetter", "--trocken")
    assert r.returncode == 0, r.stderr
    assert (k / "fyos_plugin_vorlage").is_dir() and not (k / "fyos_plugin_wetter").exists()


@pytest.mark.parametrize("name", ["Wetter", "1abc", "a", "vorlage", "skills", "wetter__x", "wetter-x"])
def test_umbenennen_lehnt_schlechte_namen_ab(tmp_path, name):
    k = _kopie(tmp_path / "k")
    r = _umbenennen(k, name)
    assert r.returncode == 2 and "Fehler" in r.stderr
    assert (k / "fyos_plugin_vorlage").is_dir()


def test_umbenennte_vorlage_laeuft_und_besteht_ihre_eigenen_tests(tmp_path):
    k = _kopie(tmp_path / "k")
    r = _umbenennen(k, "haus_licht")
    assert r.returncode == 0, r.stderr
    assert (k / "fyos_plugin_haus_licht" / "ui" / "haus_licht.html").is_file()
    assert (k / "fyos_plugin_haus_licht" / "skills" / "haus_licht" / "SKILL.md").is_file()
    assert (k / "fyos_plugin_haus_licht" / "bilder" / "haus_licht-1.svg").is_file()
    assert not list(k.rglob("*vorlage*")), "Reste im Namen"
    # In den ersetzten Dateien bleibt außer der Anleitung des Skripts selbst nichts vom alten Namen übrig.
    reste = [
        p.relative_to(k).as_posix() for p in k.rglob("*")
        if p.is_file() and p.suffix in {".py", ".toml", ".yaml", ".html", ".svg"} and p.name != "umbenennen.py"
        and "vorlage" in p.read_text(encoding="utf-8").lower() and p.relative_to(k).as_posix() != "tools/sauber.py"
    ]
    assert reste == []
    pyproject = (k / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "fyos-plugin-haus-licht"' in pyproject
    assert 'haus_licht = "fyos_plugin_haus_licht.plugin:HausLichtPlugin"' in pyproject
    # Die umbenannte Kopie testet sich selbst (ohne installiert zu sein: pythonpath = ["."]).
    lauf = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_plugin.py"],
        cwd=k, capture_output=True, text=True, timeout=300,
    )
    assert lauf.returncode == 0, lauf.stdout[-3000:] + lauf.stderr[-1000:]
