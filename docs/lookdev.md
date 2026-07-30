# Look-Development

Gehört in **Monat 1** und ist in Prototyp 0 ausdrücklich nicht enthalten. Dieses
Dokument hält fest, was jetzt schon feststeht, damit es bis dahin nicht verloren
geht.

---

## Die Ausgangsfrage

*„Wann planen wir die einzelnen Mikroorganismen und wie sie aussehen — Varianten,
ohne sie uns auszudenken, sondern auf mathematischem Weg?"*

Die Frage hat eine unbequeme Voraussetzung: **Es gibt keine einzelnen
Organismen.** Der Zustand ist ein Feld — jede Zelle trägt eine Nährstoff- und
eine Biomassedichte, keine Individuen mit Eigenschaften. Das folgt aus
Exposé §7.2 (Fragment-Shader statt Compute); Individuenverwaltung wäre der
WebGPU-Weg, den das Exposé wegen des Stabilitätsrisikos im Wochenbetrieb
zurückstellt.

Die tragfähige Frage lautet deshalb: **woher kommen Muster und Farben?** Darauf
gibt es eine Antwort, die ohne Erfindung auskommt.

---

## Die Formen stehen bereits im Modell

In [`react.frag`](../sim/src/shaders/react.frag) gilt:

- **Nährstoff diffundiert** (Fünf-Punkt-Laplace)
- **Biomasse diffundiert nicht** — sie wächst lokal und zehrt dabei den
  Nährstoff auf

Das ist strukturell ein Aktivator-Inhibitor-System: Lokales Wachstum erzeugt
über den Nährstoffentzug eine *laterale Hemmung*, die weiter reicht als das
Wachstum selbst. Diese Skalentrennung ist der Mechanismus, aus dem
Turing-Muster entstehen — Flecken, Streifen, Labyrinthe.

Die Varianten sind also nicht zu zeichnen, sondern **im Parameterraum zu
finden**:

| Verhältnis | Wirkung auf das Bild |
|---|---|
| `diffusion_coefficient` ÷ `doubling_time_hours` | Flecken, Labyrinth oder geschlossene Decke |
| `lifetime_hours` ÷ `doubling_time_hours` | wie scharf die Ränder stehen, wie schnell Strukturen wandern |
| `base_current_gain`, `curl_noise_strength` | ob Muster zu Streifen ausgezogen oder verwirbelt werden |
| `nutrient_half_saturation` | wie hart die Konkurrenz um Nährstoff ist — Kontrast der Struktur |

### Die Inspirationsbilder, technisch gelesen

Vier Referenzen wurden am 30.07.2026 eingebracht. Ihre technische Einordnung:

1. **Fluid mit verästelten Fronten und Membranblasen** (orange/violett) —
   die dendritischen Fronten sind erreichbar, die Blasen- und Membranstrukturen
   **nicht**: Sie brauchen einen Oberflächenspannungsterm, den das Modell nicht
   hat und den Exposé §7.3 nicht in der Liste etablierter Operatoren führt. Der
   Ausreißer der vier.
2. **Blobs mit chromatischen Rändern** auf blassgrün — klassisches
   Turing-Regime. Die farbigen Konturen sind eine Sache des Anzeige-Shaders
   (Farbe nach Gradient, nicht nur nach Wert) und kosten wenig.
3. **Dichtes Labyrinth**, Säuregrün auf Dunkelorange — dasselbe Regime bei
   höherer Ortsfrequenz. Erreichbar über kleinere Diffusionsweite gegen die
   Wachstumszeit.
4. **Kammartige Streifen** in einem Strömungsfeld — Turing-Struktur unter
   Scherung. Entsteht, wenn die Grundströmung stark genug gegen die
   Musterbildung steht.

**Der gemeinsame Nenner von 2, 3 und 4: feine Struktur überlebt nur bei geringer
numerischer Dissipation.** Genau die fehlt der semi-lagrangeschen Advektion
derzeit — das ist [A12](annahmen.md). Ästhetisches Ziel und Massenerhaltung
zeigen also in dieselbe Richtung: Masseerhaltende Advektion nach Flow-Lenia löst
beides, eine bloße Renormalisierung nur die Bilanz.

---

## Die Farben: eine Kurve, keine Palette

Exposé §6.2 nennt als vierten Genwert ausdrücklich **Pigment**. Die Farbe ist
damit eine vererbte, mutierende Größe — kein Gestaltungsakt pro Organismus.

Der Weg dahin: **eine** Kurve durch einen wahrnehmungsgleichabständigen Farbraum
(OKLCH), und das Pigment-Gen ist die Position darauf. Dann gilt: gleicher
genetischer Abstand = gleicher wahrgenommener Farbabstand.

Die Gestaltungsentscheidung ist damit *eine Kurve statt hundert Farben* — und
sie ist begründbar, weil sie eine Eigenschaft hat statt einen Geschmack. Die
Population füllt die Kurve über Wochen selbst, durch Mutation und Selektion.

---

## Wann was passiert

| Wann | Was | Voraussetzung |
|---|---|---|
| vor allem anderen | **A12 entscheiden** | Dissipation bestimmt, welche Feinheit überhaupt erreichbar ist |
| Monat 1 | Parameterraum durchfahren, Regime dokumentieren | **funktionierender Zeitraffer** |
| Monat 1, Ende | Farbkurve festlegen | Ergebnis des Parameterlaufs |
| Prototyp 1 / Monat 2 | Genkanäle, Vererbung, Mutation, Pigment | — |

Der mittlere Punkt ist der wichtigste und wird leicht übersehen: **Ohne
Zeitraffer lässt sich der Parameterraum nicht erkunden.** Ein Musterregime zeigt
sich erst nach Welttagen bis -wochen; bei `speed = 1` dauert ein einziger
Versuch Wochen, bei `speed = 500` zwei Stunden. Der Zeitraffer ist nicht nur das
Prüfinstrument gegen Risiko 1 — er ist das **Entwurfswerkzeug für den Look**.

Deshalb stand die Behebung von [A11](annahmen.md) auch aus gestalterischer Sicht
zuerst: Solange die Welt in Dauernacht steht und nach dreizehn Welttagen
ausstirbt, ist kein einziges Musterregime zu sehen.

---

## Technisch vorbereitet

Die Genkanäle sind kein Umbau, sondern eine zweite Textur neben der bestehenden:
vier Genwerte als RGBA, mit der Biomasse mitadvektiert, bei Fortpflanzung
biomassegewichtet gemischt und mit hash-basiertem Rauschen aus
`(seed, tick, Position)` mutiert. Das ist das Parameter-Embedding aus Flow-Lenia,
das Exposé §3.2 ohnehin als Grundlage führt.

Nebenwirkung, die der Arbeit nützt: „Eine Linie setzt sich durch" wird damit
messbar als Verschiebung des räumlichen Medians eines Genkanals. Der
Regeldetektor kann sie erkennen, und die Chronik kann sie beschreiben, ohne dass
ein Modell etwas erfindet — genau die Trennung, auf der Exposé §6.4 besteht.

Der Vertrag ist darauf schon vorbereitet: `gene_median` und `lineages` stehen in
der Metriknachricht und sind in Prototyp 0 bewusst leer bzw. konstant 1.

---

## Was hier nicht entschieden wird

Panelgröße und Format (Exposé §6.1), das Register der Chronikeinträge (§6.4) und
vor allem die **Interaktionsform** (§6.5). Look-Development beantwortet, wie das
Bild aussieht — nicht, wie Bewohner mit ihm in Kontakt treten.
