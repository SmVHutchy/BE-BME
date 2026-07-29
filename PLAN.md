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
9. Chronikpipeline: Flow → Crew → Eintrag → SQLite → `GET /chronicle`
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

| Phase | Inhalt | Prüfbar an |
|---|---|---|
| **0** | Gerüst und Vertrag. `PLAN.md`, `CLAUDE.md`, Ordnerstruktur, `config/params.yaml`, `docs/contract.md`, `docs/mapping.md`, `docs/expose.md`. Keine Logik. | Ein fremder Entwickler versteht aus `PLAN.md` und `docs/contract.md`, was gebaut wird und wie die beiden Prozesse reden. `scripts/verify_structure.py` läuft durch. |
| **1** | Core ohne CrewAI. Umweltdienst, Metrikspeicher, Regeldetektor, `SingleChronicle`, WebSocket-Server. | Eingespeiste synthetische Metriken lösen genau dann eine „Blüte" aus, wenn sie sollen. Tests für Detektor und Massenbilanz grün. |
| **2** | Simulation. GLSL-Kern, geschlossener Kreislauf, Klimakopplung, Pulsempfang, Zeitraffer, Snapshot/Restore. | 10.000 Ticks im Zeitraffer ohne Absturz, Massendrift unter 2 %. |
| **3** | CrewAI. Flow und Crew, `CrewChronicle`, Umschaltung. | Ein Chronikeintrag, dessen sämtliche Zahlen sich in der SQLite-Datenbank wiederfinden. Umschalten auf `single` ohne Codeänderung. |
| **4** | Dauerbetrieb. Soak-Test, Health-Log, Watchdog, README. | Sechs simulierte Wochen im Zeitraffer in unter zwei Stunden, ohne Absturz, mit auswertbarem Health-Log. |

---

## 6. CrewAI — Umfang

Dies ist die Stelle, an der das Projekt schiefgehen kann.

Das Exposé grenzt sich in §5 ausdrücklich gegen Multi-Agenten-Simulationen ab
und legt in §6.4 fest: **Die Ereigniserkennung leistet ein Regeldetektor, nicht
das Sprachmodell.** Beides ist bindend. CrewAI wird deshalb an genau einer
Stelle eingesetzt und nirgends sonst.

**Erlaubt**

- Ein **Flow** als deterministische Orchestrierung der Chronikpipeline.
  `@start` / `@listen` / `@router` steuern die Reihenfolge; die Verzweigung
  „Ereignis erkannt → schreiben / kein Ereignis → nichts tun" gehört in den Flow.
- Eine **Crew** ausschließlich im Schreibschritt, mit genau zwei
  Pflicht-Agenten:
  - `chronicler` — formuliert aus dem übergebenen Ereignis und den übergebenen
    Kennzahlen einen kurzen Logbucheintrag.
  - `verifier` — prüft jede Aussage des Entwurfs gegen die übergebenen Zahlen
    und verwirft oder korrigiert alles, was nicht belegt ist.
  - Ein dritter `editor` für Register und Länge ist optional und standardmäßig
    aus.

**Verboten, jeweils mit Grund**

| Verbot | Grund |
|---|---|
| Kein LLM im Simulationstakt | Die Simulation läuft mit 30–60 Hz über Wochen. Ein Modellaufruf darin ist weder latenzverträglich noch reproduzierbar. |
| Kein LLM in der Ereigniserkennung | Der Detektor ist reines Python: Schwellenwerte auf Zeitreihen, deterministisch, testbar. Das Exposé steht und fällt damit, dass keine Ereignisse beschrieben werden, die nie stattfanden. |
| Keine Agenten als Bewohner der Welt | Kein Agent repräsentiert einen Organismus, keiner entscheidet im Ökosystem. Die Agenten stehen außerhalb und beschreiben. |
| Kein Schreibzugriff auf den Simulationszustand | Die Chronikpipeline liest, sie greift nicht ein — in keiner Richtung. |
| Keine Cloud-LLMs, kein Netzverkehr auf dem Chronikpfad | Das Modell läuft lokal über einen OpenAI-kompatiblen Endpunkt. |
| Nichts CUDA-Abhängiges | Entwicklungshardware ist eine AMD RX 7600 XT. |

**Pflicht-Rückfallebene.** Das Interface `ChronicleBackend` hat zwei
Implementierungen:

