# Übergabe — Prompt für die nächste Sitzung

Kopiere den Block unter „Der Prompt" in eine neue Sitzung. Alles darunter ist
Beleg und Nachschlagewerk.

---

## Der Prompt

```text
ROLLE
Du bist Senior Engineer für langlaufende Echtzeitsysteme. Du übernimmst ein
laufendes Bachelorarbeitsprojekt (E:\Projekte\BE-BME) in Phase 4. Prototyp 0
ist weitgehend gebaut und läuft; es geht um Abschluss, Nachweise und
Dokumentation — nicht um neue Features.

ZUERST LESEN, vollständig und in dieser Reihenfolge:
  1. CLAUDE.md            — sieben nicht verhandelbare Regeln
  2. docs/annahmen.md     — A1 bis A17, das Gedächtnis des Projekts
  3. PLAN.md              — Phasen, Definition of Done
  4. docs/uebergabe.md    — dieses Dokument, Abschnitt „Stand" und „Fallen"
  5. docs/expose.md       — verbindliche Spezifikation, gewinnt bei Konflikt

ARBEITSWEISE, die sich in diesem Projekt bewährt hat:
- Messen statt vermuten. Die Massenbilanz hat fünf Fehler nacheinander
  aufgedeckt, die sich gegenseitig maskiert hatten. Jeder wurde erst sichtbar,
  nachdem der davor behoben war. Ändere deshalb IMMER nur eine Sache und miss
  danach, sonst weißt du hinterher nicht, was gewirkt hat.
- Gegenproben kosten zwei Minuten und sparen Stunden. Beispiel: Ein Lauf mit
  abgeschalteter Strömung isolierte die Advektion als Ursache und widerlegte
  eine falsche Vermutung, bevor daran weitergebaut wurde.
- Jede Zahl in die Config, mit begründender Kommentarzeile. Keine Literale im
  Shader oder Detektor.
- Bei Unsicherheit fragen. Bei getroffenen Annahmen: `# ANNAHME:` im Code UND
  ein Eintrag in docs/annahmen.md.

SOFORT ZU ERLEDIGEN (in dieser Reihenfolge):
1. Sieben Dateien sind unversioniert, darunter die getaktete Sedimentation und
   ein neues Skript. Sichte, prüfe, committe — siehe „Offene Änderungen".
2. Die getaktete Sedimentation wurde gebaut, aber der Nachweis fehlt:
   `mass.sedimentation_interval_ticks: 100`. Ein Lauf muss zeigen, dass der
   Austrag jetzt größer null ist. Er stand zuvor bei exakt 0,0.
3. env_applied hat keine Tick- oder Weltzeitspalte, obwohl der Docstring in
   store.py genau das behauptet. Schema ergänzen.

DANACH, als Arbeitspakete verteilbar — Details unten unter „Arbeitspakete".

STOPP-REGEL: Nach jedem Paket anhalten, Ergebnis mit Zahlen berichten, auf
Freigabe warten. Nicht durchlaufen.
```

---

## Stand

**Committet und abgeschlossen:** Phasen 0 bis 3 vollständig, Phase 4 zu großen
Teilen. 78 Tests grün, Strukturprüfung bestanden.

| Bereich | Stand |
|---|---|
| Simulation (GLSL, Ping-Pong, Zeitraffer, Snapshot) | gebaut |
| Umweltdienst mit echtem Archivwetter | gebaut, nachgewiesen |
| Metrikspeicher, Regeldetektor | gebaut, getestet |
| Chronik: `SingleChronicle` + `TwoStepChronicle` | gebaut, getestet, **ohne CrewAI** |
| Watchdog, Soak-Modus, Auswertungsskript | gebaut |
| Massenbilanz A12 | **BESTANDEN**, 0,948 % bei 2 % Toleranz |

**Der letzte Soak-Bericht (7 Welttage, echtes Archivwetter):**

```
1. Ueberleben          [ OK ] Biomasse 5.839 -> 22.055
2. Keine Konvergenz    [ OK ] Varianz > 0, Spannweite 4.768-22.055
3. Massenbilanz        [ OK ] groesstes Residuum 0,948 % (Toleranz 2,0 %)
   Massenkorridor      [ OK ] 0,991-1,000 bei erlaubten 0,7-1,4
4. Klimakanal          [ OK ] 14 von 22 hell, Licht 0,000-0,947
   Q10 an der Klammer  [ -- ] 0 von 22
