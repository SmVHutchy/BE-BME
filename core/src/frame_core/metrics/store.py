"""Metrikspeicher auf SQLite.

Haelt die Zeitreihe des Systemzustands, die je Tick angewandten Klimawerte und
die Chronikeintraege.

Die Tabelle `env_applied` ist kein Beiwerk: Ohne die Aufzeichnung, welche
env-Werte bei welchem Tick galten, laesst sich ein Lauf nicht rekonstruieren -
die Glaettung haengt vom Zeitpunkt der Nachfuehrung ab, und der ist aus den
Rohdaten allein nicht ableitbar.

Jede Chronikzeile fuehrt in `metrics_ref` genau die Zahlen mit, die dem
Sprachmodell uebergeben wurden. Das ist die Grundlage der Abnahmebedingung fuer
Phase 3 und der Grund, warum der Chroniktext ueberpruefbar ist, obwohl er nicht
reproduzierbar ist (docs/annahmen.md A10).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from frame_core.contract import EnvValues, MetricsMessage

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    seed         INTEGER NOT NULL,
    config_hash  TEXT    NOT NULL,
    started_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL REFERENCES runs(id),
    t             TEXT    NOT NULL,
    tick          INTEGER NOT NULL,
    nutrient      REAL    NOT NULL,
    producer      REAL    NOT NULL,
    consumer      REAL    NOT NULL,
    total         REAL    NOT NULL,
    inflow_total  REAL    NOT NULL,
    outflow_total REAL    NOT NULL,
    lineages      INTEGER NOT NULL,
    occupancy     REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_metrics_run_tick ON metrics(run_id, tick);

CREATE TABLE IF NOT EXISTS env_applied (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER NOT NULL REFERENCES runs(id),
    t              TEXT    NOT NULL,
    light          REAL    NOT NULL,
    nutrient_input REAL    NOT NULL,
    rate           REAL    NOT NULL,
    wind_dir_deg   REAL    NOT NULL,
    wind_speed     REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_env_run_t ON env_applied(run_id, t);

CREATE TABLE IF NOT EXISTS chronicle_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES runs(id),
    t           TEXT    NOT NULL,
    tick        INTEGER NOT NULL,
    event_type  TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    metrics_ref TEXT    NOT NULL,
    backend     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chronicle_run_t ON chronicle_entries(run_id, t DESC);
"""


@dataclass(frozen=True)
class ChronicleRow:
    id: int
    t: str
    tick: int
    event_type: str
    text: str
    metrics_ref: dict
    backend: str

    def as_dict(self) -> dict:
        return {"id": self.id, "t": self.t, "tick": self.tick,
                "event_type": self.event_type, "text": self.text,
                "metrics_ref": self.metrics_ref, "backend": self.backend}


class MetricsStore:
    """Duenne Huelle um SQLite. Bewusst synchron.

    Das Schreibaufkommen liegt bei einer Zeile alle 5 Sekunden; eine
    asynchrone Datenbankschicht waere hier zusaetzliche Fehlerquelle ohne
    Gegenwert. Ein Lock genuegt, weil FastAPI die Zugriffe aus mehreren
    Aufgaben heraus ausloest.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # WAL: Lesen waehrend eines Schreibvorgangs blockiert nicht. Im
        # Dauerbetrieb wird waehrend laufender Messung ueber GET /chronicle
        # gelesen.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- Laeufe -------------------------------------------------------------

    def start_run(self, name: str, seed: int, config_hash: str) -> int:
        """Legt einen Lauf an und gibt seine id zurueck.

        Seed und Konfigurationshash stehen am Lauf, nicht an der Einzelmessung:
        Sie gelten fuer den ganzen Lauf, und genau dieses Tripel macht ihn
        zusammen mit dem Wetter-Rohlog rekonstruierbar.
        """
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO runs (name, seed, config_hash, started_at) VALUES (?, ?, ?, ?)",
                (name, seed, config_hash, datetime.now(UTC).isoformat()),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    # --- Metriken -----------------------------------------------------------

    def insert_metrics(self, run_id: int, message: MetricsMessage) -> None:
        mass = message.mass
        with self._lock:
            self._conn.execute(
                """INSERT INTO metrics
                   (run_id, t, tick, nutrient, producer, consumer, total,
                    inflow_total, outflow_total, lineages, occupancy)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, message.t, message.tick, mass.nutrient, mass.producer,
                 mass.consumer, mass.total, mass.inflow_total, mass.outflow_total,
                 message.lineages, message.occupancy),
            )
            self._conn.commit()

    def recent_producer_series(self, run_id: int, limit: int) -> list[float]:
        """Die juengsten Produzentenwerte, aelteste zuerst.

        Reihenfolge ist wichtig: Der Detektor erwartet eine chronologische
        Zeitreihe, SQLite liefert bei DESC die umgekehrte.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT producer FROM metrics WHERE run_id = ? ORDER BY tick DESC LIMIT ?",
                (run_id, limit),
            ).fetchall()
        return [float(row["producer"]) for row in reversed(rows)]

    def first_total(self, run_id: int) -> float | None:
        """Startmasse des Laufs - Bezugsgroesse der Massenbilanz."""
        with self._lock:
            row = self._conn.execute(
                "SELECT total FROM metrics WHERE run_id = ? ORDER BY tick ASC LIMIT 1",
                (run_id,),
            ).fetchone()
        return float(row["total"]) if row else None

    def metrics_count(self, run_id: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM metrics WHERE run_id = ?", (run_id,)
            ).fetchone()
        return int(row["n"])

    # --- Angewandte Klimawerte ---------------------------------------------

    def insert_env(self, run_id: int, env: EnvValues, when: datetime | None = None) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO env_applied
                   (run_id, t, light, nutrient_input, rate, wind_dir_deg, wind_speed)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, (when or datetime.now(UTC)).isoformat(), env.light,
                 env.nutrient_input, env.rate, env.wind.dir_deg, env.wind.speed),
            )
            self._conn.commit()

    # --- Chronik ------------------------------------------------------------

    def insert_chronicle_entry(self, run_id: int, tick: int, event_type: str,
                               text: str, metrics_ref: dict, backend: str,
                               when: datetime | None = None) -> int:
        with self._lock:
            cursor = self._conn.execute(
                """INSERT INTO chronicle_entries
                   (run_id, t, tick, event_type, text, metrics_ref, backend)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, (when or datetime.now(UTC)).isoformat(), tick, event_type,
                 text, json.dumps(metrics_ref, ensure_ascii=False), backend),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    def recent_chronicle_entries(self, limit: int = 20,
                                 since: str | None = None) -> list[ChronicleRow]:
        query = "SELECT * FROM chronicle_entries"
        params: list = []
        if since:
            query += " WHERE t > ?"
            params.append(since)
        query += " ORDER BY t DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [ChronicleRow(id=row["id"], t=row["t"], tick=row["tick"],
                             event_type=row["event_type"], text=row["text"],
                             metrics_ref=json.loads(row["metrics_ref"]),
                             backend=row["backend"]) for row in rows]

    def last_chronicle_time(self, run_id: int) -> datetime | None:
        """Fuer den Mindestabstand zwischen zwei Eintraegen."""
        with self._lock:
            row = self._conn.execute(
                "SELECT t FROM chronicle_entries WHERE run_id = ? ORDER BY id DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        return datetime.fromisoformat(row["t"]) if row else None
