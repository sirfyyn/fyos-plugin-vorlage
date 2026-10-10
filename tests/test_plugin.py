"""Das Plugin gegen den echten Hub-Kern: Werkzeuge, Trockenlauf, Fehlerarten, Oberfläche, REST-Wege."""

from __future__ import annotations

import importlib
import importlib.metadata
import tomllib
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp_hub import registry as hub_registry
from mcp_hub import server as hub_server
from mcp_hub.config import HubConfig, PluginConfig
from mcp_hub.kv import SpeicherKv
from mcp_hub.plugin import HubPlugin

from fyos_plugin_vorlage.plugin import SCHLUESSEL, UI_URI, VorlagePlugin

WURZEL = Path(__file__).resolve().parent.parent


@pytest.fixture
def plugin() -> VorlagePlugin:
    p = VorlagePlugin()
    p._r = SpeicherKv()  # eigener Speicher je Test
    return p


@pytest.fixture
def reg(plugin: VorlagePlugin, monkeypatch: pytest.MonkeyPatch) -> hub_registry.PluginRegistry:
    r = hub_registry.PluginRegistry()
    hub_registry._register_one(r, "vorlage", plugin)
    monkeypatch.setattr(hub_server, "_REGISTRY", r)
    return r


@pytest.fixture
def client(reg) -> TestClient:
    assert hub_server._REGISTRY is reg  # die Fixture reg richtet die Registry des Hubs ein, bevor die Routen sie lesen
    app = Starlette(
        routes=[
            Route("/hub/call", hub_server.rest_call, methods=["POST"]),
            Route("/hub/app-call", hub_server.rest_app_call, methods=["POST"]),
            Route("/hub/apps", hub_server.rest_apps, methods=["GET"]),
            Route("/hub/resource", hub_server.rest_resource, methods=["GET"]),
        ]
    )
    return TestClient(app)


# ── Anmeldung beim Hub ────────────────────────────────────────────────────────────────────────────


def test_entry_point_steht_in_der_pyproject_und_ist_ladbar():
    daten = tomllib.loads((WURZEL / "pyproject.toml").read_text(encoding="utf-8"))
    ziel = daten["project"]["entry-points"]["mcp_hub.plugins"]["vorlage"]
    modul, klasse = ziel.split(":")
    cls = getattr(importlib.import_module(modul), klasse)
    assert issubclass(cls, HubPlugin) and cls.name == "vorlage"


def test_hub_laedt_das_plugin_per_modul():
    cfg = HubConfig(plugins=[PluginConfig(name="vorlage", module="fyos_plugin_vorlage.plugin")])
    reg = hub_registry.build_registry(cfg)
    assert not reg.nicht_geladen
    # Der Hub lädt außerdem seine Kern-Plugins über deren Entry-Points; hier zählt nur dieses Plugin.
    assert sorted(t for t in reg.tools if t.startswith("vorlage.")) == ["vorlage.hallo", "vorlage.notiz_setzen"]
    assert UI_URI in reg.resources


def test_hub_findet_das_installierte_paket_per_entry_point():
    eps = [ep for ep in importlib.metadata.entry_points(group="mcp_hub.plugins") if ep.name == "vorlage"]
    if not eps:
        pytest.skip("Paket nicht installiert (uv pip install -e .)")
    reg = hub_registry.build_registry(HubConfig())
    assert "vorlage.hallo" in reg.tools


def test_config_wird_dem_konstruktor_uebergeben():
    cfg = HubConfig(
        plugins=[PluginConfig(name="vorlage", module="fyos_plugin_vorlage.plugin", config={"begruessung": "Moin"})]
    )
    reg = hub_registry.build_registry(cfg)
    r = hub_registry.dispatch(reg, "vorlage.hallo", {"name": "Alex"})
    assert r["ok"] is True and r["result"]["satz"] == "Moin, Alex!"


# ── Werkzeuge ─────────────────────────────────────────────────────────────────────────────────────


def test_scopes_und_tags(reg):
    assert hub_registry.scope_from_tags(reg.tools["vorlage.hallo"].descriptor.tags) == "READ"
    assert hub_registry.scope_from_tags(reg.tools["vorlage.notiz_setzen"].descriptor.tags) == "WRITE"
    for rt in reg.tools.values():
        assert hub_registry.ist_flaechen_werkzeug(rt.descriptor)
        assert rt.descriptor.meta["ui"]["resourceUri"] == UI_URI


def test_hallo(reg):
    r = hub_registry.dispatch(reg, "vorlage.hallo", {})
    assert r["ok"] is True
    assert r["result"]["satz"] == "Hallo, du!"
    assert r["result"]["notiz"] is None
    r = hub_registry.dispatch(reg, "vorlage.hallo", {"name": "  Alex  "})
    assert r["result"]["satz"] == "Hallo, Alex!"