5. Chronik             [ -- ] 0 Eintraege
6. Betrieb             [ -- ] 0 Neustarts, keine verworfenen Ticks
GESAMT: BESTANDEN
```

---

## Offene Änderungen im Arbeitsbaum

Sieben Dateien, unversioniert. Alle geprüft lauffähig (Tests grün,
Typecheck sauber), aber der Sedimentationsnachweis fehlt.

| Datei | Was |
|---|---|
| `config/params.yaml` | `mass.sedimentation_interval_ticks: 100` neu |
| `core/src/frame_core/config.py` | dasselbe Feld im Modell |
| `sim/src/sim/params.ts`, `sim/src/main.ts` | Uniform durchgereicht |
| `sim/src/shaders/react.frag` | getaktete Sedimentation |
| `PLAN.md`, `docs/annahmen.md` | A12-Auflösung, A14-Ergänzung, A17 neu |
| `scripts/verify_reproducibility.py` | **neu**, noch nie gegen zwei echte Läufe gelaufen |

---

## Arbeitspakete

Vier der sechs Pakete brauchen **dieselbe GPU, denselben Browser, dieselbe
Datenbank**. Sie lassen sich nicht parallelisieren — Läufe schreiben alle nach
`data/`, und jede Änderung unter `sim/` löst einen Vite-Reload aus, der einen
fremden Lauf abbricht. Dokumentation und reine Python-Arbeit lassen sich
abgeben.

| # | Paket | Wer | Abhängig von |
|---|---|---|---|
| 1 | Sedimentationsnachweis: Austrag > 0 | Hauptsitzung | — |
| 2 | `env_applied` um `world_time` ergänzen (Schema + Store + Skript) | Agent | — |
| 3 | Regenlauf: Kopplung 2, Detektor, erster echter Chronikeintrag | Hauptsitzung | 1 |
| 4 | Reproduzierbarkeit nachweisen (DoD) | Hauptsitzung | 2, Skript |
| 5 | Snapshot/Restore nachweisen (Exposé §7.4) | Hauptsitzung | — |
| 6 | Sechs-Wochen-Lauf (DoD: unter zwei Stunden) | Hauptsitzung | 1, 3 |

**Paket 2 im Detail, weil es sauber abgrenzbar ist:** `env_applied` in
`core/src/frame_core/metrics/store.py` hat nur einen Wanduhr-Zeitstempel. Der
Docstring behauptet, die Tabelle halte fest, „welche env-Werte bei welchem Tick
galten" — das stimmt nicht. `metrics` hat `world_time` bereits;
`env_applied` braucht es auch, samt Index und angepasstem `insert_env`. Danach
kann `scripts/verify_reproducibility.py` die Klimawerte tickgenau vergleichen
statt nur ordinal. Berührt: `store.py`, `api.py` (Aufrufstelle),
`verify_reproducibility.py`, ein Test. Nicht berührt: `sim/`, Shader, Config.

**Paket 3 im Detail:** Beide bisherigen Läufe erzeugten null Chronikeinträge.
Das ist **kein Fehler** — die Biomasse wuchs monoton, ein gleitender Median
wächst mit, und eine Blüte braucht einen Ausschlag. Dazu war die gewählte
Junihälfte fast regenfrei: Eintrag 1.746 gegen Austrag 4.381, Regenanteil am
Gesamteintrag 1,1 %. Für Paket 3 eine **regenreiche Epoche** aus dem
Wetter-Rohlog auswählen, `environment.epoch` darauf setzen und erneut laufen
lassen. Siehe auch A17: In Prototyp 0 ist keine anhaltende Schwingung zu
erwarten, weil die Konsumenten fehlen — eine dünne Chronik wäre ein
strukturelles Ergebnis, kein Defekt.

---

## Fallen, die diese Sitzung Zeit gekostet haben

**Laufparameter stehen auf Zeitraffer, nicht auf Feldbetrieb.**
`environment.epoch: "2026-06-18T00:00:00+02:00"` und `sim.speed: 500.0`. Für
den Feldbetrieb müssen sie auf `null` und `1.0`. Steht auch im README.

**Das Browserfenster muss sichtbar sein** (A16). Chrome drosselt Zeitgeber und
GPU-Arbeit in verborgenen Tabs um Faktor zehn — 10.000 gegen 1.000 Ticks/s. Ein
Screenshot holt den Tab in den Vordergrund und hebt die Drosselung auf.

**Vor jedem Lauf aufräumen.** `core` stoppen, warten, `data/` leeren, dann neu
starten. Sonst hält der alte Prozess die SQLite-Datei, der Port ist belegt, und
es entstehen mehrere `run_id` in derselben Datenbank.

**Das Overlay hängt hinterher.** Es rendert über `requestAnimationFrame`, das im
verborgenen Tab nicht läuft. Die Datenbank ist die Wahrheit, nicht die Anzeige.

**`core` muss aus dem Wurzelverzeichnis starten:**
`uv run --project core uvicorn frame_core.api:app --port 8000`. Ein
`cd core && uv run uvicorn ...` bricht mit `FileNotFoundError: config/params.yaml`
ab — dieser Fehler stand ein halbes Projekt lang falsch im README.

**PowerShell statt Bash für Befehle.** Der Windows-PATH kommt in der Bash-Umgebung
als Semikolon-String an, den bash nicht parsen kann; `uv`, `git` und `tail` sind
dort teilweise nicht auffindbar. Mehrzeilige Commit-Nachrichten über
`git commit -F datei` statt `-m`, sonst zerlegen Anführungszeichen die
Argumentübergabe.

---

## Was in dieser Sitzung gelernt wurde und nicht verlorengehen darf

Die Massenbilanz meldete 6,344 % unerklärte Masse. Es waren **fünf** Fehler,
die sich gegenseitig verdeckten:

1. **Stille Klammern** buchten Masse nicht → 6,344 auf 4,538 %
2. **Semi-lagrangesche Advektion** ist nicht konservativ → ersetzt durch
   Reintegration Tracking (Flow-Lenia, Exposé §3.2)
3. **Die Dichte-Schere** löschte zusammengeschobene Biomasse → 5.728 auf 55
   binnen eines halben Welttages
4. **Das Refugium als Zufuhr** war eine unbegrenzte Nährstoffquelle → 98,9 %
   des Gesamteintrags, Gesamtmasse auf das 2,46-fache
5. **float32-Asymmetrie**: Abzug verschwindet, Gutschrift kommt an → lineares
   Wachstum von 0,58 % je Welttag

Der methodische Kern: **Kein einziger hätte sich in einem Unit-Test gezeigt.**
Alle brauchten einen Lauf über Millionen Ticks und eine Metrik, die unerklärte
Masse anzeigt. Genau die Rolle, die Exposé §6.2 der Massenbilanz zuschreibt.

Und ein Muster, das sich wiederholt hat: **Linear wachsende Fehler sind
systematisch, wurzelförmig wachsende sind Rauschen.** Diese Unterscheidung hat
den float32-Term identifiziert.

---

## Agenten-Anweisung

Ein frisch gestarteter Agent kennt A1 bis A17 nicht. In diesem Repo ist das ein
echtes Risiko, kein theoretisches: Er könnte in bester Absicht die Dichte-Schere
wieder einbauen oder das Refugium zurück auf Zufuhr stellen — beides waren
Fehler, die eine Sitzung lang gekostet haben, und beide sehen im Code
vernünftig aus. Der **Pflichtkopf** unten trägt das mit.

### Pflichtkopf für jedes Briefing

```text
Du arbeitest im Repository E:\Projekte\BE-BME an einer Bachelorarbeit
(künstliches Ökosystem im Bilderrahmen, Dauerbetrieb über Monate).

