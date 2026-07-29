"""Ereigniskanal: Interface und Stub.

Liefert die beiden uebrigen Kopplungen (docs/mapping.md, Zeilen 5-6):
Bassband -> Stroemungsimpuls, Hochtonband -> Naehrstoffpartikel.

In Prototyp 0 erzeugt ein Testendpunkt synthetische Pulse. **Das Interface ist
bereits das endgueltige**, die Implementierung nicht: Die echte Erfassung tritt
spaeter hinter dasselbe `PulseSource` und aendert nichts an `api` oder `sim`.

Bewusst offen gelassen (Expose 7.5): ob dahinter ein Raummikrofon oder
Audio-Loopback liegt. `PulseSource` laesst beides zu und nimmt die Entscheidung
nicht vorweg. Ebenso wenig praejudiziert dieses Modul die Interaktionsform aus
Expose 6.5 - es transportiert Pegel, keine Absichten.

Datenschutz ist Teil der Aufgabe, nicht Randbedingung: Aus einer Umsetzung
dieses Interfaces treten ausschliesslich zwei Pegelwerte aus. Keine
Inhaltsanalyse, kein Puffer ueber das FFT-Fenster hinaus, keine Speicherung.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Literal, Protocol, runtime_checkable

from frame_core.config import CouplingConfig
from frame_core.contract import PulseValues

logger = logging.getLogger(__name__)

Band = Literal["low", "high"]


@runtime_checkable
class PulseSource(Protocol):
    """Quelle von Ereignispulsen."""

    name: str

    async def next_pulse(self) -> PulseValues:
        """Wartet auf den naechsten Puls und gibt ihn zurueck."""
        ...


class StubPulseSource:
    """Synthetische Pulse aus dem Testendpunkt.

    Setzt bereits die Schwellen und den Mindestabstand aus der Konfiguration
    durch. Das gehoert hierher und nicht in die echte Erfassung: Die Regeln
    sind Teil des Mapping-Designs und sollen fuer jede Quelle gleich gelten.
    """

    name = "stub"

    def __init__(self, coupling: CouplingConfig, min_pulse_interval_s: float) -> None:
        self._coupling = coupling
        self._min_interval = min_pulse_interval_s
        self._queue: asyncio.Queue[PulseValues] = asyncio.Queue()
        self._last_emit: dict[str, float] = {}

    def _threshold(self, band: Band) -> float:
        return (self._coupling.pulse_low.threshold if band == "low"
                else self._coupling.pulse_high.threshold)

    def emit(self, band: Band, level: float) -> bool:
        """Nimmt einen Puls an. Gibt zurueck, ob er durchgelassen wurde.

        Zwei Filter, beide aus der Konfiguration:

        - `threshold` verhindert, dass Raumgrundrauschen das Bild dauerhaft in
          Bewegung haelt. Ein Objekt, das staendig zuckt, wird abgeschaltet.
        - `min_pulse_interval_s` begrenzt die Rate je Band, damit ein
          durchlaufender Bass nicht in jedem Analysefenster einen Wirbel setzt.
        """
        if level < self._threshold(band):
            logger.debug("Puls %s unter Schwelle (%.3f)", band, level)
            return False

        now = time.monotonic()
        last = self._last_emit.get(band)
        if last is not None and (now - last) < self._min_interval:
            logger.debug("Puls %s innerhalb des Mindestabstands", band)
            return False

        self._last_emit[band] = now
        self._queue.put_nowait(PulseValues(band=band, level=min(1.0, max(0.0, level))))
        return True

    async def next_pulse(self) -> PulseValues:
        return await self._queue.get()
