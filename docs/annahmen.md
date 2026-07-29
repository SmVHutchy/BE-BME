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

## A8 — Modellname als Platzhalter

**Ort:** `config/params.yaml` → `chronicle.model`

Eingetragen ist `qwen2.5-7b-instruct`.

**Begruendung.** LM Studio ist als Endpunkt gesetzt, der HTTP-Server antwortete
zum Zeitpunkt der Einrichtung aber nicht auf Port 1234 (im Developer-Tab
vermutlich nicht gestartet), sodass der geladene Modellname nicht ausgelesen
werden konnte.

**Aufloesung.** Vor Phase 1: Server starten, `GET /v1/models` abfragen, den
exakten Namen eintragen. Eine Zeile.

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