LIES ZUERST, vollständig:
  CLAUDE.md          — sieben nicht verhandelbare Regeln
  docs/annahmen.md   — A1 bis A17, das Gedächtnis des Projekts
  docs/uebergabe.md  — Stand, Fallen, Arbeitspakete

SIEBEN HARTE REGELN, die du nicht verletzen darfst:
1. Eine Eingangsgröße, ein Angriffspunkt. Keine siebte Kopplung.
2. Kein Sprachmodell im Simulationstakt.
3. Kein Sprachmodell in der Ereigniserkennung — der Detektor ist reines Python.
4. Der Chronikpfad liest, er greift nicht ein. Kein Schreibzugriff auf den
   Simulationszustand, in keiner Richtung.
5. Kein Netzverkehr auf dem Chronikpfad. Nur der lokale Endpunkt aus der Config.
6. Nichts CUDA-Abhängiges.
7. Keine Magic Numbers. Jeder Zahlenwert kommt MIT begründender Kommentarzeile
   in config/params.yaml, nie als Literal in Shader oder Detektor.

DIE OFFENE ENTSCHEIDUNG: Die Interaktionsform (Exposé §6.5) ist ausdrücklich
offen und darf auch nicht IMPLIZIT festgelegt werden — nicht durch ein
Config-Feld, nicht durch ein Modul, nicht durch eine Vertragsnachricht. Wenn dir
eine Stelle begegnet, an der die Entscheidung fallen müsste: anhalten und
fragen. Nicht die naheliegende Variante wählen und weiterbauen.

FÜNF DINGE, DIE DU NICHT RÜCKGÄNGIG MACHEN DARFST — sie sehen jeweils wie
Verbesserungen aus und waren teuer erkämpft (docs/annahmen.md A12):
- KEINE Schere an `max_density` in react.frag. Das ist eine Wachstumsgrenze und
  wirkt bereits über den Faktor (1 − producer/max_density). Sie zusätzlich als
  nachträglichen Schnitt zu benutzen löscht Masse: Biomasse fiel 5.728 → 55.
- Das Refugium ist ENTZUGSSCHUTZ, keine Zufuhr. Als Auffüllung war es eine
  unbegrenzte Nährstoffquelle — 98,9 % des Gesamteintrags.
