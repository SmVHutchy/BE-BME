# PLAN — Umweltgekoppeltes künstliches Ökosystem im Bilderrahmen

Bachelorarbeit Media Engineering, TH Nürnberg. Verfasser: Liam Moosburger.
Verbindliche Spezifikation: [`docs/expose.md`](docs/expose.md). Bei jedem
Konflikt zwischen diesem Plan und dem Exposé gewinnt das Exposé.

---

## 1. Was gebaut wird

Ein Bilderrahmen an der Wand, in dem ein künstliches Ökosystem in Echtzeit
läuft — über Monate, im häuslichen Dauerbetrieb.

Nährstofffeld mit Diffusion, zwei trophische Ebenen, Vererbung mit Mutation,
Strömungsfeld. Der Stoffkreislauf ist geschlossen: Was stirbt, zerfällt ins
Nährstofffeld zurück. Nur ein geschlossener Kreislauf kennt keinen Endzustand
und kann prinzipiell unbegrenzt laufen.

Das System ist über **zwei streng getrennte Kanäle** an seine reale Umgebung
gekoppelt:

- **Klima** (langsam, Stunden): echtes Wetter über Open-Meteo → Licht,
  Nährstoffeintrag, Prozessgeschwindigkeit, Grundströmung
- **Ereignis** (schnell, Sekunden): Musik im Raum, nur als Pegel in zwei
  Frequenzbändern → Strömungsimpuls, Nährstoffpartikel

Darüber eine Erzählschicht: Ein lokal laufendes Sprachmodell führt aus dem
Simulationszustand ein Logbuch der Welt.

**Der wissenschaftliche Beitrag liegt nicht in der Simulationsmathematik.** Der
Kern verwendet ausschließlich etablierte Operatoren — Laplace-Diffusion,
semi-lagrangesche Advektion, schwellwertbasierte Wachstumsregeln, gaußsches
Mutationsrauschen. Der Beitrag liegt im **Mapping-Design** und in der
Evaluation: sechs Eingangsgrößen, jede mit genau einem Angriffspunkt, zwei
Zeitkonstanten mit drei Größenordnungen Abstand. Siehe
[`docs/mapping.md`](docs/mapping.md).

---

## 2. Architektur

Zwei Prozesse, ein Vertrag dazwischen.

```
   ┌──────────────────────┐         WebSocket        ┌──────────────────────┐
   │  sim/                │◄────────────────────────►│  core/               │
   │  TypeScript + WebGL2 │  Metriken    ──►         │  Python 3.13         │
   │                      │  env, pulse  ◄──         │  FastAPI             │
   │  GLSL-Shader         │                          │                      │
   │  Ping-Pong-FBOs      │  GET /config ──►         │  Umweltdienst        │
   │                      │                          │  Audiodienst         │
   │  rechnet & rendert,  │                          │  Metrik (SQLite)     │
   │  sonst nichts        │                          │  Regeldetektor       │
   └──────────────────────┘                          │  Chronikpipeline     │
                                                     └──────────┬───────────┘
                                       Open-Meteo ──────────────┤
                                       LM Studio (lokal) ───────┘
```

Der Vertrag ist in [`docs/contract.md`](docs/contract.md) spezifiziert und wird
beidseitig eingehalten. Er wird geändert, bevor Code geändert wird.

**Zwei Regeln, die die Architektur tragen:**

1. **Das Mapping liegt in `core`, nicht im Shader.** Die Abbildung Wetterwert →
   Simulationsgröße ist der Beitrag der Arbeit; sie muss testbar,
   dokumentierbar und aus der Konfiguration parametrierbar sein.
2. **Der Chronikpfad liest nur.** Es gibt keine Nachricht, mit der `core` Felder
   setzt, Masse korrigiert oder Organismen erzeugt — auch nicht „nur zum
   Ausgleichen".

---

## 3. Konfiguration

**Eine Datei:** [`config/params.yaml`](config/params.yaml). Jeder Parameter mit
sprechendem Namen und einer Kommentarzeile, die ihn begründet. Es gibt keinen
Zahlenwert im Shader oder im Detektor, der nicht von dort stammt — in der Arbeit
muss jeder Parameter dokumentiert und begründet werden, und das geht nur, wenn
er genau einen Ort hat.

`core` ist die Quelle der Wahrheit; `sim` holt die Parameter beim Start über
`GET /config`.

**Reproduzierbarkeit:** `run.seed` + `params.yaml` + Wetter-Rohlog
rekonstruieren einen Lauf vollständig. Wetterdaten werden **roh** mitgeloggt,
nicht nur interpoliert.

---

## 4. Prototyp 0 — die vertikale Scheibe

Bewusst schmal: ein dünner, aber vollständig durchgehender Pfad von der
Simulation bis zum ausgegebenen Chronikeintrag. Breite kommt danach.

