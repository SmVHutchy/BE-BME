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

Fenster und Sperrzeit sind in **Stichproben** definiert, nicht in Minuten. Der
Grund ist Geschwindigkeitsinvarianz: Metriken treffen alle 5 s Wanduhrzeit ein,
unabhaengig von `sim.speed`. Bei speed = 100 entspraechen 60 Wanduhrminuten
hundertmal so viel simulierter Zeit wie bei speed = 1, und der Detektor saehe im
Zeitraffer eine voellig andere Statistik als im Feldbetrieb - genau die
Vergleichbarkeit, um derentwillen die Zeitrafferlaeufe existieren
(docs/annahmen.md A6).
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


def evaluate_bloom(window: Sequence[float], candidate: float,
                   samples_since_last_event: int | None,
                   config: BloomDetectorConfig) -> BloomEvaluation:
    """Prueft eine einzelne Stichprobe gegen die Bluete-Regel.

    `window` sind die vorangegangenen Messwerte der Produzentenbiomasse, ohne
    `candidate`. Der Kandidat bleibt bewusst draussen: Er soll die Schwelle
    nicht mitbestimmen, gegen die er geprueft wird.

    `samples_since_last_event` ist `None`, wenn im Lauf noch kein Ereignis
    aufgetreten ist.
    """
    if len(window) < config.min_samples:
        return BloomEvaluation(
            triggered=False,
            reason=f"zu wenige Stichproben ({len(window)} < {config.min_samples})",
            value=candidate,
        )

    if (samples_since_last_event is not None
            and samples_since_last_event < config.refractory_samples):
        return BloomEvaluation(
            triggered=False,
            reason=(f"Sperrzeit aktiv ({samples_since_last_event} < "
                    f"{config.refractory_samples} Stichproben)"),
            value=candidate,
        )

    recent = list(window[-config.window_samples:])
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
