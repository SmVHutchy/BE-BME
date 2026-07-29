"""Tests des Regeldetektors.

Geprueft wird beides: dass eine Bluete ausloest, wenn sie soll, und - wichtiger -
dass sie es in den drei Faellen nicht tut, in denen sie nicht soll. Ein
Detektor, der zu oft ausloest, erzeugt Chronikeintraege ueber Ereignisse, die
so nie stattgefunden haben, und genau das schliesst Expose 6.4 aus.
"""

from __future__ import annotations

import random

import pytest

from frame_core.config import BloomDetectorConfig
from frame_core.detect.bloom import evaluate_bloom, median_absolute_deviation


@pytest.fixture
def kleine_config() -> BloomDetectorConfig:
    """Kleine Fenster, damit die Testdaten lesbar bleiben."""
    return BloomDetectorConfig(window_samples=20, k_mad=4.0,
                               min_samples=10, refractory_samples=15)


def rauschen(n: int, mittel: float = 0.20, streuung: float = 0.01) -> list[float]:
    rng = random.Random(20260901)          # fester Seed: Tests sind deterministisch
    return [rng.gauss(mittel, streuung) for _ in range(n)]


# --- Ausloesen --------------------------------------------------------------

def test_bluete_loest_bei_deutlichem_anstieg_aus(kleine_config):
    fenster = rauschen(20)
    ergebnis = evaluate_bloom(fenster, candidate=0.60,
                              samples_since_last_event=None, config=kleine_config)
    assert ergebnis.triggered
    assert ergebnis.threshold < 0.60
    assert "ueber Schwelle" in ergebnis.reason


def test_ausloesung_nennt_die_zahlen_die_spaeter_in_die_chronik_gehen(kleine_config):
    fenster = rauschen(20)
    ergebnis = evaluate_bloom(fenster, candidate=0.60,
                              samples_since_last_event=None, config=kleine_config)
    # Diese vier Werte sind es, die dem Sprachmodell uebergeben werden - und
    # gegen die der Text spaeter geprueft wird.
    assert ergebnis.value == pytest.approx(0.60)
    assert ergebnis.median > 0.0
    assert ergebnis.mad > 0.0
    assert ergebnis.threshold == pytest.approx(ergebnis.median + 4.0 * ergebnis.mad)


# --- Nicht ausloesen: die drei Negativfaelle --------------------------------

def test_knapp_unter_der_schwelle_loest_nicht_aus(kleine_config):
    fenster = rauschen(20)
    referenz = evaluate_bloom(fenster, candidate=0.60,
                              samples_since_last_event=None, config=kleine_config)

    knapp_darunter = referenz.threshold - 1e-6
    ergebnis = evaluate_bloom(fenster, candidate=knapp_darunter,
                              samples_since_last_event=None, config=kleine_config)
    assert not ergebnis.triggered
    assert "unter Schwelle" in ergebnis.reason


def test_vor_min_samples_loest_nichts_aus(kleine_config):
    # Am Anfang eines Laufs ist die Statistik nicht belastbar. Ein Ausschlag in
    # den ersten Minuten ist Einschwingen, kein Ereignis.
    fenster = rauschen(kleine_config.min_samples - 1)
    ergebnis = evaluate_bloom(fenster, candidate=99.0,
                              samples_since_last_event=None, config=kleine_config)
    assert not ergebnis.triggered
    assert "zu wenige Stichproben" in ergebnis.reason


def test_innerhalb_der_sperrzeit_loest_nichts_aus(kleine_config):
    # Sonst landet eine einzige Bluete als Dutzend Eintraege in der Chronik.
    fenster = rauschen(20)
    ergebnis = evaluate_bloom(fenster, candidate=0.60,
                              samples_since_last_event=kleine_config.refractory_samples - 1,
                              config=kleine_config)
    assert not ergebnis.triggered
    assert "Sperrzeit" in ergebnis.reason


def test_nach_ablauf_der_sperrzeit_loest_wieder_aus(kleine_config):
    fenster = rauschen(20)
    ergebnis = evaluate_bloom(fenster, candidate=0.60,
                              samples_since_last_event=kleine_config.refractory_samples,
                              config=kleine_config)
    assert ergebnis.triggered


# --- Eigenschaften der Regel ------------------------------------------------

