"""Massenbilanz als reine Funktion.

Der Stoffkreislauf ist **intern** verlustfrei: Absterbende Biomasse geht
vollstaendig ins Naehrstofffeld zurueck. Nach aussen ist er **offen**: Der
Niederschlag traegt Masse ein, die Sedimentation traegt aus (Expose 6.2).

Daraus folgt das Pruefkriterium, und es ist nicht das naheliegende. Die
Gesamtmasse **soll** sich aendern - sie schwingt in einem Korridor. Wer auf
konstante Gesamtmasse prueft, prueft das Falsche und bekommt bei korrekt
arbeitendem Kreislauf einen Fehlalarm. Was nicht passieren darf, ist
**unerklaerte** Masse:

    residual(t) = total(t) - total(0) - Summe(Eintrag) + Summe(Austrag)

Bleibt dieser Saldo nahe null, ist jede Massenaenderung durch einen
protokollierten Vorgang gedeckt. Laeuft er weg, erzeugt oder verliert die
Advektion Masse - genau die numerische Drift aus Risiko 2.

Die Bilanz ist gleichzeitig Stabilitaetsmetrik fuer TF2 und Nachweis, dass der
Kreislauf haelt.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BalanceResult:
    """Ergebnis einer Bilanzpruefung."""

    residual: float
    """Unerklaerte Masse in absoluten Einheiten. Vorzeichen sagt die Richtung:
    positiv = es ist Masse entstanden, negativ = Masse verschwunden."""

    residual_pct: float
    """Residuum bezogen auf die Startmasse, in Prozent."""

    within_tolerance: bool
    """Liegt `residual_pct` innerhalb von `mass.drift_tolerance_pct`?"""

    within_corridor: bool
    """Liegt die Gesamtmasse im Korridor `mass.corridor_min`..`corridor_max`,
    jeweils relativ zur Startmasse? Das ist die zweite, unabhaengige Frage:
    Der Saldo kann sauber sein, waehrend das System trotzdem leerlaeuft."""

    total_ratio: float
    """Gesamtmasse relativ zur Startmasse."""


def mass_residual(initial_total: float, current_total: float,
                  inflow_total: float, outflow_total: float) -> float:
    """Unerklaerte Masse zum Zeitpunkt t.

    Alle vier Groessen sind kumulativ ueber den Lauf, nicht pro Tick.
    """
    return current_total - initial_total - inflow_total + outflow_total


def check_balance(initial_total: float, current_total: float,
                  inflow_total: float, outflow_total: float,
                  drift_tolerance_pct: float,
                  corridor_min: float, corridor_max: float) -> BalanceResult:
    """Prueft Residualsaldo und Korridor.

    Bezugsgroesse fuer beide Prozentangaben ist die **Startmasse**, nicht die
    aktuelle: Sonst wuerde ein leerlaufendes System sich seinen eigenen Massstab
    schrumpfen und die Drift bliebe unauffaellig, obwohl sie waechst.
    """
    if initial_total <= 0.0:
        raise ValueError(f"initial_total muss positiv sein, war {initial_total}")

    residual = mass_residual(initial_total, current_total, inflow_total, outflow_total)
    residual_pct = abs(residual) / initial_total * 100.0
    total_ratio = current_total / initial_total

    return BalanceResult(
        residual=residual,
        residual_pct=residual_pct,
        within_tolerance=residual_pct <= drift_tolerance_pct,
        within_corridor=corridor_min <= total_ratio <= corridor_max,
        total_ratio=total_ratio,
    )
