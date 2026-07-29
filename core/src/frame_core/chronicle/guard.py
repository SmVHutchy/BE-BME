"""Numerisches Guardrail - reine Funktion.

Prueft, ob jede Zahl in einem erzeugten Chronikeintrag in den uebergebenen
Kennzahlen vorkommt. Deterministisch, testbar, ohne Modellaufruf.

Die Reihenfolge ist Absicht und steht so in CLAUDE.md: Was Python mechanisch
pruefen kann, wird nicht einem Modell ueberlassen. Der `verifier` beurteilt
danach die inhaltlichen Aussagen - ob also stimmt, was ueber die Zahlen
behauptet wird. Erfundene Zahlen faengt vorher diese Funktion.

Damit ist die Abnahmebedingung fuer Phase 3 - "jede Zahl im Eintrag ist in der
Metrikdatenbank auffindbar" - nicht nur eine Pruefung am Ende, sondern eine
Eigenschaft, die bei der Erzeugung erzwungen wird.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Erfasst 0.42, 0,42, -3, 184320 und 1.234 - jeweils mit optionalem Vorzeichen.
# Deutsche Texte schreiben das Dezimalkomma, das Modell wird beides mischen.
_NUMBER_PATTERN = re.compile(r"-?\d+(?:[.,]\d+)?")


@dataclass(frozen=True)
class NumberMention:
    """Eine im Text gefundene Zahl."""

    raw: str
    value: float
    decimals: int


def extract_numbers(text: str) -> list[NumberMention]:
    """Findet alle Zahlen im Text, mit ihrer Stellenzahl.

    Die Stellenzahl wird gebraucht, weil das Modell runden darf: Steht in den
    Kennzahlen 0.4231 und im Text "0,42", ist das korrekt und keine Erfindung.
    """
    mentions: list[NumberMention] = []
    for match in _NUMBER_PATTERN.finditer(text):
        raw = match.group()
        normalised = raw.replace(",", ".")
        _, _, fraction = normalised.partition(".")
        mentions.append(NumberMention(raw=raw, value=float(normalised),
                                      decimals=len(fraction)))
    return mentions


def is_supported(mention: NumberMention, allowed: Iterable[float]) -> bool:
    """Deckt einer der uebergebenen Werte diese Zahl?

    Gerundet wird auf die im Text verwendete Stellenzahl. Damit gilt 0.42 als
    belegt, wenn 0.4231 uebergeben wurde - aber 0.43 nicht.
    """
    for value in allowed:
        if round(value, mention.decimals) == round(mention.value, mention.decimals):
            return True
    return False


def collect_allowed_values(metrics: dict) -> list[float]:
    """Sammelt alle Zahlen aus den uebergebenen Kennzahlen, auch verschachtelte."""
    found: list[float] = []

    def walk(node) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            found.append(float(node))
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(metrics)
    return found


def find_unsupported_numbers(text: str, metrics: dict) -> list[str]:
    """Gibt die Zahlen zurueck, die durch keine Kennzahl gedeckt sind.

    Leere Liste heisst: Jede Zahl im Text ist belegt.

    Bewusst streng. Auch eine beilaeufige Angabe wie "in den letzten 24 Stunden"
    faellt durch, wenn 24 nicht uebergeben wurde - denn der Eintrag soll keine
    Zeitspanne behaupten, die niemand gemessen hat. Der Prompt weist das Modell
    ausdruecklich an, keine eigenen Zahlen einzufuehren.
    """
    allowed = collect_allowed_values(metrics)
    return [mention.raw for mention in extract_numbers(text)
            if not is_supported(mention, allowed)]
