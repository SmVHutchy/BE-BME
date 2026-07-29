# Ökosystem im Bilderrahmen

Ein künstliches Ökosystem, das in einem Bilderrahmen an der Wand in Echtzeit
läuft — über Monate, im häuslichen Dauerbetrieb. Gekoppelt an das echte Wetter
des Standorts (langsam, über Stunden) und an Musik im Raum (schnell, über
Sekunden). Ein lokal laufendes Sprachmodell führt aus dem Simulationszustand ein
Logbuch der Welt.

Bachelorarbeit Media Engineering, TH Nürnberg Georg Simon Ohm.

> **Stand: Phase 0.** Gerüst, Konfiguration und Verträge stehen; die Logik
> folgt in den Phasen 1–4. Die Startkommandos unten sind ab Phase 2 vollständig.

---

## Start

```bash
cd core && uv run uvicorn frame_core.api:app --port 8000
```

```bash
cd sim && npm run dev
```

Danach `http://localhost:5173` im Browser öffnen.

---

## Struktur prüfen

```bash
uv run --with pyyaml python scripts/verify_structure.py
```

Prüft, dass genau sechs Kopplungen mit sechs verschiedenen Angriffspunkten
existieren, dass alle in der Dokumentation genannten Parameter in
`config/params.yaml` vorhanden sind und dass die Interaktionsform nirgends —
auch nicht implizit — festgelegt wurde. Läuft ohne installierte Abhängigkeiten.

---

## Dokumentation

| Datei | Inhalt |
|---|---|
| [`PLAN.md`](PLAN.md) | Was gebaut wird, Architektur, Phasen, Definition of Done |
| [`docs/expose.md`](docs/expose.md) | Das Exposé — verbindliche Spezifikation |
| [`docs/contract.md`](docs/contract.md) | WebSocket-Vertrag zwischen `sim` und `core` |
| [`docs/mapping.md`](docs/mapping.md) | Die sechs Kopplungen und ihre Angriffspunkte |
| [`docs/annahmen.md`](docs/annahmen.md) | Jede getroffene Annahme mit Begründung |
| [`CLAUDE.md`](CLAUDE.md) | Arbeitsregeln für dieses Repository |
| [`config/params.yaml`](config/params.yaml) | Die einzige Konfigurationsdatei |

---

## Aufbau

```
core/   Python 3.13, FastAPI — Umweltdienst, Metrik, Detektor, Chronik
sim/    TypeScript, Vite, WebGL2 — Simulation als GLSL-Fragment-Shader
config/ params.yaml — jeder Parameter des Systems
docs/   Exposé, Verträge, Annahmen
data/   Laufzeitdaten (nicht versioniert)
```

---

## Voraussetzungen

- **Python 3.13** — projektlokal über [`uv`](https://docs.astral.sh/uv/);
  `uv sync` in `core/` holt den Interpreter mit. Python 3.14 funktioniert
  **nicht**, weil CrewAI `>=3.10,<3.14` verlangt.
- **Node 20+** für `sim/`.
- **GPU mit WebGL2** und `EXT_color_buffer_float`. Kein CUDA nötig und keines
  verwendet — entwickelt auf AMD RX 7600 XT.
- **[LM Studio](https://lmstudio.ai/)** mit einem geladenen Modell und
  gestartetem lokalem Server auf `http://localhost:1234/v1`. Modellname in
  `config/params.yaml` unter `chronicle.model`.

Ein Internetzugang wird ausschließlich für Open-Meteo gebraucht. Der
Chronikpfad läuft vollständig lokal.

---

## Datenschutz

Aus dem Audiosignal werden ausschließlich Pegel in zwei Frequenzbändern
gewonnen. Es findet keine Spracherkennung statt, es wird nichts gespeichert, und
es existiert kein Puffer über das FFT-Fenster hinaus. Kein Audiosignal verlässt
das Gerät. Der Ereigniskanal ist abschaltbar — das System läuft dann auf dem
Klimakanal weiter.

---

## Attribution

Wetterdaten von [Open-Meteo.com](https://open-meteo.com/), lizenziert unter
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## Lizenz

Noch nicht festgelegt.
