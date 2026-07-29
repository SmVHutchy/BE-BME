"""Health-Log und Betriebsueberwachung.

Schreibt JSON Lines nach data/health.jsonl: Bildzeit, Speicher, Massenbilanz,
Neustartzaehler, Zustand des Klimakanals und den aktuellen Zeitrafferfaktor.

Der Zeitrafferfaktor gehoert dazu, damit spaeter nachvollziehbar bleibt, ob ein
Abschnitt der Zeitreihe im Zeitraffer entstanden ist oder im Feldbetrieb.

Quelle der Bild- und Speicherwerte ist die health-Nachricht aus `sim` (siehe
docs/contract.md Abschnitt 6). Diese Werte sind ausdruecklich
Betriebstelemetrie und kein Simulationszustand: Keiner von ihnen fliesst in
Metrikzeitreihe, Detektor oder Chronik.
"""
