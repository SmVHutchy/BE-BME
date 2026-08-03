# Annahmen

Jede Annahme, die im Verlauf des Projekts getroffen wurde, mit Begruendung und
dem Weg, sie aufzuloesen. Im Code sind die zugehoerigen Stellen mit
`# ANNAHME:` markiert.

Der Zweck dieser Datei ist nicht Buchhaltung: In der Arbeit muss jede
Entwurfsentscheidung begruendet werden, und eine Annahme, die sechs Monate
spaeter niemand mehr als Annahme erkennt, wird stillschweigend zur Tatsache.

**Stand: Phasen 0 bis 4 gebaut** (A1 bis A17). Erledigte Annahmen bleiben mit
ihrer Auflösung stehen und werden nicht gelöscht — für die Arbeit zählt der Weg
zur Entscheidung, nicht nur ihr Ergebnis. Überholte Annahmen sind als solche
gekennzeichnet und verweisen auf ihre Nachfolgerin (siehe A6 → A14).

---

## A1 — Umweltdienst in Python statt TypeScript/Node

**Ort:** `core/src/frame_core/environment/`, `docs/contract.md` §1

Exposé §7.1 nennt in der Werkzeugspalte fuer den Umweltdienst „lokaler Dienst
(TypeScript/Node)". Umgesetzt wird er in Python als Teil von `core`.

**Begruendung.** Metrikspeicher, Regeldetektor und Chronikpipeline sind
ohnehin Python; der Umweltdienst schreibt den Wetter-Rohlog, den der
Metrikspeicher fuer die Reproduzierbarkeit braucht. Ein eigener Node-Prozess
allein fuer einen stuendlichen HTTP-Abruf waere ein dritter Dienst mit eigenem
Autostart, eigenem Watchdog und eigenem Logpfad — im monatelangen Dauerbetrieb
reine Betriebslast, und er wuerde den Rohlog vom uebrigen Speicher trennen.
Die Werkzeugspalte in §7.1 benennt keine forschungsrelevante Festlegung; der
Beitrag der Arbeit liegt im Mapping-Design, nicht in der Sprachwahl des
Abrufdienstes.

**Status.** Vom Verfasser am 29.07.2026 entschieden. Bei der schriftlichen
Fixierung der Umfangsgrenze mit der Betreuung (Risiko 7) zu erwaehnen.

---

## A2 — Standort Nuernberg

**Ort:** `config/params.yaml` → `environment.latitude` / `.longitude`

Angesetzt sind 49.4521 / 11.0767.

**Begruendung.** Fuer Entwicklung und Zeitrafferlaeufe wird ein plausibler
mitteleuropaeischer Standort gebraucht. Der Betriebsstandort ist der Wohnraum
des jeweiligen Studienhaushalts.

**Aufloesung.** Je Durchgang der Feldstudie anzupassen. Der Wert gehoert in die
Laufdokumentation, weil er Teil der Reproduzierbarkeit ist.

---

## A3 — Vierte Vertragsnachricht `health`

**Ort:** `docs/contract.md` §6

Die Vertragsvorgabe kennt drei Nachrichten. Ergaenzt wurde eine vierte fuer
Betriebstelemetrie.

**Begruendung.** Das Health-Log verlangt Bildzeit und Speicherverbrauch
(Prototyp 0, Punkt 14); beide kennt nur `sim`. Die Alternative waere gewesen,
die Werte in die Metriknachricht zu mischen — dann waere Betriebstelemetrie
nicht mehr von Simulationszustand zu unterscheiden. Die drei vorgegebenen
Nachrichten bleiben unveraendert; kein Wert aus `health` fliesst in
Metrikzeitreihe, Detektor oder Chronik.

**Status.** Vom Verfasser widersprechbar.

---

## A4 — Bilanzsummen in der Metriknachricht

**Ort:** `docs/contract.md` §3

`mass.inflow_total` und `mass.outflow_total` wurden dem vorgegebenen
`mass`-Objekt hinzugefuegt.

**Begruendung.** Der Stoffkreislauf ist intern verlustfrei, aber nach aussen
offen: Niederschlag traegt ein, Sedimentation traegt aus (Exposé §6.2). Die
Gesamtmasse **soll** sich also veraendern. Prueffaehig ist deshalb nicht ihre
Konstanz, sondern der Residualsaldo

```
residual(t) = total(t) - total(0) - Σ Eintrag + Σ Austrag
```

Ohne die beiden Summen liesse sich die Abnahmebedingung „Massendrift unter 2 %"
gar nicht bilden. Eine Pruefung auf konstante Gesamtmasse waere das falsche
Kriterium und wuerde bei korrekt arbeitendem Kreislauf fehlschlagen.

---

## A5 — Windrichtung in meteorologischer Konvention

**Ort:** `docs/contract.md` §4, `config/params.yaml` → `coupling.wind`

`env.wind.dir_deg` bezeichnet die Richtung, *aus der* der Wind weht
(0° = Nord). Die Umrechnung in einen Stroemungsvektor geschieht in `sim`.

**Begruendung.** So liefert Open-Meteo den Wert. Wird er unveraendert
durchgereicht, bleibt der Wetter-Rohlog ohne Umrechnung mit der Originalquelle
vergleichbar — noetig fuer die Rekonstruktion eines Laufs. Die Konvention ist
eine haeufige Fehlerquelle (Vorzeichen bzw. 180°-Drehung) und deshalb an beiden
Stellen ausdruecklich benannt.

---

## A6 — Detektorfenster in Messpunkten statt in Minuten (ÜBERHOLT durch A14)

