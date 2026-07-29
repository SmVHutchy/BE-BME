"""Gemeinsame Fixtures.

Die Tests laufen bewusst gegen die **echte** config/params.yaml und nicht gegen
erfundene Werte. Damit pruefen sie zwei Dinge zugleich: dass die Funktionen
stimmen, und dass die ausgelieferten Parameter sich sinnvoll verhalten. Ein
Parameter, der in der Arbeit begruendet werden muss, sollte auch im Test
auftauchen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frame_core.config import AppConfig, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARAMS_PATH = PROJECT_ROOT / "config" / "params.yaml"


@pytest.fixture(scope="session")
def app_config() -> AppConfig:
    return load_config(PARAMS_PATH)
