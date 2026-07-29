"""Regeldetektor — erkennt Ereignisse in der Metrikzeitreihe.

REINES PYTHON. Schwellenwerte auf Zeitreihen, deterministisch, testbar. Hier
laeuft kein Sprachmodell und wird nie eines laufen.

Das ist keine Stilfrage: Das Expose legt in 6.4 fest, dass die Ereigniserkennung
der Regeldetektor leistet und nicht das Modell. Die Trennung haelt die Chronik
reproduzierbar und schliesst aus, dass Ereignisse beschrieben werden, die im
System nie stattgefunden haben. Das Modell bekommt das BEREITS ERKANNTE
Ereignis samt Kennzahlen und formuliert daraus einen Text - mehr nicht.

Prototyp 0 hat genau eine Regel:
    Bluete - Produzentenbiomasse ueber gleitendem Median + k * MAD im Fenster W

Spaeter (nicht in Prototyp 0): Kollaps, Aussterben einer Linie, Durchsetzung
einer Variante, Wanderung einer Front, leergefressene Zone.

Die Regeln sind reine Funktionen und werden getestet - einschliesslich der
Faelle knapp unter Schwelle und innerhalb der Sperrzeit.
"""