> **Diese Annahme war halb richtig und dadurch gefaehrlich.** Sie stellte
> Geschwindigkeitsinvarianz der *Statistik* her, aber nicht der *Weltzeit*, die
> sie abdeckt - und massgeblich ist die biologische Zeitspanne. Siehe A14. Der
> Text bleibt stehen, weil die urspruengliche Ueberlegung nachvollziehbar sein
> soll.


**Ort:** `config/params.yaml` → `detector.bloom.window_samples`,
`.refractory_samples`

Fenster W und Sperrzeit sind in Stichproben definiert, nicht in Wanduhr- oder
Simulationsminuten.

**Begruendung.** Geschwindigkeitsinvarianz. Metriken treffen alle 5 s
Wanduhrzeit ein, unabhaengig von `sim.speed`. Bei speed = 100 entsprechen
60 Wanduhrminuten hundertmal so viel simulierter Zeit wie bei speed = 1 — ein in
Minuten definiertes Fenster wuerde im Zeitraffer eine voellig andere Statistik
sehen als im Feldbetrieb, und der Detektor waere zwischen beiden nicht
vergleichbar. Genau diese Vergleichbarkeit ist aber der Zweck der
Zeitrafferlaeufe.

**Nebenwirkung, bewusst in Kauf genommen.** Ein Fenster in Stichproben deckt im
Zeitraffer eine laengere simulierte Zeitspanne ab. Fuer die Bluetenerkennung ist
das unproblematisch, weil die Regel auf der Form der Zeitreihe arbeitet, nicht
auf absoluter Dauer. Bei spaeteren Regeln (Wanderung einer Front, Aussterben
einer Linie) ist erneut zu pruefen.

---

## A7 — Feldaufloesung 512 × 512

**Ort:** `config/params.yaml` → `sim.grid`

**Begruendung.** Kompromiss aus sichtbarer Struktur und Rechenlast auf
integrierter Grafik.

**Aufloesung.** Erster Meilenstein mit Abbruchrelevanz (Exposé §7.4,
Risiko 3): Lauffaehigkeit auf der Ziel-APU ist in Monat 1 zu verifizieren.
Rueckfallebene laut Risiko 2: groeberes Gitter bei halbiertem Zeitschritt.

---

## A8 — Modellgroesse ueber der im Exposé genannten Groessenordnung

**Ort:** `config/params.yaml` → `chronicle.model`

Eingetragen ist `google/gemma-4-12b-qat` — Gemma 4 12B QAT, Q4_0-quantisiert,
GGUF, rund 8,2 GB Speicherbedarf. **Erledigt:** Der Modellname war zunaechst ein
Platzhalter und ist am 29.07.2026 durch den tatsaechlichen API-Identifier aus
LM Studio ersetzt worden.

**Was offen bleibt.** Exposé §7.4 setzt das Sprachmodell mit „Groessenordnung
1–8 Mrd. Parameter" an. 12 Mrd. liegen darueber. Auf der Entwicklungshardware
(RX 7600 XT, 16 GB VRAM) ist das unproblematisch: 8,2 GB fuer das Modell lassen
der Simulation reichlich Raum, denn die Felder brauchen bei 512² auch als
RGBA32F nur wenige Megabyte.

