Deutsch: [README.md](README.md)

# fyos-plugin-vorlage

A complete, runnable sample for a plugin of **FYOS — For Your Own Sake**. It follows the guide
[`docs/ERWEITERN.md`](https://git.example.com/fyos/fyos-os/src/branch/main/docs/ERWEITERN.md) in
`fyos-os` step by step. Copy the repo, rename it, replace the tools with yours.

## What is in it

| Path | Purpose |
|---|---|
| `fyos_plugin_vorlage/plugin.py` | `VorlagePlugin`: tools `vorlage.hallo` (read) and `vorlage.notiz_setzen` (write, with dry run; a real run needs `bestaetigt: true`), configuration, secret, error kinds, registering the interface |
| `fyos_plugin_vorlage/ui/vorlage.html` | the app (`ui://vorlage/vorlage.html`) with the hub's shared bridge: a freshness stamp on the panel ("Stand vor 2 Min." = "as of 2 min ago", "veraltet" = "stale" after 5 minutes) and "Speichern" (save) as a request (show the plan, ask back, write only after "Ja" = yes) |
| `fyos_plugin_vorlage/fyos-katalog.yaml`, `bilder/` | catalog entry for the installer with a sketch and "Was daraus wird" (what it turns into) |
| `fyos_plugin_vorlage/skills/vorlage/SKILL.md` | knowledge for the agent (which tool when, pitfalls); travels with the package |
| `pyproject.toml` | package, entry points `mcp_hub.plugins` (hub), `fyos.katalog` (installer) and `fyos.skills` (skills) |
| `Dockerfile` | hub image with this plugin; installs with uv, a package index of your own goes before PyPI via `FYOS_INDEX_URL` |
| `hub-config.beispiel.yaml` | entry in the hub configuration: `config:` and `secrets:` |
| `begleiter/hallo_per_rest.py` | companion script: call a tool from outside via `/hub/call` (`--notiz` shows the plan, only `--ja` saves) |
| `tests/` | pytest against the real hub core, plus a test that renames the template and tests the copy |
| `tools/sauber.py`, `.sauber/` | cleanliness check (no private addresses, accounts or secrets in the repo) |
| `.gitea/workflows/ci.yml` | CI: cleanliness, then tests (packages with uv, package index before PyPI) |
| `.github/workflows/` | the same on GitHub: `tests.yml` (tests and secret scan), `pypi.yml` (publishes the package on a `v*` tag via Trusted Publishing) |
| `umbenennen.py` | renames package, plugin and tools in one step |
| `LICENSE`, `NOTICE` | Apache License 2.0 and copyright notice; adapt them for a derived plugin (see [License](#license)) |
| `README.md` | German version of this file |

## Trying it out

Packages are installed with [uv](https://docs.astral.sh/uv/) instead of pip; the reason is given in the section
[Packages with uv, your own index first](#packages-with-uv-your-own-index-first).

```sh
uv venv && . .venv/bin/activate
uv pip install -e /pfad/zu/fyos-os/hub     # the hub (package fyos-hub); /pfad/zu/ means /path/to/
uv pip install -e ".[test]"
python3 -m pytest -q
python3 -m mcp_hub.server                  # hub on port 8080; the template loads via the entry point
curl -s localhost:8080/hub/call -H 'Content-Type: application/json' \
  -d '{"tool":"vorlage.hallo","arguments":{"name":"Alex"}}'
```

The app opens in the shell at `/os?offen=app:vorlage__hallo`.

Writing happens in two steps, as a request instead of an action (`docs/ERWEITERN.md` in the repo `fyos-os`, section 3.6):
first the plan, then the confirmation. The app does this by itself with "Speichern"; from outside it looks like this:

```sh
curl -s localhost:8080/hub/call -H 'Content-Type: application/json' \
  -d '{"tool":"vorlage.notiz_setzen","arguments":{"text":"Milch kaufen","__dry_run__":true}}'   # the plan only
curl -s localhost:8080/hub/call -H 'Content-Type: application/json' \
  -d '{"tool":"vorlage.notiz_setzen","arguments":{"text":"Milch kaufen","bestaetigt":true}}'    # really saves
```

## Renaming in 5 steps

1. **Copy:** Copy the repo or use it as a template, and rename it to `fyos-plugin-<name>` (the installer recognizes
   plugin packages by the prefix `fyos-plugin-`).
2. **Rename:** `python3 umbenennen.py wetter` (rehearse first with `--trocken`, the dry-run flag). The script replaces the
   package (`fyos_plugin_wetter`), plugin name and tool IDs (`wetter.hallo`), class (`WetterPlugin`), environment variables
   (`FYOS_WETTER_…`), folder `skills/wetter`, `ui/wetter.html`, `bilder/wetter-1.svg` and the entries in `pyproject.toml`.
3. **Install and check:** `uv pip install -e ".[test]" && python3 -m pytest -q`.
4. **Replace the tools:** adapt `describe_tools` and `call` in `plugin.py` to your purpose, the app in
   `ui/<name>.html`, the skill in `fyos_plugin_<name>/skills/<name>/SKILL.md`, the catalog entry in `fyos-katalog.yaml`. Update the tests to match.
5. **Deliver:** `python3 tools/sauber.py .` must be silent, then commit. Build the hub image with
   `docker build --build-arg HUB_BILD=<registry>/fyos-os/hub:main -t mein-hub:main .` (if the package needs packages
   from an index of your own, add `--build-arg FYOS_INDEX_URL=<Index-URL>`) or choose the package via the
   installer (see ERWEITERN.md, section 10).

Afterwards delete `umbenennen.py` or keep it, as you like; the tests that check the renaming
(`tests/test_paket.py`, group "Umbenennen", i.e. renaming) can be removed along with it.

## Packages with uv, your own index first

Dockerfile and CI install with [uv](https://docs.astral.sh/uv/) instead of pip. A package index of your own (for example
the PyPI registry of your Git server) goes before PyPI via `--index`: in the Dockerfile as the build argument
`FYOS_INDEX_URL`, in the CI as the repo variable `FYOS_PIP_INDEX`. In addition, `--index-strategy first-index` is set
explicitly in the command: uv takes a package only from the first index that carries it. A package of the same name on
PyPI therefore cannot displace a package from your index (dependency confusion); with `pip --extra-index-url` it could,
because pip takes the highest version from all indexes. The version of uv is pinned in the Dockerfile and in the CI. More in
`docs/ERWEITERN.md` in the repo `fyos-os`, section 10.3.

## What does not belong in the repo

Tokens, passwords, keys, `.env` files, real addresses of your devices, names of people. Secrets live in the hub's
environment or under `/run/secrets/`; the repo holds only their name. `tools/sauber.py` catches the coarsest mistakes.
A plugin repo with personal configuration stays private.

## License

FYOS Plugin-Vorlage is licensed under the Apache License, Version 2.0 (SPDX identifier `Apache-2.0`).

Copyright 2026 sirfyyn and FYOS CONTRIBUTORS <!-- sauber: ok -->

The full license text is in [`LICENSE`](LICENSE), the copyright notice in [`NOTICE`](NOTICE).

For a plugin of your own based on this sample: you choose the license of your plugin yourself. Whatever you take over from
the sample stays under Apache-2.0; keep `LICENSE` and the copyright line in `NOTICE` for that and add your own. Also enter
your license and your copyright line in `pyproject.toml` (`license`, `authors`) and in `NOTICE`; `umbenennen.py` does not
change them.
