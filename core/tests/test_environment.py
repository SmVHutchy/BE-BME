"""Tests des Umweltdienstes: Interpolation und Fortschreibung."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from frame_core.environment.client import WeatherSample, parse_forecast
from frame_core.environment.service import interpolate_at

BASIS = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def stundenwerte() -> list[WeatherSample]:
    return [
        WeatherSample(time=BASIS, values={"temperature_2m": 10.0, "precipitation": 0.0}),
        WeatherSample(time=BASIS + timedelta(hours=1),
                      values={"temperature_2m": 20.0, "precipitation": 4.0}),
        WeatherSample(time=BASIS + timedelta(hours=2),
                      values={"temperature_2m": 14.0, "precipitation": 0.0}),
    ]


def test_exakter_stundenwert_wird_unveraendert_geliefert():
    werte = interpolate_at(stundenwerte(), BASIS + timedelta(hours=1))
    assert werte["temperature_2m"] == pytest.approx(20.0)


def test_zwischen_zwei_stunden_wird_linear_interpoliert():
    werte = interpolate_at(stundenwerte(), BASIS + timedelta(minutes=30))
    assert werte["temperature_2m"] == pytest.approx(15.0)
    assert werte["precipitation"] == pytest.approx(2.0)


def test_vor_dem_ersten_wert_gilt_der_erste():
    werte = interpolate_at(stundenwerte(), BASIS - timedelta(hours=5))
    assert werte["temperature_2m"] == pytest.approx(10.0)


def test_nach_dem_letzten_wert_wird_fortgeschrieben():
    """Die Rueckfallebene bei Netzausfall (Expose Risiko 8).

    Der letzte bekannte Wert gilt weiter. Es wird ausdruecklich **nicht**
    extrapoliert - sonst liefe die Temperatur bei laengerem Ausfall in
    beliebige Werte davon und das Bild wuerde sichtbar falsch, statt
    unauffaellig stehenzubleiben.
    """
    werte = interpolate_at(stundenwerte(), BASIS + timedelta(hours=50))
    assert werte["temperature_2m"] == pytest.approx(14.0)


def test_ohne_stundenwerte_wird_nicht_geraten():
    with pytest.raises(ValueError):
        interpolate_at([], BASIS)


# --- Antwort von Open-Meteo lesen -------------------------------------------

def test_parse_forecast_setzt_die_zeitzone_der_quelle():
    payload = {
        "utc_offset_seconds": 7200,
        "hourly": {
            "time": ["2026-09-01T12:00", "2026-09-01T13:00"],
            "temperature_2m": [18.0, 19.0],
        },
    }
    forecast = parse_forecast(payload, ["temperature_2m"])
    assert len(forecast.samples) == 2
    assert forecast.samples[0].time.utcoffset() == timedelta(hours=2)


def test_parse_forecast_ueberspringt_luecken():
    """Fehlende Werte sind nicht null.

    Open-Meteo liefert `null`, wo ein Wert fehlt. Als 0 eingesetzt waere das
    bei der Globalstrahlung "Nacht" - etwas ganz anderes als "unbekannt".
    """
    payload = {
        "utc_offset_seconds": 0,
        "hourly": {
            "time": ["2026-09-01T12:00", "2026-09-01T13:00", "2026-09-01T14:00"],
            "temperature_2m": [18.0, None, 20.0],
        },
    }
    forecast = parse_forecast(payload, ["temperature_2m"])
    assert [s.values["temperature_2m"] for s in forecast.samples] == [18.0, 20.0]


def test_parse_forecast_verlangt_alle_angeforderten_groessen():
    # Eine Stunde, in der eine der vier Kopplungsgroessen fehlt, ist unbrauchbar:
    # Sonst entstuende ein env-Satz aus teils aktuellen, teils alten Werten.
    payload = {
        "utc_offset_seconds": 0,
        "hourly": {
            "time": ["2026-09-01T12:00"],
            "temperature_2m": [18.0],
        },
    }
    forecast = parse_forecast(payload, ["temperature_2m", "precipitation"])
    assert forecast.samples == []
