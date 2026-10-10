"""fyos_plugin_vorlage — Muster für ein FYOS-Hub-Plugin.

Das Paket meldet sich über den Entry-Point `mcp_hub.plugins` beim Hub an (`plugin.py`) und über `fyos.katalog`
beim Installer (`katalog_pfad`).
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

KATALOG_DATEI = Path(__file__).resolve().parent / "fyos-katalog.yaml"


def katalog_pfad() -> Path:
    """Pfad der Katalogdatei dieses Pakets. Die Bilder liegen daneben unter `bilder/`."""
    return KATALOG_DATEI
