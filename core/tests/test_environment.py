"""Tests des Umweltdienstes: Interpolation und Fortschreibung."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from frame_core.environment.client import WeatherSample, parse_forecast
from frame_core.environment.service import EnvironmentService, covers, interpolate_at

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


# --- Weltzeit statt Wanduhrzeit (A11) ---------------------------------------

def test_covers_erkennt_ob_nachgeladen_werden_muss():
    """Die Bedingung, an der der erste Zeitrafferlauf gescheitert ist.

    Ohne diese Pruefung haette `core` die Stundenwerte des Startzeitpunkts
    behalten, waehrend die Weltzeit im Zeitraffer daran vorbeigelaufen ist -
    dreizehn Welttage Dauernacht, Biomasse auf null.
    """
    samples = stundenwerte()
    assert covers(samples, BASIS + timedelta(minutes=30))
    assert not covers(samples, BASIS + timedelta(days=3))
    assert not covers(samples, BASIS - timedelta(hours=1))
    assert not covers([], BASIS)


def test_weltzeit_wird_ueber_die_epoche_auf_wetterzeit_abgebildet(app_config):
    epoche = datetime(2026, 6, 15, tzinfo=UTC)
    config = app_config.model_copy(update={
        "values": app_config.values.model_copy(update={
            "environment": app_config.values.environment.model_copy(update={"epoch": epoche})
        })
    })
    service = EnvironmentService(config)

    assert service.epoch == epoche
    assert service.weather_time(0.0) == epoche
    assert service.weather_time(3600.0) == epoche + timedelta(hours=1)
    # Sechs Wochen Weltzeit landen sechs Wochen nach der Epoche - unabhaengig
    # davon, wie lange der Lauf in Wanduhrzeit gedauert hat.
    assert service.weather_time(6 * 7 * 86400.0) == epoche + timedelta(weeks=6)


def test_ohne_epoche_gilt_der_laufbeginn(app_config):
    """Feldbetrieb: Weltzeit 0 ist jetzt, und weil eine Weltsekunde je
    Wanduhrsekunde vergeht, faellt die Wetterzeit mit der Wirklichkeit
    zusammen.

    Die Epoche wird hier ausdruecklich auf None gesetzt, statt sich auf die
    ausgelieferte params.yaml zu verlassen: Dort ist sie ein LAUFPARAMETER wie
    run.seed und steht waehrend eines Zeitrafferlaufs in der Vergangenheit.
    Ein Test, der an so einem Wert haengt, prueft die Laune des letzten Laufs.
    """
    config = app_config.model_copy(update={
        "values": app_config.values.model_copy(update={
            "environment": app_config.values.environment.model_copy(update={"epoch": None})
        })
    })
    service = EnvironmentService(config)
    abstand = abs((service.epoch - datetime.now(UTC)).total_seconds())
    assert abstand < 5.0


def test_echtzeit_im_feldbetrieb(app_config):
    """Die Eigenschaft, die A11 zugrunde liegt.

    Bei speed = 1 muss genau eine Weltsekunde je Wanduhrsekunde vergehen.
    Andernfalls driften Weltzeit und Wirklichkeit auseinander, und der
    Klimakanal kann das reale Wetter nicht mehr tragen - die Kernpraemisse der
    Arbeit.
    """
    sim = app_config.values.sim
    weltsekunden_je_wanduhrsekunde = sim.dt_base * sim.tick_hz * 1.0
    assert weltsekunden_je_wanduhrsekunde == pytest.approx(1.0)


def test_stabilitaetsgrenze_der_diffusion_haelt(app_config):
    """Expliziter Euler-Schritt: diffusion * dt_eff muss unter 0.25 bleiben.

    `sim` prueft das beim Start ebenfalls und bricht ab; hier steht es als
    Regressionsschutz, damit eine Aenderung an dt_base, der Diffusion oder der
    oberen Rate-Klammer nicht erst im Browser auffaellt.
    """
    values = app_config.values
    faktor = (values.field.nutrient.diffusion_coefficient
              * values.sim.dt_base * values.coupling.rate.output_max)
    assert faktor < 0.25


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