### Drin

1. Nährstofffeld: Diffusion, Zerfall, Remineralisierung (GLSL, Ping-Pong-FBO)
2. Produzenten: Wachstum aus Licht und Nährstoff, Absterben → zurück ins
   Nährstofffeld. Geschlossener Kreislauf ab Tag eins.
3. Strömungsfeld: Curl-Noise, Grundrichtung aus dem Windwert
4. Massenbilanz als Laufzeitmetrik, jeden Tick gerechnet, per Readback bei
   niedriger Frequenz an `core`
5. Umweltdienst: Open-Meteo stündlich, Cache, Interpolation, Fallback bei
   Netzausfall
6. Audiodienst: Stub hinter dem endgültigen Interface, synthetische Pulse über
   Testendpunkt
7. Metriken → SQLite, mit Zeitstempel, Tick und Seed
8. Regeldetektor mit genau einer Regel: „Blüte"
9. Chronikpipeline: Ereignis → Chronicle-Backend → Eintrag → SQLite →
   `GET /chronicle` (siehe Abschnitt 6 für die beiden Implementierungen)
10. Minimale Anzeige der Chronik als Entwickler-Overlay
11. Zeitraffermodus, Faktor 1–100, **ab dem ersten Tag**
12. Seed-basierter RNG, vollständig deterministisch
13. Zustandssicherung: Snapshot alle N Minuten, beim Start wiederherstellen
14. Health-Log als JSON Lines

### Ausdrücklich draußen

- Konsumenten, Vererbung, Mutation → Prototyp 1
- Echte Audioerfassung (Stub genügt, Interface muss stimmen)
- **Die Interaktionsform.** Sprachinteraktion, Anwesenheitserkennung, beides —
  diese Entscheidung ist im Exposé §6.5 ausdrücklich offen und fällt erst am
  Ende von Monat 1. Sie wird auch nicht implizit durch die Architektur
  festgelegt.
- Rahmenbau, Kioskbetrieb, Zielhardware-Deployment
- Look-Development, Farbgebung, finale Darstellung

---

## 5. Phasen

Nach jeder Phase wird angehalten und auf Freigabe gewartet.

| Phase | Inhalt | Prüfbar an | Status |
|---|---|---|---|
| **0** | Gerüst und Vertrag. `PLAN.md`, `CLAUDE.md`, Ordnerstruktur, `config/params.yaml`, `docs/contract.md`, `docs/mapping.md`, `docs/expose.md`. Keine Logik. | Ein fremder Entwickler versteht aus `PLAN.md` und `docs/contract.md`, was gebaut wird und wie die beiden Prozesse reden. `scripts/verify_structure.py` läuft durch. | Abgeschlossen |
| **1** | Core ohne Framework. Umweltdienst, Metrikspeicher, Regeldetektor, `SingleChronicle`, WebSocket-Server. | Eingespeiste synthetische Metriken lösen genau dann eine „Blüte" aus, wenn sie sollen. Tests für Detektor und Massenbilanz grün. | Abgeschlossen |
| **2** | Simulation. GLSL-Kern, geschlossener Kreislauf, Klimakopplung, Pulsempfang, Zeitraffer, Snapshot/Restore. | 10.000 Ticks im Zeitraffer ohne Absturz, Massendrift unter 2 %. | Abgeschlossen — Massendrift siehe [`docs/annahmen.md`](docs/annahmen.md) A12 |
| **3** | Chronikpipeline, zweistufig. `TwoStepChronicle` (`chronicler` + `verifier`, zwei schlichte httpx-Aufrufe), Umschaltung gegen `SingleChronicle`. | Ein Chronikeintrag, dessen sämtliche Zahlen sich in der SQLite-Datenbank wiederfinden. Umschalten auf `single` ohne Codeänderung. | Abgeschlossen — **ohne CrewAI**, siehe Abschnitt 6 |
| **4** | Dauerbetrieb. Soak-Test, Health-Log, Watchdog, README. | Sechs simulierte Wochen im Zeitraffer in unter zwei Stunden, ohne Absturz, mit auswertbarem Health-Log. | Offen |

---

## 6. Chronikpipeline — zwei Implementierungen, kein Framework