def test_kandidat_hebt_seine_eigene_schwelle_nicht_an(kleine_config):
    """Der Kandidat darf nicht in seine eigene Vergleichsbasis eingehen.

    Sonst wuerde eine Bluete die Schwelle mitanheben, gegen die sie geprueft
    wird, und koennte sich selbst maskieren.
    """
    fenster = rauschen(20)
    klein = evaluate_bloom(fenster, candidate=0.30,
                           samples_since_last_event=None, config=kleine_config)
    riesig = evaluate_bloom(fenster, candidate=50.0,
                            samples_since_last_event=None, config=kleine_config)
    assert klein.threshold == pytest.approx(riesig.threshold)


def test_median_und_mad_sind_robust_gegen_einen_ausreisser(kleine_config):
    """Warum Median und MAD statt Mittelwert und Standardabweichung.

    Eine vorangegangene Bluete im Fenster darf die Schwelle nicht so weit
    anheben, dass die naechste unerkannt bleibt.
    """
    ruhig = rauschen(20)
    mit_ausreisser = list(ruhig)
    mit_ausreisser[5] = 5.0

    ohne = evaluate_bloom(ruhig, candidate=0.60,
                          samples_since_last_event=None, config=kleine_config)
    mit = evaluate_bloom(mit_ausreisser, candidate=0.60,
                         samples_since_last_event=None, config=kleine_config)

    assert mit.triggered and ohne.triggered
    # Der Ausreisser ist 25-mal so gross wie das Signal; die Schwelle darf sich
    # dadurch nur unwesentlich verschieben.
    assert mit.threshold == pytest.approx(ohne.threshold, rel=0.5)


def test_nur_das_juengste_fenster_zaehlt():
    """`window_samples` begrenzt wirklich, auch wenn mehr Daten anliegen.

    Sonst wuerde die Vergleichsbasis ueber Wochen mitwachsen und der Detektor
    im Dauerbetrieb immer traeger reagieren.
    """
    config = BloomDetectorConfig(window_samples=10, k_mad=4.0,
                                 min_samples=5, refractory_samples=0)
    # Alte Daten auf hohem Niveau, juengste zehn auf niedrigem.
    fenster = [5.0] * 50 + [0.20] * 10
    ergebnis = evaluate_bloom(fenster, candidate=0.60,
                              samples_since_last_event=None, config=config)
    assert ergebnis.median == pytest.approx(0.20)
    assert ergebnis.triggered


def test_mad_einer_konstanten_reihe_ist_null():
    """Bekannte Grenze der Regel, hier bewusst festgehalten.

    Bei einer perfekt konstanten Reihe ist die MAD null und die Schwelle faellt
    mit dem Median zusammen - dann loest schon der kleinste Anstieg aus. In
    echten Daten kommt das nicht vor, wohl aber in einem pathologischen Zustand:
    Wenn die Biomasse exakt auf dem Refugium-Mindestwert liegt, meldet jede
    beginnende Erholung sofort eine "Bluete".

    Siehe offener Punkt am Ende von Phase 1.
    """
    assert median_absolute_deviation([0.2] * 20, 0.2) == 0.0

    config = BloomDetectorConfig(window_samples=20, k_mad=4.0,
                                 min_samples=10, refractory_samples=0)
    ergebnis = evaluate_bloom([0.2] * 20, candidate=0.2001,
                              samples_since_last_event=None, config=config)
    assert ergebnis.triggered
    assert ergebnis.mad == 0.0


# --- Gegen die ausgelieferte Konfiguration ----------------------------------

def test_ausgelieferte_parameter_ergeben_eine_brauchbare_schwelle(app_config):
    """Die echten Werte aus params.yaml an einer realistischen Zeitreihe."""
    bloom = app_config.values.detector.bloom
    fenster = rauschen(bloom.window_samples, mittel=0.20, streuung=0.012)

    # Normale Schwankung loest nicht aus.
    ruhig = evaluate_bloom(fenster, candidate=0.23,
                           samples_since_last_event=None, config=bloom)
    assert not ruhig.triggered

    # Eine Verdopplung der Biomasse schon.
    bluete = evaluate_bloom(fenster, candidate=0.42,
                            samples_since_last_event=None, config=bloom)
    assert bluete.triggered
