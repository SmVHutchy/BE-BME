"""Tests der vier Klimakopplungen.

Das Mapping ist der Beitrag der Arbeit; hier wird geprueft, dass die
ausgelieferten Kennlinien das tun, was docs/mapping.md behauptet.
"""

from __future__ import annotations

import math

import pytest

from frame_core.environment.mapping import (
    apply_curve,
    map_climate,
    map_rate,
    map_wind,
    normalize,
    smooth,
    smooth_angle,
)


# --- Grundbausteine ---------------------------------------------------------

def test_normalize_klammert_statt_zu_extrapolieren():
    # Ein Sturmtief soll dieselbe Wirkung haben wie kraeftiger Regen, nicht die
    # sechsfache - sonst wird das Bild bei Unwetter ein anderes Objekt.
    assert normalize(-5.0, 0.0, 10.0) == 0.0
    assert normalize(60.0, 0.0, 10.0) == 1.0
    assert normalize(5.0, 0.0, 10.0) == pytest.approx(0.5)


def test_normalize_scheitert_bei_entarteter_spanne():
    # Lieber laut scheitern als still einen Vorgabewert liefern: Ein solcher
    # Fehler wuerde sonst als falsche Messreihe ueber Wochen weiterlaufen.
    with pytest.raises(ValueError):
        normalize(1.0, 5.0, 5.0)


def test_apply_curve_kennt_nur_dokumentierte_kennlinien():
    assert apply_curve(0.25, "linear") == 0.25
    assert apply_curve(0.25, "sqrt") == pytest.approx(0.5)
    with pytest.raises(ValueError):
        apply_curve(0.25, "logistic")


# --- Kopplung 1: Licht ------------------------------------------------------

def test_licht_bildet_globalstrahlung_auf_null_bis_eins_ab(app_config):
    light = app_config.values.coupling.light
    assert light.source == "shortwave_radiation"

    assert map_climate(0.0, light) == pytest.approx(0.0)          # Nacht
    assert map_climate(900.0, light) == pytest.approx(1.0)        # klarer Sommertag
    assert map_climate(450.0, light) == pytest.approx(0.5)        # linear dazwischen


def test_licht_saettigt_statt_zu_ueberschiessen(app_config):
    # Ueber der oberen Grenze bleibt es bei 1.0. Die Produzenten sollen an einem
    # aussergewoehnlich hellen Tag nicht ueber jede Grenze wachsen.
    light = app_config.values.coupling.light
    assert map_climate(1400.0, light) == pytest.approx(1.0)


# --- Kopplung 2: Naehrstoffeintrag ------------------------------------------

def test_niederschlag_wurzelkennlinie_macht_normalen_regen_sichtbar(app_config):
    nutrient = app_config.values.coupling.nutrient_input
    assert nutrient.curve == "sqrt"

    assert map_climate(0.0, nutrient) == pytest.approx(0.0)
    assert map_climate(10.0, nutrient) == pytest.approx(1.0)

    # Das ist der eigentliche Zweck der Wurzel: 2.5 mm/h sind ein Viertel der
    # Spanne, wirken aber zur Haelfte. Linear abgebildet blieben normale
    # Regenfaelle nahezu unsichtbar und nur Starkregen waere wahrnehmbar.
    massvoller_regen = map_climate(2.5, nutrient)
    assert massvoller_regen == pytest.approx(0.5)
    assert massvoller_regen > 0.25


# --- Kopplung 3: Prozessgeschwindigkeit -------------------------------------

def test_q10_ist_bei_referenztemperatur_neutral(app_config):
    rate = app_config.values.coupling.rate
    assert map_rate(rate.reference_temp_c, rate) == pytest.approx(1.0)


def test_q10_verdoppelt_je_zehn_kelvin(app_config):
    rate = app_config.values.coupling.rate
    # 10 K unter der Referenz: halbe Geschwindigkeit (liegt noch im Klammerbereich)
    assert map_rate(rate.reference_temp_c - 10.0, rate) == pytest.approx(0.5)


@pytest.mark.parametrize("temperature_c", [-20.0, -10.0, 0.0])
def test_q10_klammert_nach_unten(app_config, temperature_c):
    # Ohne untere Klammer wuerde ein Kaeltesturz das Bild einfrieren.
    rate = app_config.values.coupling.rate
    assert map_rate(temperature_c, rate) >= rate.output_min


