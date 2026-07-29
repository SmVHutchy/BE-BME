"""Umweltdienst — der langsame Klimakanal.

Ruft Open-Meteo stuendlich ab, cacht die Antworten, interpoliert zwischen den
Stundenwerten und bildet vier der sechs Kopplungen ab: light, nutrient_input,
rate, wind (siehe docs/mapping.md).

Die Abbildung Wetterwert -> Simulationsgroesse geschieht hier und nicht im
Shader. Sie ist der wissenschaftliche Beitrag der Arbeit und muss testbar,
dokumentierbar und aus config/params.yaml parametrierbar bleiben.

Zwei Anforderungen, die nicht verhandelbar sind:
  - Die ROHEN Wetterdaten werden mitgeloggt, nicht nur die interpolierten.
    Ohne sie ist kein Lauf rekonstruierbar.
  - Bei Netzausfall werden die letzten bekannten Werte fortgeschrieben. Der
    Ausfall bleibt im Bild unsichtbar, wird aber protokolliert (Expose
    Risiko 8).

Attribution: Wetterdaten von Open-Meteo.com, CC BY 4.0.
"""
