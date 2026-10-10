"""Gemeinsame Vorgaben: die Tests laufen ohne Redis, Qdrant und Anmeldung, egal was die Umgebung des Rechners setzt."""

from __future__ import annotations

import os


def pytest_configure(config):
    os.environ.setdefault("MCP_HUB_AUDIT_SKIP_QDRANT", "1")
    for name in (
        "REDIS_URL", "QDRANT_URL", "FYOS_EMBED_URL", "HUB_SUCHE_EMBED_URL", "FYOS_OIDC_ISSUER",
        "FYOS_VORLAGE_BEGRUESSUNG", "FYOS_VORLAGE_NOTIZ_MAX", "FYOS_VORLAGE_TOKEN",
    ):
        os.environ.pop(name, None)