def test_notiz_setzen_und_lesen(reg):
    r = hub_registry.dispatch(reg, "vorlage.notiz_setzen", {"text": "  Milch kaufen  ", "bestaetigt": True})
    assert r["ok"] is True and r["result"]["notiz"] == "Milch kaufen"
    assert hub_registry.dispatch(reg, "vorlage.hallo", {})["result"]["notiz"] == "Milch kaufen"


def test_trockenlauf_aendert_nichts(reg, plugin):
    r = hub_registry.dispatch(reg, "vorlage.notiz_setzen", {"text": "Plan", "__dry_run__": True})
    assert r["ok"] is True
    plan = r["result"]
    assert plan["dry_run"] is True and plan["method"] == "notiz_setzen" and "would_execute" in plan
    assert plugin._r.get(SCHLUESSEL) is None  # nichts geschrieben
    # auch eine Bestätigung macht aus dem Trockenlauf keinen echten Lauf
    r = hub_registry.dispatch(reg, "vorlage.notiz_setzen", {"text": "Plan", "__dry_run__": True, "bestaetigt": True})
    assert r["ok"] is True and r["result"]["dry_run"] is True
    assert plugin._r.get(SCHLUESSEL) is None


def test_echter_lauf_braucht_die_bestaetigung(reg, plugin):
    """Anfrage statt Aktion: ohne `bestaetigt: true` ändert das Werkzeug nichts und sagt, was fehlt."""
    for args in ({"text": "Milch"}, {"text": "Milch", "bestaetigt": False}, {"text": "Milch", "bestaetigt": "true"}):
        r = hub_registry.dispatch(reg, "vorlage.notiz_setzen", args)
        assert r["ok"] is False and r["kind"] == "bad_arguments", args
        assert "bestaetigt" in r["error"] and "__dry_run__" in r["error"]
    assert plugin._r.get(SCHLUESSEL) is None
    # Eingabefehler kommen vor der Rückfrage: ein leerer Text wird nicht erst „bestätigt“
    r = hub_registry.dispatch(reg, "vorlage.notiz_setzen", {"text": "  ", "bestaetigt": True})
    assert r["ok"] is False and "text" in r["error"]


def test_plan_hat_die_felder_die_die_oberflaeche_zeigt(reg):
    """`App.beantragen` zeigt would_execute und expected_side_effects und verlangt dry_run: true; der Plan liefert sie."""
    plan = hub_registry.dispatch(reg, "vorlage.notiz_setzen", {"text": "Eins", "__dry_run__": True})["result"]
    assert plan["dry_run"] is True and plan["ok"] is True
    assert isinstance(plan["would_execute"], str) and "4 Zeichen" in plan["would_execute"]
    assert plan["expected_side_effects"] and all(isinstance(w, str) for w in plan["expected_side_effects"])
    hub_registry.dispatch(reg, "vorlage.notiz_setzen", {"text": "Eins", "bestaetigt": True})
    ersetzt = hub_registry.dispatch(reg, "vorlage.notiz_setzen", {"text": "Zwei", "__dry_run__": True})["result"]
    assert "ersetzen" in ersetzt["would_execute"] and "ersetzt" in ersetzt["expected_side_effects"][0]


def test_eingabefehler_sind_bad_arguments_und_sperren_nicht(reg):
    for _ in range(8):  # mehr als die Schwelle des Schutzschalters
        for tool, args in (
            ("vorlage.notiz_setzen", {}),
            ("vorlage.notiz_setzen", {"text": "   "}),
            ("vorlage.notiz_setzen", {"text": "x" * 1000}),
            ("vorlage.hallo", {"name": 5}),
        ):
            r = hub_registry.dispatch(reg, tool, args)
            assert r["ok"] is False and r["kind"] == "bad_arguments"
    assert hub_registry.dispatch(reg, "vorlage.hallo", {})["ok"] is True


def test_unbekanntes_argument_wird_vom_hub_abgelehnt(reg):
    r = hub_registry.dispatch(reg, "vorlage.hallo", {"foo": 1})
    assert r["ok"] is False and r["kind"] == "bad_arguments" and "foo" in r["error"]


def test_konfiguration_vorrang_config_vor_umgebung_vor_vorgabe(monkeypatch):
    assert VorlagePlugin().begruessung == "Hallo"
    monkeypatch.setenv("FYOS_VORLAGE_BEGRUESSUNG", "Servus")
    assert VorlagePlugin().begruessung == "Servus"
    assert VorlagePlugin(config={"begruessung": "Moin"}).begruessung == "Moin"
    monkeypatch.setenv("FYOS_VORLAGE_NOTIZ_MAX", "kaputt")
    assert VorlagePlugin().notiz_max == 280


