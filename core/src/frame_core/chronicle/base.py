"""Schnittstelle der Chronikpipeline.

Zwei Implementierungen hinter einem Protokoll, umschaltbar ueber
`chronicle.backend` in config/params.yaml, ohne Codeaenderung:

    SingleChronicle  ein Modellaufruf, ohne Framework - PFLICHT-RUECKFALLEBENE
    CrewChronicle    CrewAI Flow mit `chronicler` und `verifier` (Phase 3)

Warum die Rueckfallebene Pflicht ist: Zwei Agenten sind zwei Modellaufrufe je
Eintrag. Gemessen wurden 19-25 s je Aufruf auf einer RX 7600 XT; auf der
Ziel-APU mit geteiltem Speicher entsprechend mehr. Die Chronik ist im Expose
Pflichtumfang, CrewAI nicht - das Projekt darf an dieser Stelle nicht kippen.

Das Sprachmodell steht ausserhalb der Welt. Es erkennt keine Ereignisse, es
entscheidet nichts, und es schreibt nie in den Simulationszustand
(Expose 3.4 und 6.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class DetectedEvent:
    """Ein vom Regeldetektor erkanntes Ereignis samt seiner Kennzahlen.

    Was hier drinsteht, ist alles, was das Modell je zu sehen bekommt. Es hat
    keinen Zugriff auf die Datenbank, keine Werkzeuge und keinen Kontext aus
    frueheren Eintraegen - genau deshalb ist der erzeugte Text gegen
    `metrics` pruefbar.
    """

    event_type: str
    """Ereignisart, in Prototyp 0 immer "bloom"."""
    tick: int
    metrics: dict[str, float]
    """Die Kennzahlen. Jede Zahl im Text muss durch einen dieser Werte gedeckt
    sein; das prueft `frame_core.chronicle.guard`."""
    weather: dict[str, float] = field(default_factory=dict)
    """Die Wetterlage zum Zeitpunkt des Ereignisses, sofern bekannt."""

    def all_numbers(self) -> dict:
        """Kennzahlen und Wetterlage zusammen - die Belegbasis des Eintrags."""
        return {"tick": self.tick, **self.metrics, **self.weather}


@dataclass(frozen=True)
class ChronicleEntry:
    """Ein fertiger Logbucheintrag."""

    text: str
    metrics_ref: dict
    """Genau die Zahlen, die dem Modell uebergeben wurden. Landet in SQLite und
    macht jede Zahl im Text nachpruefbar (docs/annahmen.md A10)."""
    backend: str
    event_type: str
    tick: int


@runtime_checkable
class ChronicleBackend(Protocol):
    """Gemeinsamer Eintrittspunkt beider Wege."""

    name: str

    async def write(self, event: DetectedEvent) -> ChronicleEntry | None:
        """Formuliert einen Eintrag zum uebergebenen Ereignis.

        Gibt `None` zurueck, wenn kein belegbarer Eintrag zustande kam. Kein
        Eintrag ist besser als einer, der Zahlen nennt, die niemand gemessen
        hat.
        """
        ...
