# Annahmen

Jede Annahme, die im Verlauf des Projekts getroffen wurde, mit Begruendung und
dem Weg, sie aufzuloesen. Im Code sind die zugehoerigen Stellen mit
`# ANNAHME:` markiert.

Der Zweck dieser Datei ist nicht Buchhaltung: In der Arbeit muss jede
Entwurfsentscheidung begruendet werden, und eine Annahme, die sechs Monate
spaeter niemand mehr als Annahme erkennt, wird stillschweigend zur Tatsache.

**Stand: Phase 0.**

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

## A6 — Detektorfenster in Messpunkten statt in Minuten

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
geladen, Flash Attention aktiv:

| Einstellung | Tokens gesamt | davon Reasoning | Dauer | Ergebnis |
|---|---|---|---|---|
| ohne Steuerung | 700 | 697 | 25,6 s | leerer Text |
| `reasoning_effort: low` | 535 | 473 | 19,4 s | 62 Tokens Text |
| `enable_thinking: false` | 511 | 446 | 18,6 s | 65 Tokens Text |

Daraus folgt dreierlei. Erstens zaehlen die Reasoning-Tokens gegen `max_tokens`;
der urspruengliche Wert 220 haette **stillschweigend leere Eintraege** erzeugt.
Zweitens laesst sich das Reasoning nicht abschalten, nur daempfen. Drittens ist
die Latenz mit rund 20 s je Aufruf zwar unkritisch bei einem Mindestabstand von
20 Minuten zwischen Eintraegen, aber deutlich hoeher als die Formulierung in
Expose 7.4 nahelegt - der Crew-Pfad liegt bei etwa 40 s, auf der Ziel-APU
entsprechend hoeher.

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
