# Vertrag zwischen `sim` und `core`

Dieses Dokument ist verbindlich. Beide Seiten halten es ein, und es wird
geaendert, bevor Code geaendert wird — nicht danach.

---

## 1. Die beiden Prozesse

| | `sim` | `core` |
|---|---|---|
| Technik | TypeScript, Vite, WebGL2 | Python 3.13, FastAPI |
| Aufgabe | rechnen und rendern | Umwelt, Metrik, Detektor, Chronik, Auslieferung |
| Rolle in der Verbindung | WebSocket-**Client** | WebSocket-**Server** |
| Laeuft als | Browser (spaeter Chromium im Kioskmodus) | lokaler Dienst |

`sim` weiss nichts vom Wetter, nichts von Open-Meteo, nichts von SQLite und
nichts von einem Sprachmodell. Es empfaengt fertig abgebildete, dimensionslose
Groessen und wendet sie an. `core` fasst keinen Simulationszustand an; es liest
Metriken und schreibt sie fort.

**Warum das Mapping in `core` liegt und nicht im Shader:** Die Abbildung
Wetterwert → Simulationsgroesse *ist* der wissenschaftliche Beitrag der Arbeit
(Exposé §4, §7.3). Sie muss testbar, dokumentierbar und aus `config/params.yaml`
parametrierbar sein. In GLSL waere sie keines davon.

---

## 2. Verbindung

- Endpunkt: `ws://{host}:{port}{ws_path}` aus `params.yaml → server` —
  Voreinstellung `ws://127.0.0.1:8000/ws`.
- `sim` verbindet beim Start und haelt die Verbindung.
- Alle Nachrichten sind JSON-Textrahmen, UTF-8.
- Es gibt **keinen Envelope und kein `type`-Feld**. Die Nachrichtenart wird am
  Vorhandensein eines Schluessels der obersten Ebene erkannt: `tick`, `env`,
  `pulse`, `health`. Empfaenger ignorieren unbekannte Schluessel schweigend,
  damit der Vertrag erweiterbar bleibt, ohne die Gegenseite zu brechen.

### Verbindungsverlust

`sim` verbindet mit exponentiellem Backoff neu (1 s, 2 s, 4 s … maximal 30 s).

**Die Simulation laeuft waehrenddessen weiter** und rechnet mit den zuletzt
empfangenen `env`-Werten. Das ist kein Notbehelf, sondern die geforderte
Betriebseigenschaft: Ein Ausfall des Klimakanals darf im Bild nicht sichtbar
werden (Exposé Risiko 8). Metriken, die waehrend der Trennung anfallen, werden
verworfen und nicht nachgesendet — eine Luecke in der Zeitreihe ist ehrlicher
als nachtraeglich eingefuegte Werte, und der Detektor arbeitet ohnehin
stichprobenbasiert.

Faellt `core` aus, faellt damit der Chronikpfad aus, nicht die Welt.

---

## 3. `sim → core`: Metriken

Alle 5 Sekunden Wanduhrzeit (`params.yaml → sim.readback_interval_s`).

> **Lesehilfe.** In diesem Dokument bezeichnen Schluessel wie `mass.total` immer
> **Felder der Nachricht**. Verweise auf die Konfiguration tragen durchgaengig
> den Dateinamen vorweg, etwa `params.yaml → mass.drift_tolerance_pct`. Die
> beiden Namensraeume ueberschneiden sich — es gibt ein `mass`-Objekt in der
> Nachricht *und* einen `mass`-Abschnitt in der Konfiguration —, deshalb die
> Unterscheidung.

```json
{ "t": "ISO8601", "tick": 12345,
  "mass": { "nutrient": 0.0, "producer": 0.0, "consumer": 0.0, "total": 0.0 },
  "lineages": 3, "gene_median": {}, "occupancy": 0.0 }
```

