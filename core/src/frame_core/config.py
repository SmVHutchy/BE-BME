"""Laden und Typisieren von config/params.yaml.

Die Konfiguration wird beim Start einmal gelesen, streng validiert und danach
unveraendert weitergereicht. `core` ist die Quelle der Wahrheit; `sim` holt
dieselben Werte ueber GET /config.

Zwei der harten Projektregeln sind hier als Ladefehler umgesetzt und nicht nur
als Kommentar:

  - `CouplingConfig` verbietet zusaetzliche Felder. Eine siebte Kopplung laesst
    die Anwendung nicht mehr starten (Expose 6.3).
  - `Config` verbietet zusaetzliche Abschnitte. Ein `interaction:`-Block, der
    die laut Expose 6.5 offene Entwurfsentscheidung stillschweigend vorwegnimmt,
    faellt beim Start auf.

Der Konfigurationshash geht in jeden Lauf und jeden Snapshot: Ohne ihn ist
spaeter nicht feststellbar, mit welchen Parametern eine Zeitreihe entstanden
ist.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

# Alle Modelle verbieten unbekannte Felder. Ein Tippfehler in params.yaml soll
# beim Start auffallen und nicht stillschweigend einen Vorgabewert benutzen -
# bei einem System, das monatelang unbeaufsichtigt laeuft, ist das der
# Unterschied zwischen einem Fehler und einer falschen Messreihe.
_STRICT = ConfigDict(extra="forbid")


# --- Lauf -------------------------------------------------------------------

class RunConfig(BaseModel):
    model_config = _STRICT
    seed: int
    name: str


# --- Simulation -------------------------------------------------------------

class GridConfig(BaseModel):
    model_config = _STRICT
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class SimConfig(BaseModel):
    model_config = _STRICT
    grid: GridConfig
    tick_hz: float = Field(gt=0.0)
    dt_base: float = Field(gt=0.0)
    # Zeitraffer. Betriebsgroesse, keine Kopplung. Obergrenze 1000, weil mit
    # dt_base = 0.1 (Echtzeit bei speed = 1) sechs Wochen erst ab etwa 500-fach
    # in zwei Stunden durchlaufen - siehe params.yaml und annahmen.md A11.
    speed: float = Field(ge=1.0, le=1000.0)
    readback_interval_s: float = Field(gt=0.0)


# --- Felder -----------------------------------------------------------------

class NutrientFieldConfig(BaseModel):
    model_config = _STRICT
    diffusion_coefficient: float = Field(ge=0.0)
    # 1.0 = intern verlustfreier Kreislauf. Kleiner waere ein Leck und wuerde
    # die Massenbilanz brechen (Expose 6.2).
    remineralization_rate: float = Field(ge=0.0, le=1.0)
    refuge_floor: float = Field(ge=0.0)
    input_per_day_at_max: float = Field(ge=0.0)


class ProducerFieldConfig(BaseModel):
    model_config = _STRICT
    doubling_time_hours: float = Field(gt=0.0)
    light_half_saturation: float = Field(gt=0.0)
    nutrient_half_saturation: float = Field(gt=0.0)
    lifetime_hours: float = Field(gt=0.0)
    max_density: float = Field(gt=0.0)


class FieldConfig(BaseModel):
    model_config = _STRICT
    nutrient: NutrientFieldConfig
    producer: ProducerFieldConfig


class InitConfig(BaseModel):
    model_config = _STRICT
    nutrient_level: float = Field(ge=0.0)
    producer_level: float = Field(ge=0.0)
    producer_patch_scale: float = Field(gt=0.0)
    producer_patch_threshold: float = Field(ge=0.0, le=1.0)


class FlowConfig(BaseModel):
    model_config = _STRICT
    curl_noise_scale: float
    curl_noise_strength: float
    advection_dissipation: float = Field(gt=0.0, le=1.0)
    base_current_gain: float = Field(ge=0.0)


class MassConfig(BaseModel):
    model_config = _STRICT
    sedimentation_half_life_days: float = Field(gt=0.0)
    corridor_min: float = Field(gt=0.0)
    corridor_max: float = Field(gt=0.0)
    drift_tolerance_pct: float = Field(gt=0.0)


# --- Kopplungen -------------------------------------------------------------
# Sechs Eingangsgroessen, sechs Angriffspunkte, keine Ueberlappung.
# Nachweis und Begruendung: docs/mapping.md

class ClimateCoupling(BaseModel):
    """Klimakopplung mit einfacher Kennlinie: light, nutrient_input."""

    model_config = _STRICT
    source: str
    input_min: float
    input_max: float
    output_min: float
    output_max: float
    curve: Literal["linear", "sqrt"]
    smoothing_minutes: float = Field(gt=0.0)


class RateCoupling(BaseModel):
    """Temperatur auf globale Prozessgeschwindigkeit, Q10-Kennlinie."""

    model_config = _STRICT
    source: str
    curve: Literal["q10"]
    q10: float = Field(gt=0.0)
    reference_temp_c: float
    output_min: float = Field(gt=0.0)
    output_max: float = Field(gt=0.0)
    smoothing_minutes: float = Field(gt=0.0)


class WindCoupling(BaseModel):
    """Wind auf die Grundstroemung. Richtung und Betrag sind eine Groesse."""

    model_config = _STRICT
    source_direction: str
    source_speed: str
    input_min: float
    input_max: float
    output_min: float
    output_max: float
    curve: Literal["linear"]
    smoothing_minutes: float = Field(gt=0.0)


class PulseLowCoupling(BaseModel):
    """Bassband auf einen lokalen Wirbel im Stroemungsfeld."""

    model_config = _STRICT
    source: str
    gain: float = Field(ge=0.0)
    radius_cells: float = Field(gt=0.0)
    decay_seconds: float = Field(gt=0.0)
    threshold: float = Field(ge=0.0, le=1.0)


class PulseHighCoupling(BaseModel):
    """Hochtonband auf punktuelle Naehrstoffpartikel."""

    model_config = _STRICT
    source: str
    gain: float = Field(ge=0.0)
    amount: float = Field(ge=0.0)
    radius_cells: float = Field(gt=0.0)
    decay_seconds: float = Field(gt=0.0)
    threshold: float = Field(ge=0.0, le=1.0)


class CouplingConfig(BaseModel):
    """Genau sechs Kopplungen.

    `extra="forbid"` ist hier kein Stilmittel: Eine siebte Eingangsgroesse
    aendert den Gegenstand der Arbeit und soll die Anwendung nicht starten
    lassen, sondern eine Aussprache ausloesen (Expose 6.3).
    """

    model_config = _STRICT
    light: ClimateCoupling
    nutrient_input: ClimateCoupling
    rate: RateCoupling
    wind: WindCoupling
    pulse_low: PulseLowCoupling
    pulse_high: PulseHighCoupling


# --- Dienste ----------------------------------------------------------------

class EnvironmentConfig(BaseModel):
    model_config = _STRICT
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    timezone: str
    base_url: str
    archive_base_url: str
    # Realer Zeitpunkt, der Weltzeit 0 entspricht. None = Laufbeginn.
    # Wetterzeit = epoch + Weltzeit (docs/annahmen.md A11).
    epoch: datetime | None = None
    poll_interval_min: int = Field(gt=0)
    request_timeout_s: float = Field(gt=0.0)
    hourly_variables: list[str] = Field(min_length=1)
    wind_speed_unit: str
    temperature_unit: str
    precipitation_unit: str
    cache_days: int = Field(gt=0)
    stale_after_hours: float = Field(gt=0.0)
    push_interval_s: float = Field(gt=0.0)


class AudioConfig(BaseModel):
    model_config = _STRICT
    # In Prototyp 0 nur "stub". Bewusst kein Literal-Typ: Ob spaeter Raummikrofon
    # oder Loopback dahinterliegt, ist laut Expose 7.5 noch offen und soll hier
    # nicht vorentschieden werden.
    source: str
    band_low_hz: tuple[float, float]
    band_high_hz: tuple[float, float]
    envelope_attack_ms: float = Field(gt=0.0)
    envelope_release_ms: float = Field(gt=0.0)
    normalization_window_s: float = Field(gt=0.0)
    min_pulse_interval_s: float = Field(ge=0.0)


class MetricsConfig(BaseModel):
    model_config = _STRICT
    db_path: str
    weather_log_path: str
    retention_days: int = Field(gt=0)


class BloomDetectorConfig(BaseModel):
    model_config = _STRICT
    window_samples: int = Field(gt=0)
    k_mad: float = Field(gt=0.0)
    min_samples: int = Field(gt=0)
    refractory_samples: int = Field(ge=0)


class DetectorConfig(BaseModel):
    model_config = _STRICT
    bloom: BloomDetectorConfig


class ChronicleConfig(BaseModel):
    # `protected_namespaces` geleert, damit das Feld `model` nicht mit Pydantics
    # eigenem `model_`-Namensraum kollidiert.
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    backend: Literal["single", "crew"]
    language: str
    base_url: str
    model: str
    api_key: str
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0)
    reasoning_effort: str
    disable_thinking: bool
    timeout_s: float = Field(gt=0.0)
    editor_enabled: bool
    min_interval_minutes: float = Field(ge=0.0)
    guardrail_max_retries: int = Field(ge=0)


class SnapshotConfig(BaseModel):
    model_config = _STRICT
    interval_minutes: float = Field(gt=0.0)
    directory: str
    keep_last: int = Field(gt=0)


class HealthConfig(BaseModel):
    model_config = _STRICT
    path: str
    interval_s: float = Field(gt=0.0)


class ServerConfig(BaseModel):
    model_config = _STRICT
    host: str
    port: int = Field(gt=0, lt=65536)
    ws_path: str
    allowed_origins: list[str] = Field(min_length=1)


# --- Wurzel -----------------------------------------------------------------

class Config(BaseModel):
    """Die vollstaendige Konfiguration.

    `extra="forbid"` faengt hier unter anderem einen `interaction:`-Abschnitt
    ab. Die Interaktionsform ist laut Expose 6.5 ausdruecklich offen und darf
    auch nicht implizit ueber ein Konfigurationsfeld festgelegt werden.
    """

    model_config = _STRICT
    run: RunConfig
    sim: SimConfig
    field: FieldConfig
    init: InitConfig
    flow: FlowConfig
    mass: MassConfig
    coupling: CouplingConfig
    environment: EnvironmentConfig
    audio: AudioConfig
    metrics: MetricsConfig
    detector: DetectorConfig
    chronicle: ChronicleConfig
    snapshot: SnapshotConfig
    health: HealthConfig
    server: ServerConfig


class AppConfig(BaseModel):
    """Konfiguration samt Hash und Herkunft."""

    model_config = ConfigDict(frozen=True)
    values: Config
    config_hash: str
    source_path: str

    def public_dict(self) -> dict:
        """Fassung fuer GET /config, die `sim` beim Start abholt."""
        return {"config": self.values.model_dump(mode="json"),
                "config_hash": self.config_hash}


DEFAULT_CONFIG_PATH = "config/params.yaml"


def load_config(path: str | Path | None = None) -> AppConfig:
    """Liest params.yaml, validiert streng und bildet den Hash.

    Der Hash wird ueber die **Rohbytes** gebildet, nicht ueber die geparsten
    Werte: Zwei Dateien, die sich nur in Kommentaren unterscheiden, sind fuer
    die Dokumentation eines Laufs zwei verschiedene Konfigurationen.
    """
    resolved = Path(path or os.environ.get("FRAME_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    raw = resolved.read_bytes()
    config_hash = hashlib.sha256(raw).hexdigest()
    values = Config.model_validate(yaml.safe_load(raw.decode("utf-8")))

    # Betriebsvariablen duerfen Host und Port ueberschreiben - sie unterscheiden
    # sich je Maschine. Fachliche Parameter nicht: Die gehoeren in params.yaml,
    # sonst ist ein Lauf nicht mehr aus Seed und Config rekonstruierbar.
    host = os.environ.get("FRAME_HOST")
    port = os.environ.get("FRAME_PORT")
    if host or port:
        values = values.model_copy(update={"server": values.server.model_copy(
            update={"host": host or values.server.host,
                    "port": int(port) if port else values.server.port})})

    return AppConfig(values=values, config_hash=config_hash,
                     source_path=str(resolved))
