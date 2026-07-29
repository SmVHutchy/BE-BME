# `sim/src` — Aufbau

`sim` rechnet und rendert, sonst nichts. Es weiß nichts vom Wetter, nichts von
Open-Meteo, nichts von SQLite und nichts von einem Sprachmodell. Es empfängt
fertig abgebildete, dimensionslose Größen über den Vertrag
([`docs/contract.md`](../../docs/contract.md)) und wendet sie an.

Alle Parameter kommen beim Start über `GET /config` aus
[`config/params.yaml`](../../config/params.yaml). **Kein Zahlenwert im Shader,
der nicht von dort stammt** — in der Arbeit muss jeder Parameter begründet
werden.

| Verzeichnis | Zweck |
|---|---|
| `gl/` | WebGL2-Kontext, Programmverwaltung, Ping-Pong-FBOs. RGBA32F über `EXT_color_buffer_float`; float16 würde die Massensumme über 512² unbrauchbar machen. |
| `shaders/` | Die GLSL-Fragment-Shader: Nährstofffeld (Diffusion, Zerfall, Remineralisierung), Produzenten, Strömungsfeld (Curl-Noise), Advektion, Darstellung. Werden über Vites `?raw` als Text geladen. |
| `net/` | WebSocket-Client zu `core` und das Laden der Konfiguration. Reconnect mit Backoff; die Simulation läuft bei Verbindungsverlust mit den letzten bekannten `env`-Werten weiter. |
| `metrics/` | Massenreduktion per progressivem Downsampling auf 1×1 und asynchroner Readback über `fenceSync`. Die Bilanz wird **jeden Tick** gerechnet, nur die Übertragung geschieht alle 5 s — ein synchroner Readback würde die Pipeline im Dauerbetrieb blockieren. |
| `snapshot/` | Sicherung und Wiederherstellung des vollständigen Feldzustands. Kernanforderung, kein Komfortmerkmal: Bei einem System, dessen ganzer Sinn die Geschichte ist, darf ein Absturz keine Wochen Verlauf vernichten (Exposé §7.4). |
| `overlay/` | Entwickler-Overlay: Chronik, Massenbilanz, Bildzeit, Open-Meteo-Attribution. **Diagnosewerkzeug, keine Interaktionsform** — jene Entscheidung ist laut Exposé §6.5 offen. |

## Zwei Regeln für den Code hier

**Determinismus.** Zufall ausschließlich aus `run.seed` und `tick`. Nie aus
Wanduhrzeit, nie aus Frame-Zeit. Im Shader hash-basiertes Rauschen aus
`(seed, tick, Position)`. Sonst ist ein Lauf nicht aus Seed, Config und
Wetterlog rekonstruierbar.

**Takt ≠ Bildrate.** Der Simulationstakt (`sim.tick_hz`) ist von der Bildrate
entkoppelt; im Dauerbetrieb wird deutlich langsamer gerechnet als gezeichnet.
Wer beides koppelt, macht die Rückfallebene aus Risiko 3 unmöglich — Takt senken
statt Auflösung senken.

Der wirksame Zeitschritt ist

```
dt_eff = sim.dt_base * env.rate * sim.speed
```

`env.rate` ist die Temperaturkopplung, `sim.speed` der Zeitraffer und eine
Betriebsgröße — keine siebte Kopplung (siehe
[`docs/mapping.md`](../../docs/mapping.md)).
