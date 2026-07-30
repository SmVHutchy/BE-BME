"""Umweltdienst: Abruf, Cache, Interpolation, Abbildung, Glaettung.

Der Klimakanal. Vier der sechs Kopplungen entstehen hier
(docs/mapping.md, Zeilen 1-4).

Ablauf je Nachfuehrung:

    Weltzeit -> Wetterzeit -> Interpolation -> Kennlinie -> Glaettung
                (epoch +)     (zwischen zwei   (mapping.py)  (Zeitkonstante
                              Stundenwerten)                  in Weltzeit)

**Alles rechnet in Weltzeit, nicht in Wanduhrzeit.** Das ist die Behebung von
A11: Zuvor bildete dieser Dienst das Wetter auf *jetzt* ab, waehrend `sim` im
Zeitraffer voraus lief. In einem Lauf ueber 13,6 Welttage vergingen draussen
64 Sekunden - die Welt hatte also durchgehend Nacht, und die Produzenten sind
verhungert. Der Zeitraffer prueft damit das Gegenteil dessen, was er soll.

    Wetterzeit = epoch + Weltzeit

Im Feldbetrieb ist `epoch` der Laufbeginn und eine Weltsekunde vergeht je
Wanduhrsekunde - Wetterzeit und Wirklichkeit fallen zusammen. In einem
Zeitrafferlauf liegt `epoch` in der Vergangenheit, und der Lauf spielt echtes
Archivwetter beschleunigt ab.

Bei Netzausfall wird der letzte bekannte Stundenwert fortgeschrieben. Der
Ausfall bleibt im Bild unsichtbar, wird aber protokolliert (Risiko 8).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from frame_core.config import AppConfig
from frame_core.contract import EnvValues, WindEnv
from frame_core.environment.client import (
    OpenMeteoError,
    WeatherSample,
    fetch_archive,
    fetch_forecast,
)
from frame_core.environment.mapping import map_climate, map_rate, map_wind, smooth, smooth_angle
from frame_core.environment.rawlog import WeatherRawLog

logger = logging.getLogger(__name__)

# Ab welchem Abstand zur Gegenwart der Archivdienst statt der Vorhersage
# gebraucht wird. Die Vorhersage deckt mit past_days=1 und forecast_days=2 rund
# drei Tage ab; darunter bleibt Reserve fuer einen laufenden Zeitrafferlauf.
_FORECAST_REACH = timedelta(days=1)


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


def covers(samples: Sequence[WeatherSample], when: datetime) -> bool:
    """Liegt `when` innerhalb der geladenen Stundenwerte?

    Getrennt von `interpolate_at`, weil dort ausserhalb bewusst fortgeschrieben
    wird. Hier geht es um die andere Frage: Muessen neue Daten geholt werden?
    """
    return bool(samples) and samples[0].time <= when <= samples[-1].time


@dataclass
class _SmoothingState:
    """Geglaettete Werte je Kopplung, mit eigener Zeitkonstante."""

    light: float | None = None
    nutrient_input: float | None = None
    rate: float | None = None
    wind_dir_deg: float | None = None
    wind_speed: float | None = None
    last_world_time: float | None = None

    def initialised(self) -> bool:
        return self.last_world_time is not None


@dataclass
class EnvironmentStatus:
    """Betriebszustand des Klimakanals, fuer das Health-Log."""

    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    sample_count: int = 0
    failure_reason: str | None = None
    source: str = "none"
    """forecast | archive | none - welcher Endpunkt die Daten geliefert hat."""

    def is_stale(self, now: datetime, stale_after_hours: float) -> bool:
        if self.last_success is None:
            return True
        return (now - self.last_success).total_seconds() > stale_after_hours * 3600.0


class EnvironmentService:
    """Haelt die aktuellen Klimawerte und fuehrt sie auf der Weltzeit nach."""

    def __init__(self, app_config: AppConfig, rawlog: WeatherRawLog | None = None) -> None:
        self._app = app_config
        self._config = app_config.values.environment
        self._coupling = app_config.values.coupling
        self._rawlog = rawlog
        self._samples: list[WeatherSample] = []
        self._smoothing = _SmoothingState()
        self.status = EnvironmentStatus()

        # Weltzeit 0. Ohne Angabe der Laufbeginn - das ist der Feldbetrieb, in
        # dem Weltzeit und Wanduhrzeit ohnehin zusammenfallen.
        self.epoch = self._config.epoch or datetime.now(UTC)
        if self.epoch.tzinfo is None:
            # Ein Datum ohne Zeitzone waere mehrdeutig und wuerde die
            # Reproduzierbarkeit eines Laufs beschaedigen.
            self.epoch = self.epoch.replace(tzinfo=UTC)
        logger.info("Klimakanal: Weltzeit 0 entspricht %s", self.epoch.isoformat())

    @property
    def samples(self) -> list[WeatherSample]:
        return list(self._samples)

    def weather_time(self, world_time: float) -> datetime:
        """Der reale Zeitpunkt, dessen Wetter zur uebergebenen Weltzeit gehoert."""
        return self.epoch + timedelta(seconds=world_time)

    def needs_refresh(self, world_time: float) -> bool:
        return not covers(self._samples, self.weather_time(world_time))

    async def refresh(self, world_time: float = 0.0,
                      client: httpx.AsyncClient | None = None) -> bool:
        """Holt die Stundenwerte, die zur gegebenen Weltzeit passen.

        Waehlt den Endpunkt nach der Wetterzeit: Was weiter als einen Tag
        zurueckliegt, kommt aus dem Archiv - der Vorhersagedienst kennt es nicht
        mehr. Gibt zurueck, ob der Abruf gelang; ein Fehlschlag wirft nicht,
        sondern laesst die Welt auf den letzten bekannten Werten weiterlaufen.
        """
        target = self.weather_time(world_time)
        use_archive = target < datetime.now(UTC) - _FORECAST_REACH

        try:
            if use_archive:
                # Grosszuegig um den Zielzeitpunkt herum, damit nicht bei jedem
                # Nachfuehrschritt neu abgerufen wird.
                start = (target - timedelta(days=1)).date()
                end = (target + timedelta(days=7)).date()
                forecast = await fetch_archive(self._config, start, end, client)
                source = "archive"
            else:
                forecast = await fetch_forecast(self._config, client)
                source = "forecast"
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
        self.status.source = source
        logger.info("Klimakanal: %d Stundenwerte aus %s, %s bis %s (Wetterzeit %s)",
                    len(forecast.samples), source,
                    forecast.samples[0].time.isoformat(),
                    forecast.samples[-1].time.isoformat(), target.isoformat())
        return True

    def current_env(self, world_time: float) -> EnvValues | None:
        """Abgebildete und geglaettete Klimawerte fuer den Vertrag.

        `None`, solange noch keine Wetterdaten vorliegen - dann wird auch nichts
        gesendet, statt dass hier ein erfundener Wert entsteht.
        """
        if not self._samples:
            return None

        raw = interpolate_at(self._samples, self.weather_time(world_time))

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
            # WELTZEIT, nicht Wanduhrzeit. Die Zeitkonstanten der Kopplungen
            # (smoothing_minutes) beziehen sich auf das Wettergeschehen; im
            # Zeitraffer muss die Glaettung mit ihm mitlaufen, sonst waere sie
            # dort um den Zeitrafferfaktor zu traege.
            dt = max(0.0, world_time - (state.last_world_time or 0.0))
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
        state.last_world_time = world_time

        return EnvValues(
            light=min(1.0, max(0.0, state.light)),
            nutrient_input=min(1.0, max(0.0, state.nutrient_input)),
            rate=state.rate,
            wind=WindEnv(dir_deg=state.wind_dir_deg % 360.0,
                         speed=min(1.0, max(0.0, state.wind_speed))),
        )

    def status_dict(self, world_time: float = 0.0) -> dict:
        now = datetime.now(UTC)
        return {
            "epoch": self.epoch.isoformat(),
            "weather_time": self.weather_time(world_time).isoformat(),
            "source": self.status.source,
            "last_success": self.status.last_success.isoformat() if self.status.last_success else None,
            "last_failure": self.status.last_failure.isoformat() if self.status.last_failure else None,
            "consecutive_failures": self.status.consecutive_failures,
            "sample_count": self.status.sample_count,
            "failure_reason": self.status.failure_reason,
            "stale": self.status.is_stale(now, self._config.stale_after_hours),
        }