Die Zielhardware ist aber ein **Mini-PC mit AMD-APU und geteiltem
Systemspeicher**. Dort konkurrieren Modell und Simulation um denselben Speicher,
und 8,2 GB sind eine harte Groesse. Genau dieser Fall ist Risiko 3 („Simulation
und Sprachmodell laufen nicht gemeinsam auf dem Mini-PC"), dessen Rueckfallebenen
in dieser Reihenfolge greifen: Feldaufloesung reduzieren, Simulationstakt senken,
**kleineres Sprachmodell**, im aeussersten Fall Chronikgenerierung auf einem
zweiten Rechner im Heimnetz.

**Aufloesung.** Bei der Verifikation der Zielhardware in Monat 1 mitmessen. Wenn
12B dort nicht traegt, ist der Wechsel auf ein kleineres Modell eine Zeile in
dieser Datei — die Chronikpipeline haengt nicht an der Modellgroesse. Die
schliesslich verwendete Groesse und die Begruendung gehoeren ins
Umsetzungskapitel.

**Nebenbefund.** Die im Dialog eingestellte Kontextlaenge von 8192 Tokens genuegt
fuer beide Chronikpfade deutlich: Ein Eintrag bekommt Ereignis, Kennzahlen und
Wetterlage uebergeben und erzeugt hoechstens `chronicle.max_tokens` Tokens. Auch
der Crew-Pfad bleibt darunter, weil `verifier` nur den Entwurf und dieselben
Zahlen sieht.

**Messung am 29.07.2026** gegen `/v1/chat/completions`, RX 7600 XT, Modell
geladen, Flash Attention aktiv.

Erste Messung mit einem **Minimalprompt** (144 Prompt-Tokens):

| Einstellung | Tokens gesamt | davon Reasoning | Dauer | Ergebnis |
|---|---|---|---|---|
| ohne Steuerung | 700 | 697 | 25,6 s | leerer Text |
| `reasoning_effort: low` | 535 | 473 | 19,4 s | 62 Tokens Text |
| `enable_thinking: false` | 511 | 446 | 18,6 s | 65 Tokens Text |

Zweite Messung mit dem **echten Chronik-Prompt** (595 Prompt-Tokens, also
Regelwerk und Beispiel):

| Einstellung | Tokens gesamt | davon Reasoning | finish | Dauer | Ergebnis |
|---|---|---|---|---|---|
| `max_tokens: 900`, effort low | 900 | 897 | length | 34,2 s | leer |
| `max_tokens: 2000`, effort low | 2000 | 1997 | length | 74,2 s | leer |
| `max_tokens: 4000`, effort low | 3426 | 3337 | stop | 129,4 s | Text |
| `max_tokens: 4000`, **ohne effort** | 1980 | 1868 | stop | **73,4 s** | Text |

Die zweite Messung korrigiert die erste in zwei Punkten, und beide Korrekturen
sind fuer die Arbeit relevant:

1. **Der Reasoning-Bedarf haengt am Prompt, nicht am Modell allein.** Mit dem
   ausfuehrlichen Regelwerk denkt das Modell rund viermal so lange wie mit einem
   Minimalprompt. Wer die Prompts in `chronicle/prompts/` aendert, muss
   `max_tokens` neu messen - sonst entstehen wieder stillschweigend leere
   Eintraege.
2. **`reasoning_effort: "low"` ist kontraproduktiv.** Es hat das Reasoning
   nahezu verdoppelt (1868 -> 3337 Tokens) und die Dauer von 73 s auf 129 s
   gebracht. LM Studio setzt den Parameter fuer dieses Modell offenbar nicht
   sinnvoll um. Er wird deshalb nicht mehr gesendet.

Damit liegt die tatsaechliche Latenz bei **rund 73 s je Aufruf**, nicht bei 20 s
wie zunaechst angenommen - der Crew-Pfad mit zwei Agenten entsprechend bei etwa
150 s, auf der Ziel-APU beim Mehrfachen. Bei einem Mindestabstand von 20 Minuten
zwischen Eintraegen traegt das noch, aber der Abstand zu Expose 7.4
("Generierungslatenz unkritisch") ist deutlich groesser als dort angenommen.

**Offene Frage fuer Phase 3.** Fuer die Aufgabe "drei nuechterne Saetze aus
gegebenen Zahlen" ist ein Reasoning-Modell moeglicherweise das falsche Werkzeug;
der erzeugte Text war eine Wiederholung der Eingabezahlen, keine Prosa. Der
Vergleich mit einem Nicht-Reasoning-Instruct-Modell gehoert in Phase 3, wenn
Crew- und Single-Pfad beide stehen und gegeneinander messbar sind.

---

## A10 — Reproduzierbarkeit gilt fuer den Lauf, nicht fuer den Chroniktext

**Ort:** `PLAN.md` (Definition of Done), `docs/contract.md` §7

Die Definition of Done verlangt: "Ein Lauf ist aus Seed, Config und Wetterlog
reproduzierbar." Das gilt fuer die Simulation, **nicht fuer den Wortlaut der
Chronikeintraege**.

**Begruendung.** Simulation, Metrikzeitreihe und Detektorausgabe sind
deterministisch: Bei gleichem Seed, gleicher Config und gleichem Wetterlog
treten dieselben Ereignisse zu denselben Ticks mit denselben Kennzahlen auf. Die
**Formulierung** ist es nicht. Kein llama.cpp-Backend garantiert bitgleiche
Ausgaben ueber Neuladungen hinweg - Batching und nichtdeterministische Kernel
reichen aus, um bei gleicher Temperatur und gleichem Seed abzuweichen. Bei einem
Reasoning-Modell kommt die Variabilitaet des Denkpfads hinzu.

**Die tragfaehige Formulierung** trennt deshalb zwei Eigenschaften:

- **Reproduzierbar** sind Lauf, Ereignisse und Kennzahlen.
- **Ueberpruefbar** ist der Chroniktext - ueber `metrics_ref`, wo genau die
  Zahlen stehen, die dem Modell uebergeben wurden.

Das ist ohnehin die Abnahmebedingung fuer Phase 3 ("ein Chronikeintrag, dessen
saemtliche Zahlen sich in der SQLite-Datenbank wiederfinden") und in der
Verteidigung haltbar. Die urspruengliche Fassung waere es nicht gewesen: Der
Einwand, dass ein LLM-erzeugter Text nicht reproduzierbar ist, kommt
vorhersehbar.

**Status.** Vom Verfasser am 29.07.2026 entschieden.

---

## A9 — Startwerte der Simulationsparameter

**Ort:** `config/params.yaml` → `field.*`, `flow.*`, `mass.*`

Saemtliche numerischen Startwerte sind begruendete Ausgangspunkte, keine
eingemessenen Werte. Sie sind so gewaehlt, dass die Groessenordnungen
zueinander passen (Umschlagzeit der Biomasse gegen Diffusionsweite gegen
Advektionsgeschwindigkeit).

**Aufloesung.** Einmessen in Phase 2 anhand der Zeitrafferlaeufe. Kriterium ist
nicht biologische Korrektheit (Exposé §5), sondern: kein Fixpunkt, keine
Ausloeschung, keine numerische Divergenz, Massenbilanz im Korridor. Die
schliesslich verwendeten Werte und der Weg dorthin gehoeren ins
Umsetzungskapitel.

---

## A11 — Der Zeitraffer liess das Wetter stehen (BEHOBEN am 30.07.2026)

**Ort:** `core/src/frame_core/environment/service.py`, `sim/src/main.ts`

**Gemessen am 30.07.2026:** In einem Zeitrafferlauf ueber 931.250 Ticks
(13,6 Welttage in 64 Sekunden Wanduhrzeit) ist die Produzentenbiomasse von 5739
auf **null** gefallen. Das System ist vollstaendig ausgestorben.

**Die Ursache ist kein Fehler in der Simulation, sondern in der Kopplung.**
`core` bildet das Wetter auf die **Wanduhrzeit** ab: Es interpoliert die
Stundenwerte auf *jetzt* und schickt alle 30 Sekunden einen neuen `env`-Satz.
`sim` dagegen laeuft im Zeitraffer mit bis zu hundertfacher Taktrate. Waehrend
in der Welt dreizehn Tage vergehen, vergeht draussen eine Minute - und der
Lichtwert bleibt der, der zum Startzeitpunkt galt. Der Lauf begann um 23 Uhr.
Die Welt hatte also dreizehn Tage lang **Nacht**, die Produzenten konnten nicht
photosynthetisieren und sind verhungert.

**Warum das ernst ist.** Der Zeitraffer ist im Exposé die Hauptgegenmassnahme
gegen Risiko 1 ("Die Simulation kippt im Langzeitbetrieb"). Er soll pruefen, ob
das System sechs Wochen uebersteht. Solange in diesen sechs Wochen die Sonne
nicht aufgeht, prueft er das Gegenteil von dem, was er pruefen soll - und liefert
ein garantiertes Aussterben, das mit dem Feldbetrieb nichts zu tun hat.

**Beim Beheben kam der eigentliche Fehler zum Vorschein.** Er lag tiefer als im
Zeitraffer: `sim.dt_base` stand auf 0,7, allein damit sechs Wochen bei
speed = 100 in unter zwei Stunden durchlaufen. Damit vergingen aber **auch im
Feldbetrieb sieben Weltsekunden je Wanduhrsekunde** - nach einer echten Woche
waeren in der Welt sieben Wochen vergangen. Der Klimakanal haette das reale
Wetter also grundsaetzlich nicht tragen koennen, nur langsamer falsch als im
Zeitraffer. Der Zeitrafferlauf hat einen Fehler sichtbar gemacht, der das
Zeitmodell insgesamt betraf.

### Die Loesung

**1. Echtzeit im Feldbetrieb.** `dt_base = 0.1` bei `tick_hz = 10` ergibt genau
eine Weltsekunde je Wanduhrsekunde bei `speed = 1`.

**2. Weltzeit-Nullpunkt.** `environment.epoch` ist der reale Zeitpunkt, der
Weltzeit 0 entspricht:

```
Wetterzeit = epoch + Weltzeit
```

`null` bedeutet Laufbeginn - der Feldbetrieb, in dem Wetterzeit und
Wirklichkeit zusammenfallen. Ein zurueckliegendes Datum laesst einen
Zeitrafferlauf **echtes Archivwetter** beschleunigt abspielen. Das deckt sich
mit Risiko 8 ("synthetisches Wetter aus historischen Daten") und macht einen
Zeitrafferlauf aus dem Wetterlog reproduzierbar.

**3. `sim` meldet seine Weltzeit** im Feld `world_time` der Metriknachricht.
Nicht aus `tick` ableitbar, weil der Zeitschritt ueber `env.rate` von der
Temperatur abhaengt. Erweiterung des Vertrags, siehe docs/contract.md.

**4. Glaettung in Weltzeit.** Die `smoothing_minutes` der Klimakopplungen
beziehen sich auf das Wettergeschehen und laufen deshalb auf der Weltzeit; im
Zeitraffer waeren sie sonst um den Zeitrafferfaktor zu traege.

**5. Zeitrafferobergrenze auf 1000.** Mit `dt_base = 0.1` braeuchten sechs
Wochen bei 100-fach zehn Stunden. Bei 500-fach sind es zwei Stunden bei
5.000 Ticks/s - gemessen wurden 10.092 Ticks/s. Das Expose nennt in Monat 2
"10-50-fach", schreibt das aber unter einem anderen Zeitbegriff; massgeblich
ist "sechs Wochen in wenigen Stunden" aus Risiko 1.

**Nachgewiesen** gegen echtes Archivwetter (Nuernberg, drei Junitage,
216 Stundenwerte): 15 helle und 9 dunkle Stichproben ueber 72 Welt-Stunden,
mit Niederschlagsereignissen und drehender Windrichtung. Der Tag-Nacht-Wechsel
laeuft also ueber die Weltzeit durch - genau das, was zuvor fehlte.

---

## A12 — Massendrift: fuenf sich gegenseitig maskierende Fehler (BEHOBEN)

**Ort:** `sim/src/shaders/react.frag`, `sim/src/shaders/advect.frag`,
`config/params.yaml` → `field.nutrient.refuge_floor`, `field.producer.max_density`

**Ausgangsbefund.** Ueber sieben Welttage meldete die Massenbilanz 6,344 %
unerklaerte Masse bei einer Toleranz von 2 % (`mass.drift_tolerance_pct`). Der
naheliegende Verdacht - die semi-lagrangesche Advektion aus A12 in der
urspruenglichen Fassung - war richtig, aber bei weitem nicht die ganze
Geschichte. Es waren **fuenf verschiedene Fehler**, die sich gegenseitig
maskiert haben: Jeder wurde erst sichtbar, nachdem der davor liegende behoben
war. Das ist der eigentliche Befund dieses Eintrags, nicht die einzelnen Fixes.

**1. Stille Klammern.** `max(nutrient, 0.0)` und `clamp(producer, ...)` in
`react.frag` erzeugten bzw. vernichteten Masse, ohne sie zu buchen - numerisches
Ueberschwingen an steilen Uebergaengen wurde stillschweigend auf null gehoben.
Nach Bilanzierung dieser beiden Klammern: **6,344 % → 4,538 %**. Der Fehler war
bis dahin verdeckt, weil die ohnehin driftende Advektion ein groesseres Signal
lieferte.

**2. Semi-lagrangesche Advektion ist nicht konservativ.** Das war der
urspruengliche Gegenstand dieser Annahme (siehe die durchgestrichene Fassung
unten in der Versionsgeschichte). Ersetzt durch **Reintegration Tracking** nach
Flow-Lenia, das Expose §3.2 ohnehin als Grundlage fuehrt: Jede Quellzelle
verteilt ihre Masse mit bilinearen Gewichten auf die vier Zellen um ihren
Zielort, die Gewichte summieren sich exakt zu eins. Im Fragment-Shader als
Gather ueber die 3×3-Nachbarschaft der Zielzelle umgesetzt, gueltig solange die
Verschiebung je Schritt unter einer Zelle bleibt - sie liegt bei den
ausgelieferten Parametern bei rund 0,21 Zellen, mit deutlichem Abstand.

**3. Die Dichte-Schere.** Nach der konservativen Advektion schnitt
`producer > max_density` zusammengeschobene Biomasse ab und buchte sie als
Austrag. Das war ein neuer, eigener Fehler: Konservative Advektion erhaelt die
Summe, verhindert aber keine lokale Konzentration - konvergente Stroemung
schiebt Masse zusammen, und das ist physikalisch richtig. Gemessen: Biomasse
5.728 → 55 binnen eines halben Welttages, waehrend der Austrag um denselben
Betrag stieg. Der Fehler war verdeckt, solange die alte dissipative Advektion
noch lief - sie glaettete, statt je etwas zusammenzuschieben. `max_density` ist
eine **Wachstumsgrenze** und wirkt bereits ueber den Faktor
`(1 − producer/max_density)` im Wachstumsterm; an der Dichteobergrenze wird
seither bewusst nicht mehr geschnitten.

**4. Das Refugium als Zufuhr.** Leergezehrte Zellen wurden in jedem Tick auf
`refuge_floor` aufgefuellt - eine unbegrenzte Naehrstoffquelle, sofern die
Produzenten sie sofort wieder aufzehren. Gemessen: **163.817 von 165.562
Gesamteintrag kamen daher, 98,9 %**, gegen 1.746 aus echtem Regen. Die
Gesamtmasse stieg auf das **2,46-fache** der Startmasse - der geschlossene
Kreislauf aus Expose §6.2 war ausgehebelt, und zwar durch eine Massnahme, die
gegen Risiko 1 gedacht war (kein dauerhaft totes Areal). Behoben als
**Entzugsschutz**: Wachstum und Sedimentation duerfen die letzte
`refuge_floor` nicht antasten. Gleiche Zusage - keine Flaeche faellt dauerhaft
tot - aber keine Masse mehr erzeugt.

**5. Asymmetrische Uebertragung in float32.** Der Naehrstoff liegt bei rund
0,4, der Abstand zweier darstellbarer float32-Zahlen dort bei rund 3·10⁻⁸. Ist
der uebertragene Betrag kleiner als dieser Abstand, verschwindet der Abzug beim
grossen Feld, waehrend die Gutschrift beim kleinen Bilanzkanal ankommt - Masse
aus dem Nichts, in jedem Tick, immer in dieselbe Richtung. Das Residuum wuchs
**linear** mit 0,58 % je Welttag, und genau diese Linearitaet hat den
systematischen Term verraten: zufaellige Rundungsfehler waeren mit der Wurzel
der Schrittzahl gewachsen, nicht linear mit ihr. Behoben durch **kompensierte
Uebertragung** an allen fuenf betroffenen Stellen im Shader: gebucht wird, was
tatsaechlich abging, nicht was abgehen sollte (`nutrientAfterX = nutrient - x;
actualX = nutrient - nutrientAfterX`). Driftrate danach **−0,105 % je
Welttag**, Faktor 5,5 besser als zuvor.

**Ergebnis.** Ein Siebentagelauf mit den behobenen fuenf Fehlern zeigt rund
−1 % Residuum ueber die volle Laufzeit - innerhalb der 2 % Toleranz.

**Warum kein Unit-Test das gefunden haette.** Keiner der fuenf Fehler waere in
einem isolierten Test aufgefallen: Jeder brauchte einen Lauf ueber Millionen
Ticks und eine Metrik, die unerklaerte Masse ueber die Zeit anzeigt, um
sichtbar zu werden - und jeder war erst messbar, nachdem der davorliegende
behoben war. Genau das ist die Rolle, die Expose §6.2 der Massenbilanz
zuschreibt: Stabilitaetsmetrik fuer TF2 und Nachweis, dass der Kreislauf haelt.
Sie hat sich hier zusaetzlich als das wirksamste Diagnosewerkzeug des gesamten
Simulationskerns erwiesen - nicht als Abnahmekriterium am Ende, sondern als
Instrument, das waehrend der Arbeit selbst Fehler freigelegt hat, die sonst
verdeckt geblieben waeren.

**Noch offen: Sedimentation findet faktisch nicht statt.** Die Sedimentation
entzieht je Tick rund 5,7·10⁻⁹ bei einem float32-Abstand von rund 3·10⁻⁸ am
Naehrstoffwert 0,4 - der Betrag liegt also unter der Darstellbarkeitsgrenze,
und der gemessene Austrag ist exakt null. Expose §6.2 verlangt aber
ausdruecklich einen Austrag gegenueber dem Eintrag, nicht nur einen
Bilanzkanal, der ihn korrekt mit null beziffert. Die Behebung - Sedimentation
nicht jeden Tick mit einem winzigen, sondern alle N Ticks mit dem N-fachen
Betrag - ist in Arbeit und noch nicht verifiziert.

**Zusammenhang mit dem Look.** Die Dissipation, die die urspruengliche
Advektion verloren hat, glaettete genau die feine Struktur, die das
Look-Development anstrebt (docs/lookdev.md). Masseerhaltende Advektion nach
Flow-Lenia loest beides zugleich - Bilanz und sichtbare Struktur -, waehrend
eine blosse Renormalisierung nur die Bilanz geloest haette. Diese Annahme war
der Grund, warum die Wahl zugunsten von Flow-Lenia gefallen ist.

<details>
<summary>Urspruengliche Fassung dieses Eintrags (30.07.2026), vor der Behebung</summary>

> **Gemessen am 30.07.2026** im selben Lauf wie A11. Der Residualsaldo verlief
> nicht monoton: −0,97 % bei 0,15 Welttagen, ein Spitzenwert von **−2,34 %** bei
> 5,1 Welttagen, dann wieder abfallend auf −0,46 % bei 13,6 Welttagen. Die
> Drift erreichte ihren Hoechstwert, solange das System lebte, und fiel danach
> wieder - ein totes Feld hat keine steilen Gradienten mehr, an denen die
> bilineare Interpolation Masse verliert. Der Spitzenwert lag ueber der
> Toleranz von `mass.drift_tolerance_pct`.
>
> Ursache: Semi-lagrangesche Advektion ist masseerhaltend nur im Grenzfall
> verschwindender Schrittweite; die bilineare Ruecksampelung glaettet und
> verliert dabei Masse an steilen Uebergaengen - bekanntes Verhalten des
> Operators, kein Umsetzungsfehler. Aufloesung damals offen zwischen
> masseerhaltender Advektion nach Flow-Lenia und protokollierter
> Renormalisierung pro Zeitschritt (Expose Risiko 2). Der Spitzenwert war
> zudem in einem durch A11 unrealistischen Lauf gemessen (dauerhafte Nacht,
> kollabierende Biomasse) und daher nicht belastbar zu beziffern.

</details>

---

## A13 — Q10 auf 1,3 statt auf den Lehrbuchwert 2,0

**Ort:** `config/params.yaml` → `coupling.rate`

**Der Befund.** Mit `q10 = 2.0` und Referenz 15 Grad ist die Kennlinie nur
zwischen +2 und +24 Grad wirksam; darueber und darunter liefert sie die
Klammerwerte. Gemessen an echtem Archivwetter (Nuernberg, drei Junitage) stand
die Rate in **15 von 24 Stichproben exakt auf `output_max`** - die
Temperaturkopplung lieferte also ueberwiegend eine Konstante.

**Warum das ein Problem ist und nicht nur ein Schoenheitsfehler.** Eine
Eingangsgroesse, die sich nicht aendert, ist fuer den Betrachter nicht
zuschreibbar. Damit faellt genau die Eigenschaft weg, um derentwillen die
1:1-Regel aus Expose 6.3 existiert. Schaerfer noch fuer die Feldstudie: Sie
laeuft Dezember bis Mitte Januar, wo Nuernberg regelmaessig unter den unteren
Klammerpunkt faellt - die Kopplung waere waehrend des gesamten
Evaluationszeitraums stumm gewesen, und TF1 haette sie nicht pruefen koennen.

**Die Wahl.** Die Klammern spannen den Faktor 1,8 / 0,4 = 4,5. Damit dieser
Bereich die Jahresspanne des Standorts abdeckt (rund -20 bis +37 Grad, 57 K):

```
q10 = 4.5^(10/57) = 1.3
```

Die Referenz wandert von 15 auf 10 Grad, naeher am Jahresmittel des Standorts,
damit die neutrale Rate 1,0 dort liegt, wo das Wetter die meiste Zeit ist.
Ergebnis derselben Messung: **3 von 24 statt 15 von 24** an der Klammer.

**Belastbarkeit.** Q10-Werte um 1,3 bis 1,5 sind fuer Vorgaenge auf
Oekosystemebene belegt und liegen unter dem oft genannten Bereich 2 bis 3 fuer
einzelne Enzymreaktionen. Das Expose misst ohnehin an Plausibilitaet im
Erleben, nicht an biologischer Korrektheit (5). Der Wert ist damit begruendbar,
gehoert aber als bewusste Abweichung vom Lehrbuchwert ins Umsetzungskapitel -
mitsamt der Messung, die ihn ausgeloest hat.

**Offen.** Der Wert ist auf Nuernberg gerechnet. Steht das Objekt in einem
Haushalt mit anderem Klima, ist er neu zu bestimmen. Er haengt also am
Standort, genau wie `environment.latitude`.

---

## A14 — Detektorfenster in Weltzeit statt in Stichproben

**Ort:** `config/params.yaml` → `detector.bloom`,
`core/src/frame_core/detect/bloom.py`, `core/src/frame_core/metrics/store.py`

**Loest A6 ab.** A6 definierte Fenster und Sperrzeit in Stichproben, um die
Statistik geschwindigkeitsinvariant zu halten. Das gelingt auch — nur deckt
dieselbe Stichprobenzahl voellig verschiedene Weltzeiten ab:

| Betriebsart | Abstand je Stichprobe | Fenster (720 Punkte) |
|---|---|---|
| Feldbetrieb `speed = 1` | 5 Weltsekunden | **1 Weltstunde** |
| Zeitraffer `speed = 500` | 2500 Weltsekunden | **20,8 Welttage** |

**Warum das ernst ist.** Eine Bluete entwickelt sich ueber Stunden bis Tage
(Verdopplung 4 h, Lebensdauer 60 h). Ein gleitender Median ueber **eine
Weltstunde** folgt ihr einfach mit - sie hebt sich nie von ihrer eigenen
Vergleichsbasis ab. Der Detektor waere im Feldbetrieb nahezu blind gewesen, und
aufgefallen waere es erst in Monat 3, wenn die Chronik leer bleibt und niemand
mehr weiss, ob das an der Simulation oder am Detektor liegt.

Der Fund kam aus einer Nebenrechnung waehrend des ersten gueltigen
Zeitrafferlaufs, nicht aus einem Test - die Tests waren gruen, weil sie
Stichprobenzahlen gegen Stichprobenzahlen prueften.

**Die Loesung.** Fenster und Sperrzeit stehen in **Weltstunden**. Die
Metriknachricht traegt `world_time` bereits (A11), der Speicher waehlt also
nach Weltzeitspanne aus statt nach Zeilenzahl:

    window_world_hours: 120.0      # 5 Welttage
    refractory_world_hours: 48.0   # 2 Welttage
    min_samples: 120               # statistische Untergrenze, unabhaengig davon
    max_window_samples: 2000       # Kostendeckel mit gleichmaessiger Ausduennung

`min_samples` bleibt in Stichproben, weil es eine andere Frage beantwortet: Mit
weniger Punkten ist der Median nicht belastbar, gleich wieviel Weltzeit sie
abdecken. `max_window_samples` deckelt die Kosten - im Feldbetrieb fielen in
120 Weltstunden sonst rund 86.000 Punkte an.

**Nachgewiesen** durch `test_gleiche_weltzeitspanne_ergibt_gleiche_entscheidung`:
Dieselbe Kurve, einmal fein (6000 Punkte, Feldbetrieb) und einmal grob
(240 Punkte, Zeitraffer) abgetastet, ergibt dieselbe Bluetenentscheidung.

**Nachtrag: der Abtastdeckel `sim.max_world_seconds_per_sample`.** Das
Weltzeitfenster allein reichte nicht - ohne einen Deckel auf den Abstand
zweier Readbacks skaliert die Abtastdichte selbst mit dem Zeitraffer. Bei
`speed = 500` liegen zwischen zwei Messpunkten 2.500 Weltsekunden statt 5 im
Feldbetrieb. Gemessen: Ein Siebentagelauf erzeugte dadurch nur **79
Messpunkte**, waehrend `min_samples` auf 120 steht - der Detektor kam nie ueber
seine statistische Untergrenze, und die Chronik blieb zwangslaeufig leer. Nicht
weil kein Ereignis stattfand, sondern weil zu wenige Stichproben vorlagen, um
darueber ueberhaupt zu urteilen.

**Ein erster Behebungsversuch griff ins Leere.** Der erste Fix deckelte nur die
Abschnittslaenge innerhalb eines Zeitraffer-Bursts, waehrend der Readback von
der GPU weiterhin ueber die Wanduhrzeit ausgeloest wurde
(`sim.readback_interval_s`) - der eigentliche Engpass blieb also unberuehrt.
Vorhergesagt waren 156 Messpunkte, gemessen wurden 158: Die Aenderung tat fast
nichts. Erst als die Ausloesung selbst auf den Weltzeitdeckel umgestellt wurde
(`max_world_seconds_per_sample`, siehe `config/params.yaml` → `sim`), stieg die
Zahl auf **303 Punkte**. Der Fund ist eine Erinnerung daran, dass ein
Deckelwert wirkungslos bleibt, wenn er neben statt an der tatsaechlichen
Ausloeseschwelle sitzt.

---

## A15 — Wachstum gegen Sterben: die Drosselungsfalle

**Ort:** `config/params.yaml` → `field.producer`

**Der Fehler.** Verdopplungszeit 9 h gegen Lebensdauer 26 h liest sich wie
"Wachstum gewinnt 2:1". Tatsaechlich verlor es um Faktor 3,2, und die Biomasse
fiel im Zeitrafferlauf vom 30.07.2026 in drei Welttagen von 5000 auf 1087.

**Die Ursache.** Das Wachstum wird zweifach gedrosselt, das Sterben nicht:

    Naehrstofffaktor   n/(n+half)                  rund 0,63
    Lichtfaktor        L/(L+half), Tagesmittel     rund 0,25   <- nachts NULL
    ------------------------------------------------------------------------
    wirksames Wachstum = Rohrate * 0,157

**Die Produzenten sterben rund um die Uhr, wachsen aber nur tagsueber.** Der
Lichtfaktor ist nicht etwa "im Mittel 0,7", sondern die Haelfte der Zeit exakt
null - und das Sterben laeuft weiter.

**Faustregel fuer jede kuenftige Aenderung:**

    doubling_time_hours  <  lifetime_hours * 0,157 * ln 2

Bei 60 h Lebensdauer sind das rund 6,5 h als Obergrenze. Gesetzt sind 4,0 h,
was dem Wachstum rund 60 % Vorsprung laesst - genug fuer eine Bluete, nicht
genug fuer eine Dauerexplosion, die ohnehin von `max_density` und der
Naehrstoffzehrung gebremst wird.

**Warum das eine Entwurfsentscheidung ist und keine Einstellung.** Die beiden
Zeitkonstanten legen fest, auf welcher Zeitskala das Bild atmet - also genau
die Groesse, um die es in der Arbeit geht. Sie stehen in Stunden in der Config,
damit dieser Zusammenhang lesbar bleibt; als Raten je Weltsekunde waere der
Fehler nicht aufgefallen und auch nicht erklaerbar gewesen.

---

## A16 — Soak-Laeufe brauchen ein sichtbares Fenster

**Ort:** `sim/src/main.ts` (Soak-Modus), Betriebsdokumentation

Chrome drosselt in verborgenen Tabs sowohl Zeitgeber als auch GPU-Arbeit.
Gemessen: rund 10.000 Ticks/s bei sichtbarem Fenster gegen rund 1.000 Ticks/s
bei verborgenem - Faktor zehn.

**Folge.** Ein Messlauf am Entwicklungsrechner muss im Vordergrund laufen. Im
Kioskbetrieb ist das ohnehin gegeben, dort ist das Fenster immer sichtbar.

**Zusammenhang mit dem Entwurf.** Dies ist derselbe Mechanismus, der in Phase 2
die Tick-Schleife aus `requestAnimationFrame` herausgezwungen hat: Ein
verborgenes Fenster fuehrt rAF ueberhaupt nicht mehr aus. Der Zeitgeber laeuft
weiter, nur langsamer - die Welt bleibt also stehen, statt zu sterben. Das ist
der Unterschied zwischen der damaligen Fehlkonstruktion und dieser
Betriebseigenschaft.

---

## A17 — In Prototyp 0 ist keine anhaltende Schwingung zu erwarten

**Ort:** Erwartungshaltung an die Chronik in Prototyp 0; betrifft die
Interpretation der Zeitrafferlaeufe und die Abnahmebedingung „Biomasse
konvergiert nicht auf einen Fixpunkt" (`PLAN.md`, Definition of Done).

**Der Befund.** Expose §6.2 schreibt die dauerhafte Bewegung des Systems
ausdruecklich der Raeuber-Beute-Kopplung zu - also den Konsumenten, die erst in
Prototyp 1 hinzukommen. Prototyp 0 hat nur eine trophische Ebene: Produzenten
und Naehrstoff. Fuer ein System dieser Art ist eine **gedaempfte Annaeherung an
eine Tragfaehigkeit** zu erwarten, keine anhaltende Schwingung - eine
Raeuber-Beute-Dynamik braucht mindestens zwei gekoppelte Populationen, um sich
selbst zu ueberschiessen.

**Woher die bisher gemessene Varianz stammt.** Sie stammt ueberwiegend aus dem
Tagesgang, also aus der Antriebsgroesse Licht, nicht aus einer Eigendynamik des
Systems. Ein System, das im Wesentlichen seinem Antrieb folgt, erzeugt keine
Bluete im Sinn des Detektors - eine Bluete ist per Definition ein Ausschlag
**gegenueber** dem gleitenden Median, nicht eine Wiederholung desselben Musters
im Tagesrhythmus.

**Folge fuer die Erwartung an die Chronik.** Bleibt die Chronik in Prototyp 0
duenn oder leer, ist das nach diesem Befund ein **strukturelles Ergebnis und
kein Defekt** - und es gehoert so in die Arbeit, nicht als offener
Debugging-Punkt. Ein gleitender Median, der mit monoton wachsender Biomasse
selbst mitwaechst, kann per Konstruktion keinen Ausschlag gegen sich selbst
registrieren; eine Bluete braucht einen Ausschlag, keinen Anstieg.

**Beleg.** Beide bisherigen Siebentagelaeufe erzeugten null Chronikeintraege,
bei monoton wachsender Biomasse von 3.768 auf 60.537. Das ist konsistent mit
der obigen Erwartung, nicht mit einem Fehler im Detektor (siehe A14, wo der
Fehler - zu wenige oder falsch bemessene Stichproben - ein anderer und bereits
behobener war).

**Aufloesung.** Keine Codeaenderung noetig. Fuer die Arbeit ist festzuhalten,
dass ein Vergleich „Chronikdichte Prototyp 0 gegen Prototyp 1" erst nach
Einfuehrung der Konsumenten aussagekraeftig ist - vorher fehlt die Kopplung, die
laut Expose §6.2 die Bewegung ueberhaupt erzeugt.

---

## Nicht getroffene Annahmen

Ausdruecklich **offen gelassen** und nicht implizit festgelegt:

- **Die Interaktionsform** (Exposé §6.5, Optionen A/B/C). Weder
  `config/params.yaml` noch die Verzeichnisstruktur noch der Vertrag enthalten
  ein Feld, ein Modul oder eine Nachricht dafuer. Die Entscheidung faellt
  dokumentiert am Ende von Monat 1. Das Entwickler-Overlay aus Prototyp 0 ist
  keine Interaktionsform, sondern ein Diagnosewerkzeug.
- **Panelgroesse und Format** (Exposé §6.1).
- **Register der Chronikeintraege** (Exposé §6.4) — wird im Look-Development
  geprueft; in Prototyp 0 steht im Prompt der nuechtern-beobachtende Ansatz aus
  dem Exposé, ohne Ich-Erzaehler.
- **Raummikrofon oder Audio-Loopback** (Exposé §7.5, offener Punkt). Der
  Audio-Stub steht hinter einem Interface, das beides zulaesst.
