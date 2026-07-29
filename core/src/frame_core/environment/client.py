"""Open-Meteo-Abruf.

Holt genau die fuenf Groessen, die die vier Klimakopplungen brauchen - keine
auf Vorrat. Kein API-Schluessel noetig; der Bedarf liegt bei 24 Abrufen
taeglich gegen ein Freikontingent von 10.000 (Expose 3.5).

Wetterdaten von Open-Meteo.com, lizenziert unter CC BY 4.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from frame_core.config import EnvironmentConfig


@dataclass(frozen=True)
class WeatherSample:
    """Ein Stundenwert, wie ihn Open-Meteo liefert."""

    time: datetime
    values: dict[str, float]


@dataclass(frozen=True)
class WeatherForecast:
    """Rohantwort und die daraus gelesenen Stundenwerte."""

    raw: dict
    samples: list[WeatherSample]

    @property
    def covered_until(self) -> datetime | None:
        return self.samples[-1].time if self.samples else None


class OpenMeteoError(RuntimeError):
    """Abruf fehlgeschlagen. Der Aufrufer schreibt die letzten bekannten Werte
    fort und protokolliert den Ausfall (Expose Risiko 8)."""


def build_params(config: EnvironmentConfig) -> dict[str, str]:
    return {
        "latitude": str(config.latitude),
        "longitude": str(config.longitude),
        "hourly": ",".join(config.hourly_variables),
        "timezone": config.timezone,
        "wind_speed_unit": config.wind_speed_unit,
        "temperature_unit": config.temperature_unit,
        "precipitation_unit": config.precipitation_unit,
        # Ein Tag rueckwaerts deckt einen Neustart ab, ohne dass eine Luecke
        # entsteht; zwei Tage vorwaerts ueberbruecken einen Netzausfall, ohne
        # dass sofort fortgeschrieben werden muss.
        "past_days": "1",
        "forecast_days": "2",
    }


def parse_forecast(payload: dict, variables: list[str]) -> WeatherForecast:
    """Liest die Stundenwerte aus einer Rohantwort.

    Der von Open-Meteo mitgelieferte `utc_offset_seconds` wird benutzt, statt
    die Zeitzone selbst aufzuloesen: Die Zeitstempel sind dann exakt die der
    Quelle, auch ueber Sommerzeitwechsel hinweg.
    """
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    offset = timedelta(seconds=int(payload.get("utc_offset_seconds", 0)))
    tzinfo = timezone(offset)

    samples: list[WeatherSample] = []
    for index, stamp in enumerate(times):
        values: dict[str, float] = {}
        for name in variables:
            series = hourly.get(name)
            if series is None or index >= len(series):
                continue
            value = series[index]
            # Open-Meteo liefert null, wo ein Wert fehlt. Solche Stunden werden
            # uebersprungen statt auf 0 gesetzt - null Globalstrahlung waere
            # Nacht, und das ist etwas anderes als "unbekannt".
            if value is None:
                continue
            values[name] = float(value)
        if len(values) == len(variables):
            samples.append(WeatherSample(
                time=datetime.fromisoformat(stamp).replace(tzinfo=tzinfo),
                values=values,
            ))

    return WeatherForecast(raw=payload, samples=samples)


async def fetch_forecast(config: EnvironmentConfig,
                         client: httpx.AsyncClient | None = None) -> WeatherForecast:
    """Ruft die Vorhersage ab. Wirft `OpenMeteoError` bei jedem Fehlschlag."""
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=config.request_timeout_s)
    try:
        response = await http.get(config.base_url, params=build_params(config))
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OpenMeteoError(f"Open-Meteo nicht erreichbar: {exc}") from exc
    finally:
        if owns_client:
            await http.aclose()

    forecast = parse_forecast(payload, config.hourly_variables)
    if not forecast.samples:
        raise OpenMeteoError("Antwort enthielt keine vollstaendigen Stundenwerte")
    return forecast
