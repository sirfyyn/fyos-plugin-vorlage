English: [README.en.md](README.en.md)

# fyos-plugin-vorlage

Ein vollständiges, lauffähiges Muster für ein Plugin von **FYOS — For Your Own Sake**. Es folgt Schritt für Schritt
der Anleitung [`docs/ERWEITERN.md`](https://git.example.com/fyos/fyos-os/src/branch/main/docs/ERWEITERN.md) in
`fyos-os`. Kopiere das Repo, benenne es um, ersetze die Werkzeuge durch deine.

## Was drin ist

| Pfad | Zweck |
|---|---|
| `fyos_plugin_vorlage/plugin.py` | `VorlagePlugin`: Werkzeuge `vorlage.hallo` (lesend) und `vorlage.notiz_setzen` (schreibend, mit Trockenlauf; ein echter Lauf braucht `bestaetigt: true`), Konfiguration, Geheimnis, Fehlerarten, Oberfläche anmelden |
| `fyos_plugin_vorlage/ui/vorlage.html` | die App (`ui://vorlage/vorlage.html`) mit der gemeinsamen Brücke des Hubs: Frische-Stempel am Panel („Stand vor 2 Min.“, nach 5 Minuten „veraltet“) und „Speichern“ als Anfrage (Plan zeigen, Rückfrage, erst nach „Ja“ schreiben) |
| `fyos_plugin_vorlage/fyos-katalog.yaml`, `bilder/` | Katalogeintrag für den Installer mit Skizze und »Was daraus wird« |
| `fyos_plugin_vorlage/skills/vorlage/SKILL.md` | Wissen für den Agenten (wann welches Werkzeug, Fallen); reist im Paket mit |
| `pyproject.toml` | Paket, Entry-Points `mcp_hub.plugins` (Hub), `fyos.katalog` (Installer) und `fyos.skills` (Skills) |
| `Dockerfile` | Hub-Bild mit diesem Plugin; installiert mit uv, ein eigener Paketindex steht per `FYOS_INDEX_URL` vor PyPI |
| `hub-config.beispiel.yaml` | Eintrag in der Hub-Konfiguration: `config:` und `secrets:` |
| `begleiter/hallo_per_rest.py` | Begleitskript: Werkzeug von außen über `/hub/call` aufrufen (`--notiz` zeigt den Plan, erst `--ja` speichert) |
| `tests/` | pytest gegen den echten Hub-Kern, dazu ein Test, der die Vorlage umbenennt und die Kopie testet |
| `tools/sauber.py`, `.sauber/` | Sauberkeits-Prüfung (keine privaten Adressen, Konten, Geheimnisse im Repo) |
| `.gitea/workflows/ci.yml` | CI: Sauberkeit, dann Tests (Pakete mit uv, Paketindex vor PyPI) |
| `.github/workflows/` | dasselbe auf GitHub: `tests.yml` (Tests und Geheimnis-Scan), `pypi.yml` (veröffentlicht das Paket auf einen Tag `v*` per Trusted Publishing) |
| `umbenennen.py` | benennt Paket, Plugin und Werkzeuge in einem Schritt um |
| `LICENSE`, `NOTICE` | Apache License 2.0 und Urheberhinweis; für ein abgeleitetes Plugin anpassen (siehe [Lizenz](#lizenz)) |
| `README.en.md` | englische Fassung dieser Datei |

## Ausprobieren

Installiert wird mit [uv](https://docs.astral.sh/uv/) statt mit pip; der Grund steht im Abschnitt
[Pakete mit uv, der eigene Index zuerst](#pakete-mit-uv-der-eigene-index-zuerst).

```sh
uv venv && . .venv/bin/activate
uv pip install -e /pfad/zu/fyos-os/hub     # der Hub (Paket fyos-hub)
uv pip install -e ".[test]"
python3 -m pytest -q
python3 -m mcp_hub.server                  # Hub auf Port 8080; die Vorlage lädt über den Entry-Point
curl -s localhost:8080/hub/call -H 'Content-Type: application/json' \
  -d '{"tool":"vorlage.hallo","arguments":{"name":"Alex"}}'
```

Die App öffnet sich in der Shell unter `/os?offen=app:vorlage__hallo`.

Schreiben geht in zwei Schritten, als Anfrage statt als Aktion (`docs/ERWEITERN.md` im Repo `fyos-os`, Abschnitt 3.6):
erst der Plan, dann die Bestätigung. Die App macht das mit „Speichern“ von selbst, von außen sieht es so aus:

```sh
curl -s localhost:8080/hub/call -H 'Content-Type: application/json' \
  -d '{"tool":"vorlage.notiz_setzen","arguments":{"text":"Milch kaufen","__dry_run__":true}}'   # nur der Plan
curl -s localhost:8080/hub/call -H 'Content-Type: application/json' \
  -d '{"tool":"vorlage.notiz_setzen","arguments":{"text":"Milch kaufen","bestaetigt":true}}'    # speichert wirklich
```

## Umbenennen in 5 Schritten

1. **Kopieren:** Repo kopieren oder als Vorlage nutzen, in `fyos-plugin-<name>` umbenennen (der Installer erkennt
   Plugin-Pakete am Präfix `fyos-plugin-`).
2. **Umbenennen:** `python3 umbenennen.py wetter` (Probe zuerst mit `--trocken`). Das Skript ersetzt Paket
   (`fyos_plugin_wetter`), Plugin-Name und Werkzeug-IDs (`wetter.hallo`), Klasse (`WetterPlugin`), Umgebungsvariablen
   (`FYOS_WETTER_…`), Ordner `skills/wetter`, `ui/wetter.html`, `bilder/wetter-1.svg` und die Einträge in `pyproject.toml`.
3. **Installieren und prüfen:** `uv pip install -e ".[test]" && python3 -m pytest -q`.
4. **Werkzeuge ersetzen:** in `plugin.py` `describe_tools` und `call` an dein Vorhaben anpassen, die App in
   `ui/<name>.html`, den Skill in `fyos_plugin_<name>/skills/<name>/SKILL.md`, den Katalogeintrag in `fyos-katalog.yaml`. Tests mitziehen.
5. **Ausliefern:** `python3 tools/sauber.py .` muss still sein, dann committen. Das Hub-Bild mit
   `docker build --build-arg HUB_BILD=<registry>/fyos-os/hub:main -t mein-hub:main .` bauen (braucht das Paket Pakete
   aus einem eigenen Index, kommt `--build-arg FYOS_INDEX_URL=<Index-URL>` dazu) oder das Paket über den
   Installer wählen (siehe ERWEITERN.md, Abschnitt 10).

Danach `umbenennen.py` löschen oder behalten, wie du magst; die Tests, die die Umbenennung prüfen
(`tests/test_paket.py`, Gruppe »Umbenennen«), lassen sich mit ihm entfernen.

## Pakete mit uv, der eigene Index zuerst

Dockerfile und CI installieren mit [uv](https://docs.astral.sh/uv/) statt mit pip. Ein eigener Paketindex (zum Beispiel
die PyPI-Registry deines Git-Servers) steht per `--index` vor PyPI: im Dockerfile als Bau-Argument `FYOS_INDEX_URL`, in der
CI als Repo-Variable `FYOS_PIP_INDEX`. Dazu steht `--index-strategy first-index` ausdrücklich im Befehl: uv nimmt ein Paket
nur aus dem ersten Index, der es führt. Ein Paket gleichen Namens auf PyPI kann ein Paket aus deinem Index so nicht
verdrängen (Dependency Confusion); mit `pip --extra-index-url` wäre das möglich, weil pip die höchste Version aus allen
Indizes nimmt. Die Version von uv ist im Dockerfile und in der CI fest. Mehr dazu in `docs/ERWEITERN.md` im Repo
`fyos-os`, Abschnitt 10.3.

## Was nicht ins Repo gehört

Tokens, Passwörter, Schlüssel, `.env`-Dateien, echte Adressen deiner Geräte, Namen von Personen. Geheimnisse stehen in
der Umgebung des Hubs oder unter `/run/secrets/`, im Repo nur ihr Name. `tools/sauber.py` fängt die gröbsten Fehler ab.
Ein Plugin-Repo mit persönlicher Konfiguration bleibt privat.

## Lizenz

FYOS Plugin-Vorlage steht unter der Apache License, Version 2.0 (SPDX-Kennung `Apache-2.0`).

Copyright 2026 sirfyyn and FYOS CONTRIBUTORS <!-- sauber: ok -->

Der vollständige Lizenztext steht in [`LICENSE`](LICENSE), der Urheberhinweis in [`NOTICE`](NOTICE).

Für ein eigenes Plugin auf Grundlage dieses Musters: Die Lizenz deines Plugins wählst du selbst. Was du vom Muster
übernimmst, bleibt unter Apache-2.0; behalte dafür `LICENSE` und die Urheberzeile in `NOTICE` bei und ergänze deine eigene.
Trage deine Lizenz und deine Urheberzeile außerdem in `pyproject.toml` (`license`, `authors`) und in `NOTICE` ein;
`umbenennen.py` ändert sie nicht.
