"""Regel "Bluete" - reine Funktion, deterministisch, testbar.

Hier laeuft kein Sprachmodell und wird nie eines laufen. Das Expose legt in 6.4
fest, dass die Ereigniserkennung der Regeldetektor leistet und nicht das Modell:
Nur so bleibt die Chronik reproduzierbar, und nur so ist ausgeschlossen, dass
Ereignisse beschrieben werden, die im System nie stattgefunden haben.

Die Regel: Produzentenbiomasse ueber gleitendem Median + k * MAD im Fenster W.

Warum Median und MAD statt Mittelwert und Standardabweichung: Beide sind robust
gegen Ausreisser. Eine Bluete ist selbst ein Ausreisser - wuerde sie in ihre
eigene Vergleichsbasis eingehen, hobe sie die Schwelle mit an und bliebe unter
Umstaenden unerkannt.

Fenster und Sperrzeit sind in **Weltstunden** definiert - nicht in Wanduhrzeit
und nicht in Stichproben.

Der erste Entwurf zaehlte Stichproben (A6). Das machte die Statistik
geschwindigkeitsinvariant, aber nicht die Weltzeit, die sie abdeckt:

    speed =   1  ->  720 Punkte * 5 Weltsekunden  =    1 Weltstunde
    speed = 500  ->  720 Punkte * 2500 Weltsek.   = 20,8 Welttage

Eine Bluete entwickelt sich ueber Stunden bis Tage. Ein gleitender Median ueber
eine Stunde folgt ihr einfach mit, sie hebt sich nie von ihrer eigenen
Vergleichsbasis ab - der Detektor waere im Feldbetrieb nahezu blind gewesen
(docs/annahmen.md A14). Massgeblich ist die biologische Zeitspanne, also die
Weltzeit.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from frame_core.config import BloomDetectorConfig


@dataclass(frozen=True)
class BloomEvaluation:
    """Ergebnis einer Detektorpruefung fuer eine einzelne Stichprobe."""

    triggered: bool
    reason: str
    """Warum ausgeloest wurde - oder warum nicht. Geht ins Protokoll: Jeder
    Eingriff und jede Nichtausloesung soll spaeter nachvollziehbar sein."""

    value: float = 0.0
    median: float = 0.0
    mad: float = 0.0
    threshold: float = 0.0


def median_absolute_deviation(values: Sequence[float], median: float) -> float:
    """Median der absoluten Abweichungen vom Median.

    Bewusst **ohne** den ueblichen Konsistenzfaktor 1.4826: Der wuerde die MAD
    an die Standardabweichung einer Normalverteilung angleichen. Die Verteilung
    der Biomasse ist nicht normal, und `k_mad` aus der Konfiguration ist ohnehin
    empirisch einzustellen - ein zusaetzlicher fester Faktor wuerde diese
    Einstellung nur verschleiern.
    """
    if not values:
        return 0.0
    return statistics.median([abs(v - median) for v in values])


def subsample(values: Sequence[float], limit: int) -> list[float]:
    """Duennt gleichmaessig aus, wenn es mehr Werte gibt als noetig.

    Im Feldbetrieb fallen in 120 Weltstunden rund 86.000 Messpunkte an. Der
    Median einer Verteilung aendert sich durch gleichmaessiges Ausduennen
    praktisch nicht, die Rechenzeit je Stichprobe schon.
    """
    if len(values) <= limit:
        return list(values)
    schritt = len(values) / limit
    return [values[int(i * schritt)] for i in range(limit)]


def evaluate_bloom(window: Sequence[float], candidate: float,
                   world_hours_since_last_event: float | None,
                   config: BloomDetectorConfig) -> BloomEvaluation:
    """Prueft eine einzelne Stichprobe gegen die Bluete-Regel.

    `window` sind die Messwerte der Produzentenbiomasse aus den vergangenen
    `config.window_world_hours` **Weltstunden**, ohne `candidate`. Die Auswahl
    nach Weltzeit trifft der Metrikspeicher; hier kommt sie fertig an.

    Der Kandidat bleibt bewusst draussen: Er soll die Schwelle nicht
    mitbestimmen, gegen die er geprueft wird.

    `world_hours_since_last_event` ist `None`, wenn im Lauf noch kein Ereignis
    aufgetreten ist.
    """
    if len(window) < config.min_samples:
        return BloomEvaluation(
            triggered=False,
            reason=f"zu wenige Stichproben ({len(window)} < {config.min_samples})",
            value=candidate,
        )

    if (world_hours_since_last_event is not None
            and world_hours_since_last_event < config.refractory_world_hours):
        return BloomEvaluation(
            triggered=False,
            reason=(f"Sperrzeit aktiv ({world_hours_since_last_event:.1f} < "
                    f"{config.refractory_world_hours} Weltstunden)"),
            value=candidate,
        )

    recent = subsample(window, config.max_window_samples)
    median = statistics.median(recent)
    mad = median_absolute_deviation(recent, median)
    threshold = median + config.k_mad * mad

    if candidate > threshold:
        return BloomEvaluation(
            triggered=True,
            reason=(f"Biomasse {candidate:.4f} ueber Schwelle {threshold:.4f} "
                    f"(Median {median:.4f} + {config.k_mad} * MAD {mad:.4f})"),
            value=candidate, median=median, mad=mad, threshold=threshold,
        )

    return BloomEvaluation(
        triggered=False,
        reason=f"Biomasse {candidate:.4f} unter Schwelle {threshold:.4f}",
        value=candidate, median=median, mad=mad, threshold=threshold,
    )