- `CrewChronicle` — der CrewAI-Weg oben
- `SingleChronicle` — ein einziger Modellaufruf mit striktem Prompt, ohne
  Framework

Umschaltbar über `chronicle.backend` in `config/params.yaml`, ohne
Codeänderung. Grund: Zwei Agenten bedeuten zwei Modellaufrufe pro Eintrag; auf
der späteren Zielhardware kann das zu langsam werden. **Die Chronik ist im
Exposé Pflichtumfang, CrewAI nicht.** Das Projekt darf an dieser Stelle nicht
kippen.

**Zwei Fallen, über Context7 verifiziert:**

- **Telemetrie ist standardmäßig an.** CrewAI sendet anonyme Nutzungsdaten über
  OpenTelemetry — Netzverkehr auf dem Chronikpfad. `CREWAI_DISABLE_TELEMETRY`
  und `OTEL_SDK_DISABLED` gehören gesetzt.
- **`memory=True` ruft die OpenAI-Cloud.** Ohne eigenen Embedder nutzt
  CrewAI-Memory `text-embedding-3-large`. Memory bleibt aus — es würde außerdem
  frühere Einträge einmischen und die Garantie brechen, dass ein Eintrag nur die
  übergebenen Zahlen enthält.

**Zwei Bausteine, die zur Aufgabe passen:** `guardrail` mit
`guardrail_max_retries` prüft die Ausgabe mit einer reinen Python-Funktion,
bevor sie angenommen wird — damit fängt Python mechanisch jede Zahl ab, die
nicht in den Kennzahlen vorkommt, und der `verifier` beurteilt nur noch die
inhaltlichen Aussagen. `output_pydantic` liefert typisierte statt geparster
Ausgabe.

**Kein MCP auf dem Chronikpfad.** MCP gibt dem Modell Werkzeuge. Könnte der
Chronist die Metrikdatenbank selbst abfragen, hielte `metrics_ref` nicht mehr
fest, was er gesehen hat, und die Abnahmebedingung dieser Phase wäre prinzipiell
unprüfbar. Der Endpunkt `/v1/chat/completions`, den CrewAI braucht, unterstützt
ohnehin keine MCPs — die Regel wird vom Transport erzwungen.

**Vor der ersten Zeile CrewAI-Code:** aktuelle API über Context7 holen
(`resolve-library-id` → `query-docs`). CrewAI ist in der 1.x-Linie unter
wöchentlicher Release-Kadenz; die Syntax wird nicht aus dem Gedächtnis
geschrieben.

---

## 7. Definition of Done

- Zwei Kommandos starten das System (dokumentiert im README).
- Sechs simulierte Wochen laufen im Zeitraffer durch: kein Absturz, Massendrift
  unter 2 %, Biomasse konvergiert nicht auf einen Fixpunkt.
- Mindestens ein Chronikeintrag existiert, und jede darin genannte Zahl ist in
  der Metrik-Datenbank auffindbar.
- `chronicle.backend` lässt sich zwischen `crew` und `single` umschalten, beide
  funktionieren.
- **Reproduzierbar** sind Lauf, Ereignisse und Kennzahlen: Gleicher Seed,
  gleiche Config und gleicher Wetterlog erzeugen dieselben Ereignisse zu
  denselben Ticks. **Überprüfbar** — nicht reproduzierbar — ist der Chroniktext:
  Kein lokales LLM-Backend garantiert bitgleiche Ausgaben über Neuladungen.
  Belegt wird er über `metrics_ref` (siehe [`docs/annahmen.md`](docs/annahmen.md)
  A10).
- [`docs/annahmen.md`](docs/annahmen.md) listet jede getroffene Annahme.

---

## 8. Werkzeuge und Versionen

| | Version | Anmerkung |
|---|---|---|
| Python | **3.13**, projektlokal über `uv` | CrewAI 1.15.8 verlangt `>=3.10,<3.14`. Das systemweit installierte Python 3.14 ist **nicht** verwendbar. |
| Node | 25.x | für `sim/` |
| GPU | AMD RX 7600 XT (Entwicklung) | kein CUDA, WebGL2 über OpenGL/Vulkan |
| LLM | LM Studio, `http://localhost:1234/v1` | lokal, OpenAI-kompatibel |
| Wetter | Open-Meteo | kein API-Schlüssel, CC BY 4.0 mit Attributionspflicht |