@pytest.mark.parametrize("temperature_c", [30.0, 35.0, 45.0])
def test_q10_klammert_nach_oben(app_config, temperature_c):
    # Ohne obere Klammer koennte ein Hitzetag den Zeitschritt ueber die
    # Stabilitaetsgrenze der expliziten Diffusion treiben.
    rate = app_config.values.coupling.rate
    assert map_rate(temperature_c, rate) <= rate.output_max


def test_q10_bleibt_im_dokumentierten_korridor(app_config):
    rate = app_config.values.coupling.rate
    for t in range(-30, 51):
        assert rate.output_min <= map_rate(float(t), rate) <= rate.output_max


# --- Kopplung 4: Wind -------------------------------------------------------

def test_wind_reicht_richtung_unveraendert_durch(app_config):
    # Meteorologische Konvention: die Richtung, AUS der der Wind weht. Nur so
    # bleibt der Wetter-Rohlog ohne Umrechnung mit Open-Meteo vergleichbar.
    wind = app_config.values.coupling.wind
    assert map_wind(0.0, 10.0, wind).dir_deg == pytest.approx(0.0)
    assert map_wind(270.0, 10.0, wind).dir_deg == pytest.approx(270.0)
    # Ueberlauf wird normiert, nicht geklammert.
    assert map_wind(370.0, 10.0, wind).dir_deg == pytest.approx(10.0)


def test_wind_normiert_den_betrag(app_config):
    wind = app_config.values.coupling.wind
    assert map_wind(180.0, 0.0, wind).speed == pytest.approx(0.0)
    assert map_wind(180.0, 40.0, wind).speed == pytest.approx(1.0)
    assert map_wind(180.0, 20.0, wind).speed == pytest.approx(0.5)


# --- Glaettung: der Abstand der Zeitkonstanten ------------------------------

def test_glaettung_ist_schrittweitenunabhaengig():
    # Ein grosser Schritt muss dasselbe ergeben wie viele kleine. Sonst haenge
    # der Verlauf am Nachfuehrintervall, das nicht garantiert gleichmaessig ist.
    tau_min = 30.0
    in_einem_schritt = smooth(0.0, 1.0, 600.0, tau_min)

    schrittweise = 0.0
    for _ in range(120):
        schrittweise = smooth(schrittweise, 1.0, 5.0, tau_min)

    assert in_einem_schritt == pytest.approx(schrittweise, rel=1e-9)


def test_glaettung_erreicht_nach_einer_zeitkonstante_63_prozent():
    tau_min = 30.0
    assert smooth(0.0, 1.0, tau_min * 60.0, tau_min) == pytest.approx(1 - math.exp(-1), rel=1e-9)


def test_glaettung_ohne_zeitfortschritt_aendert_nichts():
    assert smooth(0.3, 1.0, 0.0, 30.0) == 0.3


def test_klimakanal_ist_drei_groessenordnungen_langsamer(app_config):
    # Die zu pruefende Kernannahme von TF1, hier als Regressionsschutz: Wer die
    # Zeitkonstanten einander annaehert, hebt den Gestaltungsbeitrag der Arbeit
    # auf, weil beide Kanaele zu einem verschmelzen.
    coupling = app_config.values.coupling
    langsamste_ereigniszeit = max(coupling.pulse_low.decay_seconds,
                                  coupling.pulse_high.decay_seconds)
    schnellste_klimazeit = min(coupling.light.smoothing_minutes,
                               coupling.nutrient_input.smoothing_minutes,
                               coupling.rate.smoothing_minutes,
                               coupling.wind.smoothing_minutes) * 60.0

    assert schnellste_klimazeit / langsamste_ereigniszeit > 100.0


# --- Winkelglaettung --------------------------------------------------------

def test_winkelglaettung_nimmt_den_kurzen_weg():
    # 350 -> 10 Grad ist eine Drehung um 20 Grad nach Osten, nicht um 340 nach
    # Westen. Ohne diese Behandlung wuerde die Grundstroemung bei Nordwind
    # gelegentlich fast eine ganze Umdrehung zurueckschwenken.
    ergebnis = smooth_angle(350.0, 10.0, 600.0, 30.0)
    assert 350.0 < ergebnis or ergebnis < 20.0
    # Nach einem Zehntel der Zeitkonstante darf sich nur wenig bewegt haben.
    assert smooth_angle(350.0, 10.0, 180.0, 30.0) % 360.0 == pytest.approx(351.9, abs=0.5)


def test_winkelglaettung_bleibt_im_wertebereich():
    winkel = 359.0
    for _ in range(200):
        winkel = smooth_angle(winkel, 45.0, 30.0, 30.0)
        assert 0.0 <= winkel < 360.0
