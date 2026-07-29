"""Wetter-Rohlog.

Schreibt jede Antwort von Open-Meteo **unveraendert** als JSON Line, bevor
irgendetwas interpoliert oder abgebildet wird.

Das ist keine Bequemlichkeit, sondern die Voraussetzung fuer die
Reproduzierbarkeit: `run.seed` + `config/params.yaml` + dieser Log
rekonstruieren einen Lauf vollstaendig. Wuerden nur die interpolierten oder
bereits abgebildeten Werte protokolliert, liesse sich ein Lauf nach einer
Aenderung am Mapping nicht mehr nachrechnen - und genau das Mapping ist der
Gegenstand der Arbeit.

Attribution: Wetterdaten von Open-Meteo.com, CC BY 4.0.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class WeatherRawLog:
    """Haengt Rohantworten an eine JSON-Lines-Datei an."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, payload: dict, *, config_hash: str, run_name: str) -> None:
        """Schreibt eine Rohantwort mit dem Kontext, der sie zuordenbar macht.

        Der Konfigurationshash steht in jeder Zeile, nicht nur einmal am Anfang:
        Der Log ueberlebt Neustarts und Konfigurationsaenderungen, und eine
        Zeile ohne ihren Hash waere spaeter nicht mehr eindeutig zuzuordnen.
        """
        record = {
            "logged_at": datetime.now(UTC).isoformat(),
            "run_name": run_name,
            "config_hash": config_hash,
            "source": "open-meteo",
            "license": "CC BY 4.0",
            "response": payload,
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
