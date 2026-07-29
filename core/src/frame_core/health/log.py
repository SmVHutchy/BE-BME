"""Health-Log als JSON Lines.

Eine Zeile je Intervall mit Bildzeit, Speicher, Massenbilanz, Zustand des
Klimakanals, Neustartzaehler und dem Zeitrafferfaktor.

Der Zeitrafferfaktor gehoert dazu, damit spaeter nachvollziehbar bleibt, ob ein
Abschnitt der Zeitreihe im Zeitraffer entstanden ist oder im Feldbetrieb - sonst
liesse sich die Unterscheidung zwischen Kopplung (`rate`) und Betriebsgroesse
(`sim.speed`) nachtraeglich nicht mehr belegen (docs/mapping.md).

JSON Lines, weil der Log ueber Wochen waechst und zeilenweise auswertbar bleiben
muss, auch wenn der Prozess mitten im Schreiben abstuerzt.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class HealthLog:
    """Haengt Betriebszustaende an eine JSON-Lines-Datei an."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.restart_count = 0

    @property
    def path(self) -> Path:
        return self._path

    def note_restart(self) -> None:
        self.restart_count += 1

    def append(self, **fields) -> dict:
        """Schreibt eine Zeile und gibt sie zurueck (fuer GET /health)."""
        record = {"t": datetime.now(UTC).isoformat(),
                  "restarts": self.restart_count,
                  **fields}
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return record