| Feld | Einheit / Bereich | Bemerkung |
|---|---|---|
| `t` | ISO-8601 mit Zeitzone | Wanduhrzeit der Messung |
| `tick` | Ganzzahl, monoton | zaehlt Simulationsschritte, nicht Bilder |
| `mass.nutrient` | ≥ 0, Feldsumme | geloester Naehrstoff |
| `mass.producer` | ≥ 0, Feldsumme | Produzentenbiomasse |
| `mass.consumer` | ≥ 0, Feldsumme | **in Prototyp 0 konstant `0.0`** — Konsumenten kommen erst in Prototyp 1. Das Feld bleibt im Vertrag, damit dieser stabil bleibt. |
| `mass.total` | ≥ 0 | Summe der drei; von `sim` gerechnet, von `core` nachgeprueft |
| `lineages` | Ganzzahl ≥ 0 | **in Prototyp 0 konstant `1`** — Vererbung kommt erst in Prototyp 1 |
| `gene_median` | Objekt | **in Prototyp 0 leer** `{}` |
| `occupancy` | 0..1 | Anteil der Zellen mit Biomasse ueber Schwelle |

Die Massenwerte sind Summen ueber das Feld, gewonnen durch progressives
Downsampling auf 1×1 und asynchronen Readback. Die Bilanz selbst wird **jeden
Tick** auf der GPU gerechnet; nur die Uebertragung geschieht in dieser
niedrigen Frequenz.

**Massenbilanz.** Geprueft wird nicht die Konstanz von `mass.total`, sondern der
Residualsaldo:

```
residual(t) = total(t) - total(0) - Σ Eintrag(0..t) + Σ Austrag(0..t)
```

Eintrag ist der Niederschlag, Austrag die Sedimentation (Exposé §6.2).

> **ANNAHME.** `sim` fuehrt beide Summen mit und sendet sie als
> `mass.inflow_total` und `mass.outflow_total` **zusaetzlich** zu den
> vorgegebenen Feldern. Das ist eine Erweiterung der urspruenglichen
> Vertragsvorgabe. Begruendung: Ohne die beiden Summen laesst sich der Saldo
> nicht bilden, und die Abnahmebedingung „Massendrift unter 2 %" waere nicht
> nachweisbar — man koennte nur die Konstanz der Gesamtmasse pruefen, und die
> ist bei offenem Eintrag und Austrag das falsche Kriterium.

Toleranz: `params.yaml → mass.drift_tolerance_pct`.

---

## 4. `core → sim`: Klimakanal

Bei Aenderung, typischerweise stuendlich, geglaettet ueber
`params.yaml → coupling` und dort `smoothing_minutes` der jeweiligen Kopplung.

```json
{ "env": { "light": 0.0, "nutrient_input": 0.0, "rate": 0.0,
           "wind": { "dir_deg": 0.0, "speed": 0.0 } } }
```

| Feld | Bereich | Angriffspunkt | Quelle |
|---|---|---|---|
| `light` | 0..1 dimensionslos | Lichtenergie *L*, Wachstum der Produzenten | `shortwave_radiation` |
| `nutrient_input` | 0..1 dimensionslos | Eintrag in das Naehrstofffeld | `precipitation` |
| `rate` | 0.4..1.8 Multiplikator | globale Prozessgeschwindigkeit | `temperature_2m` |
| `wind.dir_deg` | 0..360 Grad | Grundstroemung, Richtung | `wind_direction_10m` |
| `wind.speed` | 0..1 dimensionslos | Grundstroemung, Betrag | `wind_speed_10m` |

`wind.dir_deg` folgt der **meteorologischen Konvention**: die Richtung, *aus
der* der Wind weht (0° = Nord, 90° = Ost). So liefert Open-Meteo den Wert, und
so bleibt der Wetterlog ohne Umrechnung mit der Originalquelle vergleichbar.
Die Umrechnung in einen Stroemungsvektor geschieht in `sim`.

`rate` ist ein Multiplikator auf den Zeitschritt. Der wirksame Zeitschritt ist

```
dt_eff = dt_base * rate * speed
         ^^^^^^^   ^^^^   ^^^^^
         Config    diese  Config
                   Nachricht
```

Also `params.yaml → sim.dt_base` und `params.yaml → sim.speed` aus der
Konfiguration, `rate` aus dieser Nachricht.

`sim.speed` ist der Zeitraffer und **keine siebte Kopplung**, sondern eine
Betriebsgroesse (siehe [mapping.md](mapping.md)).

`sim` sendet keine Bestaetigung. Ein neuer `env`-Satz ersetzt den vorigen
vollstaendig; es gibt keine Teilaktualisierung.

---

## 5. `core → sim`: Ereigniskanal

Bei Audioereignis, Zeitkonstante Sekunden.

```json
{ "pulse": { "band": "low" | "high", "level": 0.0 } }
```

