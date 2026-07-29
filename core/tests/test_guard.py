"""Tests des numerischen Guardrails.

Diese Funktion setzt die Abnahmebedingung fuer Phase 3 bereits bei der
Erzeugung durch: "jede Zahl im Eintrag ist in der Metrikdatenbank auffindbar".
Sie ist reines Python - was mechanisch pruefbar ist, wird nicht einem Modell
ueberlassen.
"""

from __future__ import annotations

from frame_core.chronicle.guard import (
    collect_allowed_values,
    extract_numbers,
    find_unsupported_numbers,
)

KENNZAHLEN = {
    "tick": 184320,
    "producer_biomass": 0.4231,
    "rolling_median": 0.1904,
    "mad": 0.0311,
    "nutrient": 0.0872,
}


def test_erkennt_zahlen_in_beiden_schreibweisen():
    # Das Modell wird deutsches Komma und englischen Punkt mischen.
    gefunden = {mention.raw for mention in extract_numbers("Wert 0,42 und 0.19 bei Tick 184320")}
    assert gefunden == {"0,42", "0.19", "184320"}


def test_belegter_text_geht_durch():
    text = ("Die Produzentenbiomasse liegt bei 0,4231 und damit ueber dem "
            "gleitenden Median von 0,1904.")
    assert find_unsupported_numbers(text, KENNZAHLEN) == []


def test_runden_ist_erlaubt():
    # 0,42 ist eine korrekte Rundung von 0,4231 - keine Erfindung.
    text = "Die Biomasse liegt bei 0,42, der Median bei 0,19."
    assert find_unsupported_numbers(text, KENNZAHLEN) == []


def test_falsches_runden_faellt_durch():
    # 0,43 ist keine Rundung von 0,4231.
    assert find_unsupported_numbers("Die Biomasse liegt bei 0,43.", KENNZAHLEN) == ["0,43"]


def test_erfundene_zeitspanne_faellt_durch():
    """Bewusst streng.

    "In den letzten 24 Stunden" behauptet eine Zeitspanne, die niemand gemessen
    und niemand uebergeben hat. Genau solche beilaeufigen Erfindungen sind es,
    die einen Chronikeintrag unbelegbar machen.
    """
    text = "In den letzten 24 Stunden ist die Biomasse auf 0,42 gestiegen."
    assert find_unsupported_numbers(text, KENNZAHLEN) == ["24"]


def test_mehrere_unbelegte_zahlen_werden_alle_gemeldet():
    text = "Nach 3 Tagen stieg die Biomasse um 17 Prozent auf 0,42."
    unbelegt = find_unsupported_numbers(text, KENNZAHLEN)
    assert unbelegt == ["3", "17"]


def test_tick_als_ganzzahl_ist_belegt():
    assert find_unsupported_numbers("Bei Tick 184320 wurde eine Bluete erkannt.",
                                    KENNZAHLEN) == []


def test_text_ohne_zahlen_ist_immer_belegt():
    assert find_unsupported_numbers("Die Produzenten breiten sich aus.", KENNZAHLEN) == []


def test_verschachtelte_kennzahlen_werden_gefunden():
    verschachtelt = {"mass": {"producer": 0.42, "nutrient": 0.08},
                     "weather": {"light": 0.71}}
    assert sorted(collect_allowed_values(verschachtelt)) == [0.08, 0.42, 0.71]
    assert find_unsupported_numbers("Biomasse 0,42 bei Licht 0,71.", verschachtelt) == []


def test_wahrheitswerte_gelten_nicht_als_zahlen():
    # Sonst waeren durch ein True/False im Kontext die Zahlen 1 und 0 belegt.
    assert collect_allowed_values({"ok": True, "wert": 0.5}) == [0.5]
