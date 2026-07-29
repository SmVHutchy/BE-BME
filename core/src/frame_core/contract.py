"""Die vier Vertragsnachrichten zwischen `sim` und `core`.

Massgeblich ist docs/contract.md; dieses Modul ist dessen ausfuehrbare Fassung.
Weicht eines von beiden ab, wird zuerst das Dokument geaendert.

Unterscheidung am Schluessel der obersten Ebene - `tick`, `env`, `pulse`,
`health` -, kein Envelope und kein `type`-Feld.

Anders als in `frame_core.config` werden unbekannte Felder hier **ignoriert**
statt abgewiesen. Der Vertrag soll erweiterbar bleiben, ohne dass eine aeltere
Gegenseite abstuerzt: Wenn `sim` nach einem Update ein Feld mehr sendet, muss
ein noch nicht aktualisiertes `core` weiterlaufen.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_LENIENT = ConfigDict(extra="ignore")


# --- sim -> core: Metriken --------------------------------------------------

class MassMetrics(BaseModel):
    """Feldsummen und die kumulativen Bilanzposten."""

    model_config = _LENIENT

    nutrient: float = Field(ge=0.0)
    producer: float = Field(ge=0.0)
    # In Prototyp 0 konstant 0.0 - Konsumenten kommen erst in Prototyp 1. Das
    # Feld bleibt im Vertrag, damit dieser stabil bleibt.
    consumer: float = Field(ge=0.0, default=0.0)
    total: float = Field(ge=0.0)

    # Erweiterung gegenueber der urspruenglichen Vertragsvorgabe
    # (docs/annahmen.md A4): Ohne diese beiden kumulativen Summen laesst sich
    # der Residualsaldo nicht bilden, und "Massendrift unter 2 %" waere nicht
    # nachweisbar. Vorgabewert 0.0, damit ein Lauf ohne aeusseren Austausch
    # (Zeitrafferlauf ohne Wetter) trotzdem gueltige Nachrichten sendet.
    inflow_total: float = Field(ge=0.0, default=0.0)
    outflow_total: float = Field(ge=0.0, default=0.0)


class MetricsMessage(BaseModel):
    """Alle 5 s Wanduhrzeit von `sim`."""

    model_config = _LENIENT

    t: str
    """Zeitstempel ISO-8601 mit Zeitzone."""
    tick: int = Field(ge=0)
    """Zaehlt Simulationsschritte, nicht Bilder."""
    mass: MassMetrics
    # In Prototyp 0 konstant 1 - Vererbung kommt erst in Prototyp 1.
    lineages: int = Field(ge=0, default=1)
    # In Prototyp 0 leer.
    gene_median: dict[str, float] = Field(default_factory=dict)
    occupancy: float = Field(ge=0.0, le=1.0, default=0.0)
    """Anteil der Zellen mit Biomasse ueber Schwelle."""


# --- core -> sim: Klimakanal ------------------------------------------------

class WindEnv(BaseModel):
    model_config = _LENIENT
    dir_deg: float = Field(ge=0.0, lt=360.0)
    """Meteorologische Konvention: Richtung, AUS der der Wind weht."""
    speed: float = Field(ge=0.0, le=1.0)


class EnvValues(BaseModel):
    """Die vier Klimakopplungen, bereits abgebildet und dimensionslos."""

    model_config = _LENIENT
    light: float = Field(ge=0.0, le=1.0)
    nutrient_input: float = Field(ge=0.0, le=1.0)
    rate: float = Field(gt=0.0)
    """Multiplikator auf den Zeitschritt: dt_eff = dt_base * rate * speed."""
    wind: WindEnv


class EnvMessage(BaseModel):
    model_config = _LENIENT
    env: EnvValues


# --- core -> sim: Ereigniskanal ---------------------------------------------

class PulseValues(BaseModel):
    model_config = _LENIENT
    band: Literal["low", "high"]
    """low -> Impuls ins Stroemungsfeld, high -> punktuelle Naehrstoffpartikel."""
    level: float = Field(ge=0.0, le=1.0)


class PulseMessage(BaseModel):
    model_config = _LENIENT
    pulse: PulseValues


# --- sim -> core: Betriebstelemetrie ----------------------------------------

class HealthValues(BaseModel):
    """Bildzeit und Speicher. KEIN Simulationszustand.

    Kein Wert aus dieser Nachricht fliesst in Metrikzeitreihe, Detektor oder
    Chronik (docs/annahmen.md A3).
    """

    model_config = _LENIENT
    t: str
    tick: int = Field(ge=0)
    frame_ms: float = Field(ge=0.0)
    sim_hz: float = Field(ge=0.0)
    # `performance.memory` ist nicht standardisiert - unter Chromium vorhanden,
    # sonst null.
    heap_mb: float | None = None
    gl_context_lost: int = Field(ge=0, default=0)
    speed: float = Field(gt=0.0, default=1.0)
    """Zeitrafferfaktor. Wird mitgesendet, damit spaeter ersichtlich bleibt, ob
    ein Abschnitt der Zeitreihe im Zeitraffer entstanden ist."""


class HealthMessage(BaseModel):
    model_config = _LENIENT
    health: HealthValues


# --- Eingangsunterscheidung -------------------------------------------------

IncomingMessage = MetricsMessage | HealthMessage


def parse_incoming(payload: dict) -> IncomingMessage | None:
    """Erkennt eine Nachricht von `sim` am Schluessel der obersten Ebene.

    Gibt `None` zurueck, wenn die Nachricht zu keiner bekannten Art gehoert.
    Das ist kein Fehler: Eine neuere `sim`-Fassung darf Nachrichtenarten
    senden, die dieses `core` noch nicht kennt, ohne die Verbindung zu
    zerreissen.
    """
    if "health" in payload:
        return HealthMessage.model_validate(payload)
    if "tick" in payload:
        return MetricsMessage.model_validate(payload)
    return None
