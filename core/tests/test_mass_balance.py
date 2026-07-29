"""Tests der Massenbilanz.

Der wichtigste Test in dieser Datei ist
`test_wachsende_gesamtmasse_ist_kein_fehler`: Die naheliegende Pruefung -
"bleibt die Gesamtmasse konstant?" - waere das falsche Kriterium und wuerde bei
korrekt arbeitendem Kreislauf fehlschlagen. Niederschlag traegt Masse ein,
Sedimentation traegt aus (Expose 6.2).
"""

from __future__ import annotations

import pytest

from frame_core.metrics.balance import check_balance, mass_residual


def test_geschlossener_kreislauf_ohne_austausch_hat_kein_residuum():
    # Biomasse stirbt, wird remineralisiert, waechst wieder - die Gesamtmasse
    # verschiebt sich zwischen den Feldern, verschwindet aber nicht.
    assert mass_residual(initial_total=100.0, current_total=100.0,
                         inflow_total=0.0, outflow_total=0.0) == pytest.approx(0.0)


def test_wachsende_gesamtmasse_ist_kein_fehler(app_config):
    """Der Kern der Sache.

    Ueber Wochen hat es 30 Einheiten hineingeregnet und 12 sind sedimentiert.
    Die Gesamtmasse ist damit um 18 gestiegen - und das ist vollstaendig
    erklaert. Eine Pruefung auf Konstanz wuerde hier Alarm schlagen.
    """
    mass = app_config.values.mass
    result = check_balance(
        initial_total=100.0, current_total=118.0,
        inflow_total=30.0, outflow_total=12.0,
        drift_tolerance_pct=mass.drift_tolerance_pct,
        corridor_min=mass.corridor_min, corridor_max=mass.corridor_max,
    )
    assert result.residual == pytest.approx(0.0)
    assert result.within_tolerance
    assert result.within_corridor


def test_schrumpfende_gesamtmasse_ist_kein_fehler(app_config):
    # Trockenperiode: wenig Eintrag, stetige Sedimentation.
    mass = app_config.values.mass
    result = check_balance(
        initial_total=100.0, current_total=82.0,
        inflow_total=2.0, outflow_total=20.0,
        drift_tolerance_pct=mass.drift_tolerance_pct,
        corridor_min=mass.corridor_min, corridor_max=mass.corridor_max,
    )
    assert result.residual == pytest.approx(0.0)
    assert result.within_tolerance


def test_unerklaerte_masse_faellt_durch(app_config):
    # Genau die numerische Drift aus Risiko 2: Die Advektion erzeugt Masse.
    mass = app_config.values.mass
    result = check_balance(
        initial_total=100.0, current_total=110.0,
        inflow_total=0.0, outflow_total=0.0,
        drift_tolerance_pct=mass.drift_tolerance_pct,
        corridor_min=mass.corridor_min, corridor_max=mass.corridor_max,
    )
    assert result.residual == pytest.approx(10.0)
    assert result.residual_pct == pytest.approx(10.0)
    assert not result.within_tolerance


def test_verlorene_masse_faellt_ebenso_durch(app_config):
    mass = app_config.values.mass
    result = check_balance(
        initial_total=100.0, current_total=90.0,
        inflow_total=0.0, outflow_total=0.0,
        drift_tolerance_pct=mass.drift_tolerance_pct,
        corridor_min=mass.corridor_min, corridor_max=mass.corridor_max,
    )
    assert result.residual == pytest.approx(-10.0)
    # Das Vorzeichen bleibt erhalten, damit die Richtung der Drift im
    # Health-Log ablesbar ist; geprueft wird der Betrag.
    assert result.residual_pct == pytest.approx(10.0)
    assert not result.within_tolerance


def test_toleranzgrenze_wird_eingehalten(app_config):
    mass = app_config.values.mass
    gerade_noch = check_balance(
        initial_total=100.0, current_total=102.0,
        inflow_total=0.0, outflow_total=0.0,
        drift_tolerance_pct=mass.drift_tolerance_pct,
        corridor_min=mass.corridor_min, corridor_max=mass.corridor_max,
    )
    knapp_darueber = check_balance(
        initial_total=100.0, current_total=102.5,
        inflow_total=0.0, outflow_total=0.0,
        drift_tolerance_pct=mass.drift_tolerance_pct,
        corridor_min=mass.corridor_min, corridor_max=mass.corridor_max,
    )
    assert gerade_noch.within_tolerance      # exakt 2.0 %
    assert not knapp_darueber.within_tolerance


def test_korridor_und_residuum_sind_unabhaengige_fragen(app_config):
    """Ein sauberer Saldo heisst nicht, dass das System gesund ist.

    Hier ist jede Massenaenderung erklaert - die Welt laeuft trotzdem leer.
    Beide Groessen werden gebraucht: das Residuum fuer die Numerik (Risiko 2),
    der Korridor fuer die Frage, ob das System kippt (Risiko 1).
    """
    mass = app_config.values.mass
    result = check_balance(
        initial_total=100.0, current_total=50.0,
        inflow_total=0.0, outflow_total=50.0,
        drift_tolerance_pct=mass.drift_tolerance_pct,
        corridor_min=mass.corridor_min, corridor_max=mass.corridor_max,
    )
    assert result.residual == pytest.approx(0.0)
    assert result.within_tolerance          # Numerik in Ordnung
    assert not result.within_corridor       # Welt laeuft leer
    assert result.total_ratio == pytest.approx(0.5)


def test_bezugsgroesse_ist_die_startmasse(app_config):
    """Sonst schrumpft sich ein leerlaufendes System seinen eigenen Massstab.

    Bei aktueller Masse 10 und einem Residuum von 2 waeren das 20 % - bezogen
    auf die Startmasse 100 sind es 2 % und damit noch in der Toleranz. Die
    Bezugsgroesse muss die Startmasse sein, sonst wuerde die Drift genau dann
    unauffaellig, wenn sie am gefaehrlichsten ist.
    """
    mass = app_config.values.mass
    result = check_balance(
        initial_total=100.0, current_total=10.0,
        inflow_total=0.0, outflow_total=88.0,
        drift_tolerance_pct=mass.drift_tolerance_pct,
        corridor_min=mass.corridor_min, corridor_max=mass.corridor_max,
    )
    assert result.residual == pytest.approx(-2.0)
    assert result.residual_pct == pytest.approx(2.0)


def test_startmasse_null_ist_ein_fehler():
    with pytest.raises(ValueError):
        check_balance(initial_total=0.0, current_total=1.0,
                      inflow_total=0.0, outflow_total=0.0,
                      drift_tolerance_pct=2.0, corridor_min=0.7, corridor_max=1.4)