> **Dieser Abschnitt hat den ursprünglichen Plan ersetzt, CrewAI für den
> zweistufigen Chronikweg einzusetzen.** Phase 3 wurde ohne CrewAI umgesetzt.
> Grund: Das Exposé nennt CrewAI an keiner Stelle und erwähnt „Agenten"
> genau zweimal — beide Male als Abgrenzung (§3.4 gegen Park et al. 2023,
> §5 „kein Multi-Agenten-Dialogsystem"). Ein Framework, das die Chronik über
> mehrere Agentenrollen orchestriert, stand also nie im Exposé, sondern war
> eine Entwurfsentscheidung dieses Plans — und sie war teurer als der
> Nutzen: eigenes Telemetrie- und Memory-Verhalten, das aktiv abgeschaltet
> werden musste (siehe die ursprüngliche Fassung dieses Abschnitts, unten in
> der Versionsgeschichte), gegen zwei Rollen, die sich mit zwei einfachen
> `httpx`-Aufrufen genauso umsetzen lassen. Die Zwei-Rollen-Idee —
> `chronicler` formuliert, `verifier` prüft — bleibt vollständig erhalten;
> nur das Framework fällt weg. Siehe
> `core/src/frame_core/chronicle/two_step.py` für die Begründung im Code.

Das Exposé grenzt sich in §5 ausdrücklich gegen Multi-Agenten-Simulationen ab
und legt in §6.4 fest: **Die Ereigniserkennung leistet ein Regeldetektor, nicht
das Sprachmodell.** Beides bleibt bindend, unabhängig vom Framework.

**Zwei Implementierungen hinter dem Interface `ChronicleBackend`**
(`core/src/frame_core/chronicle/base.py`), umschaltbar über
`chronicle.backend` in `config/params.yaml` (`Literal["single", "verified"]`),
ohne Codeänderung:

- **`SingleChronicle`** (`backend: "single"`) — ein einziger Modellaufruf mit
  striktem Prompt, ohne Framework. **Pflicht-Rückfallebene.**
- **`TwoStepChronicle`** (`backend: "verified"`) — zwei schlichte
  `httpx`-Aufrufe nacheinander, ohne Framework:
  - `chronicler` formuliert aus dem übergebenen Ereignis und den übergebenen
    Kennzahlen einen kurzen Logbucheintrag (wortgleicher Prompt zu
    `SingleChronicle`).
  - `verifier` prüft danach jede Aussage des Entwurfs gegen dieselben Zahlen
    und korrigiert oder verwirft, was nicht belegt ist.

**Warum die Rückfallebene Pflicht bleibt.** Zwei Rollen bedeuten zwei
Modellaufrufe pro Eintrag. Gemessen wurden 19–25 s je Aufruf auf der RX 7600
XT (siehe [`docs/annahmen.md`](docs/annahmen.md) A8); auf der Zielhardware mit
geteiltem Speicher entsprechend mehr. **Die Chronik ist im Exposé
Pflichtumfang, der zweistufige Weg nicht.** Das Projekt darf an dieser Stelle
nicht kippen.

**Guardrail vor Verifier.** Ob jede im Entwurf genannte Zahl in den
übergebenen Kennzahlen vorkommt, prüft eine reine Python-Funktion
(`chronicle/guard.py`, `guardrail_max_retries` in `config/params.yaml`) —
deterministisch und testbar, für beide Backends gleich. Der `verifier`-Schritt
in `TwoStepChronicle` beurteilt erst danach die inhaltlichen Aussagen. Nicht
umgekehrt: Was Python mechanisch prüfen kann, wird nicht einem Modell
überlassen.

**Weiterhin bindend, unabhängig vom Framework:**

| Regel | Grund |
|---|---|
| Kein LLM im Simulationstakt | Die Simulation läuft mit 30–60 Hz über Wochen. Ein Modellaufruf darin ist weder latenzverträglich noch reproduzierbar. |
| Kein LLM in der Ereigniserkennung | Der Detektor ist reines Python: Schwellenwerte auf Zeitreihen, deterministisch, testbar. Das Exposé steht und fällt damit, dass keine Ereignisse beschrieben werden, die nie stattfanden. |
| Keine Agenten als Bewohner der Welt | Kein Agent repräsentiert einen Organismus, keiner entscheidet im Ökosystem. Die Agenten stehen außerhalb und beschreiben. |
| Kein Schreibzugriff auf den Simulationszustand | Die Chronikpipeline liest, sie greift nicht ein — in keiner Richtung, auch nicht „nur zum Ausgleichen". |
| Keine Cloud-LLMs, kein Netzverkehr auf dem Chronikpfad | Das Modell läuft lokal über einen OpenAI-kompatiblen Endpunkt (`chronicle.base_url`, LM Studio). |
| Nichts CUDA-Abhängiges | Entwicklungshardware ist eine AMD RX 7600 XT. |

**Kein MCP auf dem Chronikpfad.** MCP gibt dem Modell Werkzeuge. Könnte der
Chronist die Metrikdatenbank selbst abfragen, hielte `metrics_ref` nicht mehr
fest, was er gesehen hat, und die Abnahmebedingung dieser Phase wäre
prinzipiell unprüfbar. Der Chronist bekommt ausschließlich die übergebenen
Zahlen (`DetectedEvent.all_numbers()`), keine Werkzeuge.

<details>
<summary>Ursprüngliche Fassung dieses Abschnitts, vor der Streichung von CrewAI</summary>

> Dies war die Stelle, an der das Projekt schiefgehen konnte. CrewAI war für
> genau einen Schreibschritt vorgesehen: ein **Flow** als deterministische
> Orchestrierung (`@start` / `@listen` / `@router`), darin eine **Crew** mit
> den Pflicht-Agenten `chronicler` und `verifier`, optional ein dritter
> `editor`. Pflicht-Rückfallebene war `SingleChronicle` gegen `CrewChronicle`,
> umschaltbar über `chronicle.backend` zwischen `single` und `crew`.
>
> Zwei über Context7 verifizierte Fallen wären zu beachten gewesen:
> Telemetrie ist bei CrewAI standardmäßig an (`CREWAI_DISABLE_TELEMETRY`,
> `OTEL_SDK_DISABLED` nötig), und `memory=True` ruft ohne eigenen Embedder die
> OpenAI-Cloud über `text-embedding-3-large`. Beides wäre Netzverkehr auf dem
> Chronikpfad gewesen und musste aktiv unterdrückt werden — genau die Art von
> Betriebslast, die der jetzige Weg mit zwei einfachen HTTP-Aufrufen gar
> nicht erst hat.

</details>

---

## 7. Definition of Done

- Zwei Kommandos starten das System (dokumentiert im README).
- Sechs simulierte Wochen laufen im Zeitraffer durch: kein Absturz, Massendrift
  unter 2 %, Biomasse konvergiert nicht auf einen Fixpunkt.
- Mindestens ein Chronikeintrag existiert, und jede darin genannte Zahl ist in
  der Metrik-Datenbank auffindbar.
- `chronicle.backend` lässt sich zwischen `verified` und `single` umschalten,
  beide funktionieren.
- **Reproduzierbar** sind Lauf, Ereignisse und Kennzahlen: Gleicher Seed,
  gleiche Config und gleicher Wetterlog erzeugen dieselben Ereignisse zu
  denselben Ticks. **Überprüfbar** — nicht reproduzierbar — ist der Chroniktext:
  Kein lokales LLM-Backend garantiert bitgleiche Ausgaben über Neuladungen.
  Belegt wird er über `metrics_ref` (siehe [`docs/annahmen.md`](docs/annahmen.md)
  A10).
- [`docs/annahmen.md`](docs/annahmen.md) listet jede getroffene Annahme.

**Noch ungeprüft, obwohl hier gefordert:**

- **Reproduzierbarkeit eines Laufs aus Seed, Config und Wetterlog** (Punkt
  oben, Exposé-Prämisse). Dass Simulation, Metrikzeitreihe und
  Detektorausgabe bei gleichem `run.seed`, gleicher `config/params.yaml` und
  gleichem `weather_raw.jsonl` tatsächlich dieselben Ereignisse zu denselben
  Ticks erzeugen, ist bisher nicht durch einen Vergleichslauf nachgewiesen —
  nur durch die Konstruktion (seed-basierter RNG, kein Zugriff auf Wanduhrzeit
  im Shader) plausibel gemacht. **Offen.**
- **Snapshot/Restore** (Prototyp 0, Punkt 13; Exposé §7.4). Dass ein Lauf nach
  einem Neustart aus dem letzten Snapshot in `data/snapshots` mit
  unverändertem Zustand — Felder, Massenbilanz-Akkumulatoren, `world_time` —
  weiterläuft, wurde bisher nicht durch einen tatsächlichen Neustart während
  eines laufenden Zeitrafferlaufs verifiziert. **Offen.**

---

## 8. Werkzeuge und Versionen

| | Version | Anmerkung |
|---|---|---|
| Python | **3.13**, projektlokal über `uv` | `requires-python = ">=3.13"`, ohne Obergrenze. Die frühere Obergrenze `<3.14` kam ausschließlich von CrewAI 1.x; seit Phase 3 läuft der zweistufige Chronikpfad über zwei einfache `httpx`-Aufrufe statt über CrewAI (Abschnitt 6), damit entfällt der Grund für die Obergrenze mit ihr. Das systemweit installierte Python 3.14 wird trotzdem nicht verwendet — projektlokal über `uv` bleibt Vorgabe, damit Entwicklungs- und Zielumgebung denselben Interpreter benutzen. |
| Node | 25.x | für `sim/` |
| GPU | AMD RX 7600 XT (Entwicklung) | kein CUDA, WebGL2 über OpenGL/Vulkan |
| LLM | LM Studio, `http://localhost:1234/v1` | lokal, OpenAI-kompatibel |
| Wetter | Open-Meteo | kein API-Schlüssel, CC BY 4.0 mit Attributionspflicht |