- Die Advektion ist masseerhaltend (Reintegration Tracking). Nicht durch
  semi-lagrangesche Rücksampelung ersetzen, die ist nicht konservativ.
- Übertragungen sind KOMPENSIERT: gebucht wird, was tatsächlich abging, nicht
  was abgehen sollte. Sonst kippt die float32-Asymmetrie die Bilanz.
- `sim.speed` vervielfacht die TAKTRATE, nicht den Zeitschritt. Über dt
  skaliert würde die Diffusion sofort divergieren.

ARBEITSWEISE:
- Ändere immer nur eine Sache und miss danach. Die Massenbilanz hat fünf Fehler
  aufgedeckt, die sich gegenseitig maskierten — jeder wurde erst sichtbar,
  nachdem der davor behoben war.
- Bei Annahmen: `# ANNAHME:` im Code UND ein Eintrag in docs/annahmen.md.
- Code und Bezeichner englisch, Kommentare und Doku deutsch.
- Läuft `core` beim Testen: aus dem WURZELVERZEICHNIS starten, mit
  `uv run --project core uvicorn frame_core.api:app --port 8000`.

ABNAHME, immer:
- `cd core && uv run pytest -q` grün (derzeit 78 Tests)
- `uv run --with pyyaml python scripts/verify_structure.py` bestanden
- bei Änderungen unter sim/: `cd sim && npx tsc --noEmit` sauber
- KEIN Commit. Änderungen im Arbeitsbaum liegen lassen — die Hauptsitzung prüft
  gegen die sieben Regeln und committet.

BERICHTE AM ENDE: welche Dateien du geändert hast, welche neuen Config-Schlüssel
mit welcher Begründung entstanden sind, und ob dir etwas aufgefallen ist, das
gegen eine der sieben Regeln arbeitet — auch außerhalb deines Auftrags. Melde
es, statt es stillschweigend zu übergehen oder eigenmächtig zu ändern.
```

### Was in jedes Briefing zusätzlich gehört

**Sperrbereiche, namentlich.** Nicht „fass nichts anderes an", sondern die
konkreten Pfade: „FASSE NICHT AN: `sim/`, `core/src/frame_core/detect/`,
`docs/`. Dort läuft parallel andere Arbeit." Ohne das räumen zwei Agenten
dieselbe Datei auf.

**Warum eine Entscheidung so gefallen ist**, nicht nur was zu tun ist. Der
Chronik-Agent brauchte den Satz „CrewAI wurde gestrichen, weil das Exposé
Agenten nur als Abgrenzung nennt" — sonst hätte er gebaut, was gerade bewusst
verworfen worden war.

**Zahlen statt Adjektive.** „Der Austrag stand bei exakt 0,0" ist überprüfbar,
„die Sedimentation funktionierte nicht richtig" nicht.

### Fertiges Briefing für Paket 2

```text
[Pflichtkopf einfügen]

AUFGABE: `env_applied` um die Weltzeit ergänzen.

Die Tabelle in core/src/frame_core/metrics/store.py hat nur einen
Wanduhr-Zeitstempel. Der Docstring desselben Moduls behauptet, sie halte fest,
„welche env-Werte bei welchem Tick galten" — das stimmt nicht, und deshalb kann
scripts/verify_reproducibility.py die Klimawerte nur ordinal vergleichen statt
tickgenau. Für die Reproduzierbarkeit aus Seed, Config und Wetterlog ist das
eine echte Lücke: Die Glättung hängt vom Zeitpunkt der Nachführung ab, und der
ist aus den Rohdaten allein nicht ableitbar.

`metrics` hat `world_time` bereits — orientiere dich daran, samt Index.

BERÜHRT: store.py (Schema, insert_env, Index), api.py (Aufrufstelle in
environment_push_loop), scripts/verify_reproducibility.py (Vergleich von
ordinal auf tickgenau umstellen), ein Test in core/tests/.

FASSE NICHT AN: sim/, config/params.yaml, docs/, PLAN.md, README.md.

Die Datenbank unter data/ ist Wegwerfware und wird vor jedem Lauf gelöscht —
eine Migration brauchst du nicht, eine Schemaänderung genügt.

ABNAHME zusätzlich: verify_reproducibility.py --help läuft weiterhin, und das
Skript meldet sauber, wenn nur ein Lauf in der Datenbank liegt.
```

---

## Weiterhin ausdrücklich offen

Die **Interaktionsform** (Exposé §6.5) — Sprache, Anwesenheit oder beides. Sie
darf auch nicht implizit festgelegt werden: nicht durch ein Config-Feld, nicht
durch ein Modul, nicht durch eine Vertragsnachricht. Wenn eine Stelle begegnet,
an der die Entscheidung fallen müsste: **anhalten und fragen.**