| Feld | Bereich | Angriffspunkt |
|---|---|---|
| `band: "low"` | — | Impuls in das Stroemungsfeld (lokale Wirbel) |
| `band: "high"` | — | punktuelle Naehrstoffpartikel |
| `level` | 0..1 normierter Pegel | Amplitude des jeweiligen Impulses |

Der Ort des Impulses wird in `sim` aus `run.seed` und `tick` bestimmt, nicht
uebertragen — damit bleibt der Lauf bei gleichem Puls-Protokoll reproduzierbar.

Aus dem Audiosignal treten ausschliesslich diese zwei Pegelwerte aus. Kein
Inhalt, keine Speicherung, kein Puffer ueber das FFT-Fenster hinaus
(Exposé §5, §7.5). In Prototyp 0 erzeugt ein Testendpunkt synthetische Pulse;
das Interface ist bereits das endgueltige.

---

## 6. `sim → core`: Health *(Betriebstelemetrie)*

> **ANNAHME.** Diese vierte Nachricht steht nicht in der urspruenglichen
> Vertragsvorgabe. Sie ist noetig, weil das Health-Log Bildzeit und Speicher
> verlangt (Prototyp 0, Punkt 14) und nur `sim` diese Werte kennt. Sie ist
> ausdruecklich **Betriebstelemetrie, kein Simulationszustand**: Kein Wert
> daraus fliesst in Metrikzeitreihe, Detektor oder Chronik. Die drei
> vorgegebenen Nachrichten bleiben unveraendert.

Alle `health.interval_s` Sekunden.

```json
{ "health": { "t": "ISO8601", "tick": 12345,
              "frame_ms": 0.0, "sim_hz": 0.0,
              "heap_mb": 0.0, "gl_context_lost": 0,
              "speed": 1.0 } }
```

`heap_mb` stammt aus `performance.memory` und ist nicht standardisiert; unter
Chromium vorhanden, sonst `null`. `speed` wird mitgesendet, damit im Health-Log
jederzeit ersichtlich ist, ob ein Abschnitt im Zeitraffer entstanden ist.

---

## 7. HTTP-Endpunkte von `core`

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/config` | `config/params.yaml` als JSON. `sim` holt die Parameter beim Start; die Konfiguration existiert dadurch wirklich nur einmal. Antwort enthaelt zusaetzlich `config_hash`. |
| `GET` | `/chronicle` | Chronikeintraege, neueste zuerst. Query: `limit`, `since`. |
| `GET` | `/health` | Aktueller Betriebszustand als JSON. |
| `POST` | `/debug/pulse` | Synthetischer Puls fuer den Audio-Stub. Body: `{"band": "low"\|"high", "level": 0.0}`. Entwicklungswerkzeug. |

`GET /chronicle` liefert je Eintrag:

```json
{ "id": 1, "t": "ISO8601", "tick": 12345, "event_type": "bloom",
  "text": "...", "metrics_ref": { "...": 0.0 }, "backend": "single" }
```

`metrics_ref` enthaelt genau die Zahlen, die dem Modell uebergeben wurden. Damit
ist jede Zahl im Eintrag gegen die Metrikdatenbank pruefbar — das ist die
Abnahmebedingung fuer Phase 3 und der Grund, warum das Feld existiert.

---

## 8. Was der Vertrag ausschliesst

- **Kein Rueckkanal in den Simulationszustand.** `core` kann `sim` nur ueber
  `env` und `pulse` beeinflussen — das sind die sechs Kopplungen und sonst
  nichts. Es gibt keine Nachricht, die Felder setzt, Masse korrigiert oder
  Organismen erzeugt. Die Chronikpipeline liest, sie greift nicht ein.
- **Kein Sprachmodell auf dieser Strecke.** Weder im Simulationstakt noch in der
  Ereigniserkennung. Der Detektor ist reines Python.
- **Keine siebte Kopplung.** Die vier `env`-Groessen und die zwei `pulse`-Baender
  entsprechen genau der Tabelle in Exposé §6.3.
- **Nichts zur Interaktionsform.** Der Vertrag enthaelt keine Nachricht fuer
  Sprache, Anwesenheit oder Aufmerksamkeitsstufen. Diese Entscheidung ist laut
  Exposé §6.5 offen und darf hier nicht implizit fallen.
