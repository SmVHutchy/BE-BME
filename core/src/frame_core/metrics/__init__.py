"""Metrikspeicher — die Zeitreihe des Systemzustands.

Nimmt die Metriknachrichten aus `sim` entgegen und legt sie in SQLite ab, jeweils
mit Zeitstempel, Tick und Seed. Zusaetzlich protokolliert werden die je Tick
angewandten env-Werte - ohne sie waere ein Lauf nicht rekonstruierbar.

Enthaelt ausserdem die Pruefung der Massenbilanz. Geprueft wird der
Residualsaldo, nicht die Konstanz der Gesamtmasse:

    residual(t) = total(t) - total(0) - Summe(Eintrag) + Summe(Austrag)

Niederschlag traegt Masse ein, Sedimentation traegt aus (Expose 6.2); die
Gesamtmasse SOLL sich also aendern. Was nicht passieren darf, ist unerklaerte
Masse. Toleranz: mass.drift_tolerance_pct.

Die Bilanzpruefung ist eine reine Funktion und wird getestet (siehe CLAUDE.md).
"""
