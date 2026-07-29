"""Audiodienst — der schnelle Ereigniskanal.

Liefert zwei der sechs Kopplungen: pulse_low (Bassband -> Stroemungsimpuls) und
pulse_high (Hochtonband -> Naehrstoffpartikel).

In Prototyp 0 nur als Stub: Ein Testendpunkt erzeugt synthetische Pulse. Die
echte Erfassung kommt spaeter hinter dasselbe Interface - das Interface ist
bereits das endgueltige, die Implementierung nicht.

Datenschutz ist hier keine Randbedingung, sondern Teil der Aufgabe
(Expose 5 und 7.5):
  - Aus dem Modul treten ausschliesslich zwei Pegelwerte aus.
  - Keine Inhaltsanalyse, keine Spracherkennung auf diesem Pfad.
  - Kein Puffer ueber das FFT-Fenster hinaus, keine Speicherung.
  - Kein Audiosignal verlaesst das Geraet.

Offen (Expose 7.5): Raummikrofon oder Audio-Loopback. Das Interface laesst
beides zu und darf die Entscheidung nicht vorwegnehmen.
"""
