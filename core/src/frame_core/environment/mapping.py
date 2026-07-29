"""Abbildung Wetterwert -> Simulationsgroesse.

Das ist der wissenschaftliche Beitrag der Arbeit (Expose 4 und 7.3) und
deswegen bewusst hier und nicht im Shader: reine Funktionen, testbar,
dokumentierbar, jeder Zahlenwert aus config/params.yaml.

Vier Kopplungen, vier Angriffspunkte, keine Ueberlappung:

    shortwave_radiation -> light           Wachstum der Produzenten
    precipitation       -> nutrient_input  Eintrag ins Naehrstofffeld
    temperature_2m      -> rate            globale Prozessgeschwindigkeit
    wind_*_10m          -> wind            Grundstroemung

Die beiden uebrigen Kopplungen (Bass- und Hochtonband) liegen im Ereigniskanal
und damit in `frame_core.audio`.

Nachweis der 1:1-Regel: docs/mapping.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from frame_core.config import ClimateCoupling, RateCoupling, WindCoupling


def normalize(value: float, input_min: float, input_max: float) -> float:
    """Bildet einen Messwert auf 0..1 ab und klammert ausserhalb der Spanne.

    Klammern statt Extrapolieren: Ein Sturmtief mit 60 mm/h soll dieselbe
    Wirkung haben wie 10 mm/h, nicht die sechsfache. Die Simulation kennt keine
    sinnvolle Antwort auf Extremwerte, und das Bild soll auch bei Unwetter kein
    anderes Objekt werden.
    """
    span = input_max - input_min
    if span <= 0.0:
        # Entartete Spanne. Nicht raten, sondern deutlich scheitern - ein
        # stillschweigend gelieferter Vorgabewert waere hier eine falsche
        # Messreihe ueber Wochen.
        raise ValueError(f"input_max ({input_max}) muss groesser sein als input_min ({input_min})")
    return min(1.0, max(0.0, (value - input_min) / span))


def apply_curve(unit_value: float, curve: str) -> float:
    """Wendet die Kennlinie auf einen bereits normierten Wert an."""
    if curve == "linear":
        return unit_value
    if curve == "sqrt":
        # Niederschlagsintensitaet ist stark rechtsschief. Linear abgebildet
        # blieben normale Regenfaelle nahezu unsichtbar und nur Starkregen waere
        # ueberhaupt wahrnehmbar.
        return math.sqrt(unit_value)
    raise ValueError(f"unbekannte Kennlinie: {curve!r}")


def scale(unit_value: float, output_min: float, output_max: float) -> float:
    """Spreizt 0..1 auf den Zielbereich der Kopplung."""
    return output_min + unit_value * (output_max - output_min)


def map_climate(value: float, coupling: ClimateCoupling) -> float:
    """Kennlinie fuer `light` und `nutrient_input`.

    `light` stammt aus `shortwave_radiation`. Sonnenstand und Bewoelkung stecken
    dort bereits gemeinsam drin - die Globalstrahlung ist geometrisch und durch
    Wolken gedaempft. Das Expose fasst beide ausdruecklich zu einer Groesse L
    zusammen (6.3); `cloud_cover` zusaetzlich zu verrechnen waere Doppelzaehlung
    und ein zweiter Eingang auf denselben Angriffspunkt.
    """
    unit = normalize(value, coupling.input_min, coupling.input_max)
    return scale(apply_curve(unit, coupling.curve), coupling.output_min, coupling.output_max)


def map_rate(temperature_c: float, coupling: RateCoupling) -> float:
    """Temperatur auf die globale Prozessgeschwindigkeit, Q10-Kennlinie.

    Q10 beschreibt, um welchen Faktor sich Stoffwechselraten je 10 K Erwaermung
    aendern - eine lehrbuchueblich etablierte Beziehung, kein selbst
    hergeleitetes Modell (Expose 7.3).

    Die Klammern sind nicht kosmetisch: Ohne `output_min` wuerde ein Kaeltesturz
    das Bild praktisch einfrieren, ohne `output_max` koennte ein Hitzetag den
    Zeitschritt ueber die Stabilitaetsgrenze der expliziten Diffusion treiben.
    """
    factor = coupling.q10 ** ((temperature_c - coupling.reference_temp_c) / 10.0)
    return min(coupling.output_max, max(coupling.output_min, factor))


@dataclass(frozen=True)
class WindValue:
    """Grundstroemung: Richtung in Grad, Betrag dimensionslos."""

    dir_deg: float
    speed: float


def map_wind(direction_deg: float, speed: float, coupling: WindCoupling) -> WindValue:
    """Wind auf die Grundstroemung.

    Die Richtung wird **unveraendert** in meteorologischer Konvention
    weitergereicht: die Richtung, aus der der Wind weht, 0 Grad = Nord. So
    liefert Open-Meteo den Wert, und so bleibt der Wetter-Rohlog ohne Umrechnung
    mit der Originalquelle vergleichbar. Die Umrechnung in einen
    Stroemungsvektor geschieht in `sim` (docs/annahmen.md A5).

    Richtung und Betrag sind zusammen **eine** Eingangsgroesse mit **einem**
    Angriffspunkt, nicht zwei.
    """
    unit = normalize(speed, coupling.input_min, coupling.input_max)
    return WindValue(
        dir_deg=direction_deg % 360.0,
        speed=scale(apply_curve(unit, coupling.curve), coupling.output_min, coupling.output_max),
    )


def smooth(previous: float, target: float, dt_seconds: float, smoothing_minutes: float) -> float:
    """Traegheitsglied erster Ordnung mit Zeitkonstante `smoothing_minutes`.

    Haelt den Klimakanal langsam. Der Abstand zum Ereigniskanal betraegt damit
    rund drei Groessenordnungen (20-90 Minuten gegen 2-4 Sekunden) und ist die
    zu pruefende Kernannahme von TF1.

    Die exponentielle Form ist schrittweitenunabhaengig: Ob alle 5 Sekunden oder
    alle 5 Minuten nachgefuehrt wird, aendert den zeitlichen Verlauf nicht. Das
    ist noetig, weil das Nachfuehrintervall nicht garantiert gleichmaessig ist.
    """
    if dt_seconds <= 0.0:
        return previous
    tau = smoothing_minutes * 60.0
    if tau <= 0.0:
        return target
    alpha = 1.0 - math.exp(-dt_seconds / tau)
    return previous + alpha * (target - previous)


def smooth_angle(previous_deg: float, target_deg: float, dt_seconds: float,
                 smoothing_minutes: float) -> float:
    """Wie `smooth`, aber fuer eine Richtung in Grad.

    Getrennte Funktion, weil der lineare Mittelwert bei Winkeln falsch ist: Der
    Uebergang von 350 auf 10 Grad ist eine Drehung um 20 Grad nach Osten, nicht
    um 340 Grad nach Westen. Ohne diese Behandlung wuerde die Grundstroemung bei
    Nordwind gelegentlich fast eine ganze Umdrehung zurueckschwenken - im Bild
    ein deutlich sichtbarer Fehler.
    """
    if dt_seconds <= 0.0:
        return previous_deg % 360.0
    delta = ((target_deg - previous_deg + 180.0) % 360.0) - 180.0
    return (smooth(0.0, delta, dt_seconds, smoothing_minutes) + previous_deg) % 360.0