def test_health_nennt_das_geheimnis_nie(plugin, monkeypatch):
    assert plugin.health()["token"] is False
    monkeypatch.setenv("FYOS_VORLAGE_TOKEN", "geheim-123")
    h = plugin.health()
    assert h["token"] is True and "geheim-123" not in str(h)


# ── Oberfläche ────────────────────────────────────────────────────────────────────────────────────


def test_oberflaeche_ist_vollstaendig_eingesetzt(plugin):
    html = plugin.describe_resources()[0].read()
    for rest in ("/*STIL*/", "/*BRUECKE*/", "<!--KOPF-->", "<!--/KOPF-->", "/*KONFIG*/{}", "/*SYMBOLE*/{}"):
        assert rest not in html
    assert "const App" in html and "<h1>Vorlage</h1>" in html
    assert '"werkzeug":"vorlage__hallo"' in html.replace(" ", "")
    # die Brücke des Hubs bringt Frische und Anfrage mit (ERWEITERN.md §3.6); ein älterer Hub hätte sie nicht
    assert "function frische" in html and "function beantragen" in html


def test_oberflaeche_hat_frische_stempel_und_fragt_vor_dem_schreiben():
    """Konvention (ERWEITERN.md §3.6): Daten tragen einen Frische-Stempel, ein schreibender Knopf stellt nur eine Anfrage."""
    # die Datei der App selbst, nicht die ausgelieferte Seite: in der steckt die Brücke, die `bestaetigt` setzt
    html = (WURZEL / "fyos_plugin_vorlage" / "ui" / "vorlage.html").read_text(encoding="utf-8")
    assert "App.frische(" in html and "stand.zeit" in html          # Stempel mit dem Stand der Daten
    assert "App.takt(" in html                                       # sie werden regelmäßig neu geholt
    assert "App.beantragen(" in html and 'id="antrag"' in html      # Speichern geht über die Anfrage, mit Platz für die Rückfrage
    assert "bestaetigt" not in html                                  # die Seite setzt die Bestätigung nie selbst, das tut die Brücke
    # jeder Aufruf von notiz_setzen ist entweder die Anfrage oder ein reiner Trockenlauf
    for zeile in html.splitlines():
        if "notiz_setzen" in zeile and "rufen(" in zeile:
            assert "__dry_run__" in zeile, zeile


def test_oberflaeche_per_rest(client):
    apps = client.get("/hub/apps").json()
    namen = {a["name"] for a in apps["apps"]} if isinstance(apps, dict) and "apps" in apps else {a["name"] for a in apps}
    assert {"vorlage__hallo", "vorlage__notiz_setzen"} <= namen
    antwort = client.get("/hub/resource", params={"uri": UI_URI})
    assert antwort.status_code == 200 and "Vorlage" in antwort.text


def test_app_call_ist_der_weg_des_browsers(client):
    # so geht die Brücke bei `App.beantragen` vor: erst der Plan, dann der bestätigte Lauf
    r = client.post("/hub/app-call", json={"name": "vorlage__notiz_setzen", "arguments": {"text": "aus der App"}})
    assert r.status_code == 400 and r.json()["kind"] == "bad_arguments"  # ohne Bestätigung nichts
    r = client.post("/hub/app-call", json={"name": "vorlage__hallo", "arguments": {}})
    assert r.json()["result"]["notiz"] is None
    r = client.post(
        "/hub/app-call",
        json={"name": "vorlage__notiz_setzen", "arguments": {"text": "aus der App", "bestaetigt": True}},
    )
    assert r.status_code == 200 and r.json()["ok"] is True
    r = client.post("/hub/app-call", json={"name": "vorlage__hallo", "arguments": {}})
    assert r.json()["result"]["notiz"] == "aus der App"
    plan = client.post(
        "/hub/app-call", json={"name": "vorlage__notiz_setzen", "arguments": {"text": "x", "__dry_run__": True}}
    ).json()
    assert plan["result"]["dry_run"] is True


def test_call_endpunkt_fuer_skripte_und_agenten(client):
    r = client.post("/hub/call", json={"tool": "vorlage.hallo", "arguments": {"name": "Fy"}})
    assert r.status_code == 200 and r.json()["result"]["satz"] == "Hallo, Fy!"
    r = client.post("/hub/call", json={"tool": "vorlage.notiz_setzen", "arguments": {}})
    assert r.status_code == 400 and r.json()["kind"] == "bad_arguments"
