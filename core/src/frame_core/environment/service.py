"""Umweltdienst: Abruf, Cache, Interpolation, Abbildung, Glaettung.

Der Klimakanal. Vier der sechs Kopplungen entstehen hier
(docs/mapping.md, Zeilen 1-4).

Ablauf je Nachfuehrung:

    Stundenwerte  ->  Interpolation auf jetzt  ->  Kennlinie  ->  Glaettung
    (Open-Meteo)      (linear zwischen zwei)      (mapping.py)   (Zeitkonstante)

Bei Netzausfall wird der letzte bekannte Stundenwert fortgeschrieben. Der
Ausfall bleibt im Bild unsichtbar, wird aber protokolliert - so verlangt es
Risiko 8. Erst nach `environment.stale_after_hours` gilt der Dienst als
ausgefallen und der Zustand wandert ins Health-Log.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from frame_core.config import AppConfig
from frame_core.contract import EnvValues, WindEnv
from frame_core.environment.client import (
    OpenMeteoError,
    WeatherSample,
    fetch_forecast,
)
from frame_core.environment.mapping import map_climate, map_rate, map_wind, smooth, smooth_angle
from frame_core.environment.rawlog import WeatherRawLog

logger = logging.getLogger(__name__)


def interpolate_at(samples: Sequence[WeatherSample], when: datetime) -> dict[str, float]:
    """Linear zwischen den beiden umgebenden Stundenwerten.

    Ausserhalb der abgedeckten Spanne wird der Randwert **fortgeschrieben**,
    nicht extrapoliert. Das ist zugleich die Rueckfallebene bei Netzausfall: Der
    letzte bekannte Wert gilt weiter, statt dass das Bild einfriert oder
    springt (Expose Risiko 8).
    """
    if not samples:
        raise ValueError("keine Stundenwerte vorhanden")

    if when <= samples[0].time:
        return dict(samples[0].values)
    if when >= samples[-1].time:
        return dict(samples[-1].values)

    for earlier, later in zip(samples, samples[1:], strict=False):
        if earlier.time <= when <= later.time:
            span = (later.time - earlier.time).total_seconds()
            if span <= 0.0:
                return dict(earlier.values)
            ratio = (when - earlier.time).total_seconds() / span
            return {
                name: earlier.values[name] + ratio * (later.values[name] - earlier.values[name])
                for name in earlier.values
                if name in later.values
            }

    return dict(samples[-1].values)


@dataclass
class _SmoothingState:
    """Geglaettete Werte je Kopplung, mit eigener Zeitkonstante."""

    light: float | None = None
    nutrient_input: float | None = None
    rate: float | None = None
    wind_dir_deg: float | None = None
    wind_speed: float | None = None
    last_update: datetime | None = None

    def initialised(self) -> bool:
        return self.last_update is not None


@dataclass
class EnvironmentStatus:
    """Betriebszustand des Klimakanals, fuer das Health-Log."""

    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    sample_count: int = 0
    failure_reason: str | None = None

    def is_stale(self, now: datetime, stale_after_hours: float) -> bool:
        if self.last_success is None:
            return True
        return (now - self.last_success).total_seconds() > stale_after_hours * 3600.0

    def as_dict(self, now: datetime, stale_after_hours: float) -> dict:
        return {
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "consecutive_failures": self.consecutive_failures,
            "sample_count": self.sample_count,
            "failure_reason": self.failure_reason,
            "stale": self.is_stale(now, stale_after_hours),
        }


class EnvironmentService:
    """Haelt die aktuellen Klimawerte und fuehrt sie nach."""

    def __init__(self, app_config: AppConfig, rawlog: WeatherRawLog | None = None) -> None:
        self._app = app_config
        self._config = app_config.values.environment
        self._coupling = app_config.values.coupling
        self._rawlog = rawlog
        self._samples: list[WeatherSample] = []
        self._smoothing = _SmoothingState()
        self.status = EnvironmentStatus()

    @property
    def samples(self) -> list[WeatherSample]:
        return list(self._samples)

    async def refresh(self, client: httpx.AsyncClient | None = None) -> bool:
        """Holt neue Stundenwerte. Gibt zurueck, ob der Abruf gelang.

        Ein Fehlschlag wirft nicht: Die Welt laeuft auf den letzten bekannten
        Werten weiter, und der Ausfall gehoert protokolliert, nicht eskaliert.
        """
        try:
            forecast = await fetch_forecast(self._config, client)
        except OpenMeteoError as exc:
            self.status.last_failure = datetime.now(UTC)
            self.status.consecutive_failures += 1
            self.status.failure_reason = str(exc)
            logger.warning("Klimakanal: Abruf fehlgeschlagen (%d in Folge): %s",
                           self.status.consecutive_failures, exc)
            return False

        # Rohdaten VOR jeder Verarbeitung wegschreiben.
        if self._rawlog is not None:
            self._rawlog.append(forecast.raw,
                                config_hash=self._app.config_hash,
                                run_name=self._app.values.run.name)

        self._samples = forecast.samples
        self.status.last_success = datetime.now(UTC)
        self.status.consecutive_failures = 0
        self.status.failure_reason = None
        self.status.sample_count = len(forecast.samples)
        logger.info("Klimakanal: %d Stundenwerte bis %s",
                    len(forecast.samples), forecast.covered_until)
        return True

    def current_env(self, now: datetime | None = None) -> EnvValues | None:
        """Abgebildete und geglaettete Klimawerte fuer den Vertrag.

        `None`, solange noch keine Wetterdaten vorliegen - dann wird auch nichts
        gesendet. `sim` rechnet in diesem Fall mit seinen Vorgabewerten weiter,
        statt dass hier ein erfundener Wert entsteht.
        """
        if not self._samples:
            return None

        now = now or datetime.now(UTC)
        raw = interpolate_at(self._samples, now)

        light_target = map_climate(raw[self._coupling.light.source], self._coupling.light)
        nutrient_target = map_climate(raw[self._coupling.nutrient_input.source],
                                      self._coupling.nutrient_input)
        rate_target = map_rate(raw[self._coupling.rate.source], self._coupling.rate)
        wind_target = map_wind(raw[self._coupling.wind.source_direction],
                               raw[self._coupling.wind.source_speed],
                               self._coupling.wind)

        state = self._smoothing
        if not state.initialised():
            # Beim ersten Wert nicht einschwingen lassen. Sonst startet die Welt
            # dunkel und kalt und braucht Stunden, bis sie das tatsaechliche
            # Wetter erreicht - beim Wiederanlauf nach einem Absturz waere das
            # ein sichtbarer Sprung ohne Ursache in der Umgebung.
            state.light = light_target
            state.nutrient_input = nutrient_target
            state.rate = rate_target
            state.wind_dir_deg = wind_target.dir_deg
            state.wind_speed = wind_target.speed
        else:
            dt = (now - state.last_update).total_seconds()
            state.light = smooth(state.light, light_target, dt,
                                 self._coupling.light.smoothing_minutes)
            state.nutrient_input = smooth(state.nutrient_input, nutrient_target, dt,
                                          self._coupling.nutrient_input.smoothing_minutes)
            state.rate = smooth(state.rate, rate_target, dt,
                                self._coupling.rate.smoothing_minutes)
            state.wind_dir_deg = smooth_angle(state.wind_dir_deg, wind_target.dir_deg, dt,
                                              self._coupling.wind.smoothing_minutes)
            state.wind_speed = smooth(state.wind_speed, wind_target.speed, dt,
                                      self._coupling.wind.smoothing_minutes)
        state.last_update = now

        return EnvValues(
            light=min(1.0, max(0.0, state.light)),
            nutrient_input=min(1.0, max(0.0, state.nutrient_input)),
            rate=state.rate,
            wind=WindEnv(dir_deg=state.wind_dir_deg % 360.0,
                         speed=min(1.0, max(0.0, state.wind_speed))),
        )

    def status_dict(self, now: datetime | None = None) -> dict:
        return self.status.as_dict(now or datetime.now(UTC), self._config.stale_after_hours)
