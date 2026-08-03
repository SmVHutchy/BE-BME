/**
 * Einstiegspunkt der Simulation.
 *
 * `sim` rechnet und rendert, sonst nichts. Jeder Parameter kommt beim Start
 * ueber GET /config von `core`; es gibt keinen Zahlenwert im Shader, der nicht
 * aus config/params.yaml stammt.
 *
 * DREI EIGENSCHAFTEN, die dieser Datei ihre Form geben:
 *
 * 1. Der Simulationstakt ist von der Bildrate entkoppelt. Gerechnet wird nach
 *    `tick_hz * speed`, gezeichnet nach requestAnimationFrame. Nur so laesst
 *    sich im Dauerbetrieb der Takt senken, ohne die Aufloesung anzutasten
 *    (Rueckfallebene Risiko 3).
 * 2. Der Zeitraffer vervielfacht die TAKTRATE, nicht den Zeitschritt. Ein
 *    Zeitrafferlauf durchlaeuft damit exakt dieselbe Tick-Folge wie ein
 *    Echtzeitlauf - sonst waere er als Pruefinstrument wertlos.
 * 3. Aller Zufall stammt aus `seed` und `tick`. Nie aus Wanduhrzeit, nie aus
 *    Frame-Zeit.
 */

import { createContext } from "./gl/context";
import { PingPong } from "./gl/pingpong";
import { Program, drawFullscreen } from "./gl/program";
import { MassReducer, type MassTotals } from "./metrics/reduce";
import { ContractClient, fetchConfig, type PulseValues } from "./net/client";
import { Overlay } from "./overlay/overlay";
import { assertStable, deriveRates } from "./sim/params";
import { loadLatestSnapshot, saveSnapshot } from "./snapshot/snapshot";

import commonSource from "./shaders/common.glsl?raw";
import advectSource from "./shaders/advect.frag?raw";
import displaySource from "./shaders/display.frag?raw";
import flowSource from "./shaders/flow.frag?raw";
import initSource from "./shaders/init.frag?raw";
import reactSource from "./shaders/react.frag?raw";
import reduceSource from "./shaders/reduce.frag?raw";

/**
 * Fuegt common.glsl hinter der #version-Zeile ein.
 *
 * `#version` muss die erste Zeile eines GLSL-Shaders sein, ein simples
 * Voranstellen scheitert also.
 */
function withCommon(source: string): string {
  const newline = source.indexOf("\n");
  return `${source.slice(0, newline + 1)}${commonSource}\n${source.slice(newline + 1)}`;
}

/** Ein abklingender Ereignispuls. */
interface ActivePulse {
  x: number;
  y: number;
  strength: number;
  decaySeconds: number;
  ageSeconds: number;
}

const CORE_HTTP = `http://${location.hostname}:8000`;
const CORE_WS = `ws://${location.hostname}:8000/ws`;

async function main(): Promise<void> {
  const { config, configHash } = await fetchConfig(CORE_HTTP);
  assertStable(config);
  const rates = deriveRates(config);

  const width = config.sim.grid.width;
  const height = config.sim.grid.height;
  const seed = config.run.seed >>> 0;

  const canvas = document.getElementById("sim-canvas") as HTMLCanvasElement;
  const { gl } = createContext(canvas);

  // --- Programme ----------------------------------------------------------
  const programs = {
    init: new Program(gl, withCommon(initSource), "init"),
    flow: new Program(gl, withCommon(flowSource), "flow"),
    advect: new Program(gl, withCommon(advectSource), "advect"),
    react: new Program(gl, withCommon(reactSource), "react"),
    reduce: new Program(gl, withCommon(reduceSource), "reduce"),
    display: new Program(gl, withCommon(displaySource), "display"),
  };

  // Linear filtern nur beim Zustand: Die Advektion sampelt zwischen Zellen.
  const state = new PingPong(gl, width, height, null, true);
  const velocity = new PingPong(gl, width, height, null, true);
  const reducer = new MassReducer(gl, programs.reduce, width, height);

  // --- Zustand ------------------------------------------------------------
  let tick = 0;
  let worldTime = 0;
  let initialTotal: number | null = null;
  // Ein- und Austrag zaehlen ab Tick 0, der erste Readback kommt aber erst
  // einige Ticks spaeter. Ohne diese beiden Bezugswerte enthielte der
  // Residualsaldo die Bewegungen vor der ersten Messung als scheinbare Drift.
  let initialInflow = 0;
  let initialOutflow = 0;
  let lastMass: MassTotals | null = null;
  let droppedTicks = 0;
  let glContextLost = 0;
  const pulses: { low: ActivePulse | null; high: ActivePulse | null } = { low: null, high: null };

  // --- Startzustand: Snapshot oder frisch ---------------------------------
  const snapshot = await loadLatestSnapshot(seed, configHash, width, height);
  if (snapshot) {
    state.upload(new Float32Array(snapshot.state));
    tick = snapshot.tick;
    worldTime = snapshot.worldTime;
    console.info(
      `Snapshot wiederhergestellt: Tick ${tick.toLocaleString("de-DE")}, ` +
        `Weltzeit ${(worldTime / 86400).toFixed(1)} Tage, gesichert ${snapshot.savedAt}`,
    );
  } else {
    state.bindWrite();
    programs.init.use();
    programs.init.setVec2("uResolution", width, height);
    programs.init.setInt("uSeed", seed);
    programs.init.setFloat("uNutrientLevel", config.init.nutrient_level);
    programs.init.setFloat("uProducerLevel", config.init.producer_level);
    programs.init.setFloat("uPatchScale", config.init.producer_patch_scale);
    programs.init.setFloat("uPatchThreshold", config.init.producer_patch_threshold);
    drawFullscreen(gl);
    state.swap();
    console.info(`Frischer Start mit Seed ${seed}`);
  }

  // --- Vertrag ------------------------------------------------------------
  const client = new ContractClient(CORE_WS);
  client.onPulse = (pulse: PulseValues) => {
    // Der Ort stammt aus Seed und Tick, nicht aus der Nachricht - so bleibt der
    // Lauf bei gleichem Puls-Protokoll reproduzierbar (docs/contract.md).
    const hash = (seed * 2654435761 + tick * 40503) >>> 0;
    const x = (hash % width) + 0.5;
    const y = ((hash >>> 16) % height) + 0.5;
    const coupling = pulse.band === "low" ? config.coupling.pulse_low : config.coupling.pulse_high;
    pulses[pulse.band] = {
      x,
      y,
      strength: pulse.level * coupling.gain,
      decaySeconds: coupling.decay_seconds,
      ageSeconds: 0,
    };
  };
  client.connect();

  const overlayElement = document.getElementById("dev-overlay") as HTMLElement;
  const overlay = new Overlay(overlayElement);

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    glContextLost += 1;
    console.error("WebGL-Kontext verloren. Neustart erforderlich.");
  });

  // --- Ein Simulationsschritt --------------------------------------------
  function step(dtWorld: number, dtWall: number): void {
    const env = client.env;
    const light = env?.light ?? 0;
    const nutrientInput = env?.nutrient_input ?? 0;
    const windDir = env?.wind.dir_deg ?? 0;
    const windSpeed = env?.wind.speed ?? 0;

    // Pulse altern in WANDUHRZEIT, nicht in Weltzeit: Der Ereigniskanal hat
    // seine Zeitkonstante in echten Sekunden - er reagiert auf Musik im Raum,
    // und die schert sich nicht um den Zeitraffer.
    for (const band of ["low", "high"] as const) {
      const pulse = pulses[band];
      if (!pulse) continue;
      pulse.ageSeconds += dtWall;
      if (pulse.ageSeconds >= pulse.decaySeconds) pulses[band] = null;
    }
    const low = pulses.low;
    const high = pulses.high;
    const lowStrength = low ? low.strength * (1 - low.ageSeconds / low.decaySeconds) : 0;
    const highStrength = high ? high.strength * (1 - high.ageSeconds / high.decaySeconds) : 0;

    // 1. Stroemungsfeld
    velocity.bindWrite();
    programs.flow.use();
    programs.flow.setVec2("uResolution", width, height);
    programs.flow.setInt("uSeed", seed);
    programs.flow.setInt("uTick", tick);
    programs.flow.setFloat("uWorldTime", worldTime);
    programs.flow.setFloat("uCurlScale", config.flow.curl_noise_scale);
    programs.flow.setFloat("uCurlStrength", config.flow.curl_noise_strength);
    programs.flow.setFloat("uBaseCurrentGain", config.flow.base_current_gain);
    programs.flow.setFloat("uWindDirDeg", windDir);
    programs.flow.setFloat("uWindSpeed", windSpeed);
    programs.flow.setVec2("uPulsePos", low?.x ?? 0, low?.y ?? 0);
    programs.flow.setFloat("uPulseStrength", lowStrength);
    programs.flow.setFloat("uPulseRadius", config.coupling.pulse_low.radius_cells);
    drawFullscreen(gl);
    velocity.swap();

    // 2. Advektion
    state.bindWrite();
    programs.advect.use();
    programs.advect.setTexture("uState", state.read, 0);
    programs.advect.setTexture("uVelocity", velocity.read, 1);
    programs.advect.setVec2("uResolution", width, height);
    programs.advect.setFloat("uDt", dtWorld);
    programs.advect.setFloat("uDissipation", config.flow.advection_dissipation);
    drawFullscreen(gl);
    state.swap();

    // 3. Reaktion
    state.bindWrite();
    programs.react.use();
    programs.react.setTexture("uState", state.read, 0);
    programs.react.setVec2("uResolution", width, height);
    programs.react.setFloat("uDt", dtWorld);
    programs.react.setInt("uSeed", seed);
    programs.react.setInt("uTick", tick);
    programs.react.setFloat("uDiffusion", config.field.nutrient.diffusion_coefficient);
    programs.react.setFloat("uRemineralization", config.field.nutrient.remineralization_rate);
    programs.react.setFloat("uRefugeFloor", config.field.nutrient.refuge_floor);
    programs.react.setFloat("uInputRate", rates.inputRate);
    programs.react.setFloat("uGrowthRate", rates.growthRate);
    programs.react.setFloat("uLightHalf", config.field.producer.light_half_saturation);
    programs.react.setFloat("uNutrientHalf", config.field.producer.nutrient_half_saturation);
    programs.react.setFloat("uDeathRate", rates.deathRate);
    programs.react.setFloat("uMaxDensity", config.field.producer.max_density);
    programs.react.setFloat("uSedimentationRate", rates.sedimentationRate);
    programs.react.setInt("uSedimentInterval", config.mass.sedimentation_interval_ticks);
    programs.react.setFloat("uLight", light);
    programs.react.setFloat("uNutrientInput", nutrientInput);
    programs.react.setVec2("uParticlePos", high?.x ?? 0, high?.y ?? 0);
    programs.react.setFloat("uParticleAmount", highStrength * config.coupling.pulse_high.amount);
    programs.react.setFloat("uParticleRadius", config.coupling.pulse_high.radius_cells);
    drawFullscreen(gl);
    state.swap();

    // 4. Massenbilanz - jeden Tick, auf der GPU.
    reducer.reduce(state.read, width);

    tick += 1;
    worldTime += dtWorld;
  }

  // --- Zwei getrennte Schleifen -------------------------------------------
  //
  // Der Simulationstakt haengt an einem Zeitgeber, das Zeichnen an
  // requestAnimationFrame. Diese Trennung ist keine Feinheit, sondern die in
  // CLAUDE.md geforderte Entkopplung - und sie hat einen handfesten Grund:
  // requestAnimationFrame wird vom Browser vollstaendig angehalten, sobald das
  // Fenster nicht sichtbar ist. Laege der Takt darin, bliebe die Welt jedes Mal
  // stehen, wenn im Kioskbetrieb der Bildschirm dunkel wird - bei einem System,
  // dessen ganzer Sinn die ueber Wochen fortlaufende Geschichte ist, waere das
  // ein stiller Totalausfall.
  let lastStep = performance.now();
  let lastRender = performance.now();
  let tickAccumulator = 0;
  let sinceReadback = 0;
  /** Weltzeit der letzten Stichprobe - deckelt den Abstand im Zeitraffer. */
  let lastSampleWorldTime = 0;
  let sinceHealth = 0;
  let sinceSnapshot = 0;
  let frameMs = 0;
  let ticksThisSecond = 0;
  let sinceHzSample = 0;
  let measuredHz = 0;
  let chronicle: { t: string; text: string }[] = [];

  /**
   * Alles, was NACH den Ticks passiert: Readback, Metriken, Health, Snapshot.
   *
   * Bewusst herausgezogen, damit der Zeitgeber und `runTicks` durch **dieselben
   * Stellen** laufen. Vorher meldete `runTicks` gar nichts - `core` erfuhr die
   * Weltzeit nie, das Wetter stand still, Detektor und Chronik liefen nicht mit
   * und das Health-Log blieb leer. Ein Zeitraffer, der an der halben Anlage
   * vorbeilaeuft, misst nicht den Feldbetrieb (docs/annahmen.md A11).
   *
   * `elapsedWall` ist die verstrichene Wanduhrzeit seit dem letzten Aufruf; im
   * Burst die anteilig gerechnete.
   */
  function reportAndPersist(elapsedWall: number): void {
    sinceReadback += elapsedWall;
    // Zwei Ausloeser, und der zweite ist der Grund, warum ueberhaupt einer
    // reicht: Die Wanduhrbedingung allein laesst die Abtastdichte mit dem
    // Zeitraffer zusammenbrechen. Bei speed = 500 kamen so nur 158 Messpunkte
    // je Siebentagelauf zustande - zu wenige fuer den Detektor (A14).
    //
    // Im Feldbetrieb greift immer die erste Bedingung zuerst (5 Weltsekunden
    // gegen 300), dort aendert der Deckel also nichts.
    const worldSinceSample = worldTime - lastSampleWorldTime;
    if (sinceReadback >= config.sim.readback_interval_s
        || worldSinceSample >= config.sim.max_world_seconds_per_sample) {
      sinceReadback = 0;
      lastSampleWorldTime = worldTime;
      reducer.requestReadback();
    }
    const totals = reducer.poll();
    if (totals) {
      lastMass = totals;
      captureBaseline(totals);
      client.send({
        t: new Date().toISOString(),
        tick,
        world_time: worldTime,
        mass: {
          nutrient: totals.nutrient,
          producer: totals.producer,
          consumer: 0,
          total: totals.total,
          inflow_total: totals.inflow,
          outflow_total: totals.outflow,
        },
        lineages: 1,
        gene_median: {},
        occupancy: Math.min(1, totals.producer / (width * height * config.field.producer.max_density)),
      });
    }

    // --- Takt messen ------------------------------------------------------
    sinceHzSample += elapsedWall;
    if (sinceHzSample >= 1) {
      measuredHz = ticksThisSecond / sinceHzSample;
      ticksThisSecond = 0;
      sinceHzSample = 0;
    }

    // --- Health -----------------------------------------------------------
    sinceHealth += elapsedWall;
    if (sinceHealth >= config.health.interval_s) {
      sinceHealth = 0;
      const memory = (performance as { memory?: { usedJSHeapSize: number } }).memory;
      client.send({
        health: {
          t: new Date().toISOString(),
          tick,
          frame_ms: frameMs,
          sim_hz: measuredHz,
          heap_mb: memory ? memory.usedJSHeapSize / 1048576 : null,
          gl_context_lost: glContextLost,
          speed: config.sim.speed,
        },
      });
      void fetch(`${CORE_HTTP}/chronicle?limit=2`)
        .then((response) => response.json())
        .then((payload: { entries: { t: string; text: string }[] }) => {
          chronicle = payload.entries;
        })
        .catch(() => undefined);
    }

    // --- Snapshot ---------------------------------------------------------
    sinceSnapshot += elapsedWall;
    if (sinceSnapshot >= config.snapshot.interval_minutes * 60) {
      sinceSnapshot = 0;
      void saveSnapshot(
        {
          tick,
          worldTime,
          seed,
          configHash,
          savedAt: new Date().toISOString(),
          width,
          height,
          state: state.readAll(),
        },
        config.snapshot.keep_last,
      ).catch((error: unknown) => console.warn("Snapshot fehlgeschlagen:", error));
    }
  }

  /**
   * Rechnet `count` Ticks am Stueck und meldet dabei im Normalintervall.
   *
   * Fuer Zeitrafferlaeufe und die Abnahme. Die Tick-Folge ist dieselbe wie im
   * Normalbetrieb, und gemeldet wird ueber `reportAndPersist` - also durch
   * dieselben Stellen. Ohne das liefe der Burst an Wetter, Detektor, Chronik
   * und Health-Log vorbei und waere kein Abbild des Feldbetriebs.
   */
  function runTicks(count: number): { ticks: number; ms: number } {
    const started = performance.now();
    // Ticks je Meldung - das Minimum aus zwei Bedingungen:
    //   nach Wanduhrzeit  wie im Normalbetrieb
    //   nach WELTZEIT     damit die Abtastdichte nicht mit dem Zeitraffer
    //                     zusammenbricht. Ohne diesen Deckel lagen bei
    //                     speed = 500 ganze 2500 Weltsekunden zwischen zwei
    //                     Punkten, und ein Lauf ueber sieben Welttage lieferte
    //                     nur 79 - zu wenige fuer den Detektor (A14).
    const perReportWall = config.sim.readback_interval_s * config.sim.tick_hz * config.sim.speed;
    const perReportWorld = config.sim.max_world_seconds_per_sample / config.sim.dt_base;
    const perReport = Math.max(1, Math.round(Math.min(perReportWall, perReportWorld)));

    let done = 0;
    while (done < count) {
      const chunk = Math.min(perReport, count - done);
      // rate JE ABSCHNITT neu lesen, nicht einmal fuer den ganzen Burst -
      // sonst friert die Temperaturkopplung auf dem Startwert ein.
      const dtWorld = config.sim.dt_base * (client.env?.rate ?? 1);
      for (let i = 0; i < chunk; i++) step(dtWorld, 1 / config.sim.tick_hz);
      done += chunk;
      ticksThisSecond += chunk;
      // Die Wanduhrzeit, die diese Ticks im Normalbetrieb gedauert haetten.
      // Nicht pauschal readback_interval_s: Sobald der Weltzeitdeckel greift,
      // sind die Abschnitte kuerzer, und Health- und Snapshot-Takt wuerden
      // sonst vorlaufen.
      reportAndPersist(chunk / (config.sim.tick_hz * config.sim.speed));
    }
    return { ticks: count, ms: performance.now() - started };
  }

  /** Der Zeitgeber: rechnet die faelligen Ticks und meldet danach. */
  function simulationStep(): void {
    const now = performance.now();
    const dtWall = Math.min((now - lastStep) / 1000, 1.0);
    lastStep = now;

    const dtWorld = config.sim.dt_base * (client.env?.rate ?? 1);
    const ticksPerSecond = config.sim.tick_hz * config.sim.speed;

    tickAccumulator += dtWall * ticksPerSecond;
    // Sicherheitsventil: Nie mehr als eine Sekunde Rueckstand aufholen. Was
    // darueber hinausgeht, wird verworfen und gezaehlt - dann haelt die GPU den
    // gewuenschten Takt nicht, und genau das soll im Health-Log sichtbar werden
    // (Rueckfallebene Risiko 3: Takt senken statt Aufloesung senken).
    if (tickAccumulator > ticksPerSecond) {
      droppedTicks += Math.floor(tickAccumulator - ticksPerSecond);
      tickAccumulator = ticksPerSecond;
    }

    const ticksNow = Math.floor(tickAccumulator);
    tickAccumulator -= ticksNow;
    for (let i = 0; i < ticksNow; i++) step(dtWorld, dtWall / Math.max(ticksNow, 1));
    ticksThisSecond += ticksNow;

    reportAndPersist(dtWall);

  }

  function renderFrame(): void {
    const now = performance.now();
    lastRender = now;

    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    programs.display.use();
    programs.display.setTexture("uState", state.read, 0);
    programs.display.setVec2("uResolution", canvas.width, canvas.height);
    programs.display.setFloat("uMaxDensity", config.field.producer.max_density);
    drawFullscreen(gl);

    frameMs = performance.now() - now;

    overlay.render({
      tick,
      worldTime,
      speed: config.sim.speed,
      frameMs,
      simHz: measuredHz,
      connected: client.connected,
      env: client.env,
      mass: lastMass,
      initialTotal,
      driftPct: driftPercent(),
      driftTolerancePct: config.mass.drift_tolerance_pct,
      droppedTicks,
      chronicle,
    });

    requestAnimationFrame(renderFrame);
  }

  /**
   * Residualsaldo in Prozent der Startmasse.
   *
   *   residual = total(t) - total(0) - Eintrag(0..t) + Austrag(0..t)
   *
   * Geprueft wird NICHT die Konstanz der Gesamtmasse: Niederschlag traegt ein,
   * Sedimentation traegt aus, die Summe soll sich also aendern (ExposÃ© 6.2).
   * Was nicht passieren darf, ist unerklaerte Masse.
   */
  function driftPercent(): number | null {
    if (!lastMass || !initialTotal) return null;
    const inflow = lastMass.inflow - initialInflow;
    const outflow = lastMass.outflow - initialOutflow;
    return ((lastMass.total - initialTotal - inflow + outflow) / initialTotal) * 100;
  }

  /** Setzt die Bezugsgroessen der Bilanz beim ersten Messwert. */
  function captureBaseline(totals: MassTotals): void {
    if (initialTotal !== null) return;
    initialTotal = totals.total;
    initialInflow = totals.inflow;
    initialOutflow = totals.outflow;
  }

  /**
   * Soak-Modus: `?soak=<Welttage>`.
   *
   * Faehrt den Lauf in Abschnitten und gibt zwischen ihnen an den Ereignisleser
   * zurueck, damit der WebSocket senden kann und `core` neue Klimawerte
   * zurueckschickt. Ohne dieses Nachgeben liefe der ganze Lauf in einem
   * blockierenden Rutsch und das Wetter stuende wieder still.
   *
   * Diagnosewerkzeug wie das Entwickler-Overlay - keine Interaktionsform. Der
   * Lauf meldet ueber den normalen Vertrag, damit gemessen wird, was auch im
   * Feldbetrieb passiert.
   */
  async function runSoak(worldDays: number): Promise<void> {
    // Auf den ersten Klimasatz warten. Ohne ihn startete der Lauf mit
    // Licht 0 - also genau der Dauernacht, wegen der A11 aufgefallen ist.
    for (let i = 0; i < 60 && client.env === null; i++) {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    if (client.env === null) {
      console.error("Soak: keine Klimawerte von core - Lauf waere nicht aussagekraeftig.");
      return;
    }

    const target = worldTime + worldDays * 86400;
    const batch = Math.max(
      1,
      Math.round(config.sim.readback_interval_s * config.sim.tick_hz * config.sim.speed),
    );
    const started = performance.now();
    let lastLog = started;

    console.info(
      `Soak: ${worldDays} Welttage bei speed=${config.sim.speed}, ` +
        `${batch} Ticks je Abschnitt. Start bei Weltzeit ${(worldTime / 86400).toFixed(2)} d.`,
    );

    while (worldTime < target) {
      runTicks(batch);
      // Nachgeben: WebSocket senden lassen, env empfangen, Chronik laufen lassen.
      await new Promise((resolve) => setTimeout(resolve, 0));

      const now = performance.now();
      if (now - lastLog > 10000) {
        lastLog = now;
        const fortschritt = ((worldTime - (target - worldDays * 86400)) / (worldDays * 86400)) * 100;
        console.info(
          `Soak: ${fortschritt.toFixed(1)} %  Welttag ${(worldTime / 86400).toFixed(2)}  ` +
            `Biomasse ${lastMass?.producer.toFixed(0) ?? "?"}  ` +
            `Residuum ${driftPercent()?.toFixed(3) ?? "?"} %  ` +
            `Licht ${client.env?.light.toFixed(3) ?? "?"}`,
        );
      }
    }

    const dauer = (performance.now() - started) / 1000;
    console.info(
      `Soak fertig: ${worldDays} Welttage in ${dauer.toFixed(0)} s Wanduhrzeit, ` +
        `Tick ${tick}, Biomasse ${lastMass?.producer.toFixed(0) ?? "?"}, ` +
        `Residuum ${driftPercent()?.toFixed(3) ?? "?"} %. ` +
        `Auswertung: uv run --project core python scripts/soak_report.py`,
    );
    (window as unknown as { soakDone: boolean }).soakDone = true;
  }

  // Der Zeitgeber feuert mit tick_hz; je Aufruf werden die faelligen Ticks
  // abgearbeitet. Bei speed = 100 sind das 100 Ticks je Aufruf.
  const soakDays = Number(new URLSearchParams(location.search).get("soak"));
  if (soakDays > 0) {
    // Im Soak-Modus kein Zeitgeber: Der Lauf treibt sich selbst, sonst wuerden
    // beide gleichzeitig Ticks rechnen.
    void runSoak(soakDays);
  } else {
    window.setInterval(simulationStep, 1000 / config.sim.tick_hz);
  }
  requestAnimationFrame(renderFrame);

  // --- Diagnosegriffe -----------------------------------------------------
  // Fuer Zeitrafferlaeufe und Soak-Tests von aussen erreichbar. Kein Bestandteil
  // des Vertrags und keine Interaktionsform, sondern Werkzeug - wie das
  // Entwickler-Overlay.
  (window as unknown as { frameSim: unknown }).frameSim = {
    state: () => ({
      tick,
      worldTime,
      mass: lastMass,
      initialTotal,
      droppedTicks,
      driftPct: driftPercent(),
      lastRenderAgoMs: performance.now() - lastRender,
    }),
    config: () => config,
    /**
     * Rechnet `count` Ticks am Stueck, ohne auf den Zeitgeber zu warten.
     *
     * Fuer die Abnahme "10.000 Ticks im Zeitraffer" und fuer Soak-Laeufe. Die
     * Tick-Folge ist dieselbe wie im normalen Betrieb - deshalb ist das
     * Ergebnis aussagekraeftig und kein Sonderweg.
     */
    runTicks,
    /** Wartet auf den naechsten Readback und liefert die Summen. */
    readMass: () =>
      new Promise((resolve) => {
        reducer.requestReadback();
        const attempt = (): void => {
          const totals = reducer.poll();
          if (totals) {
            lastMass = totals;
            captureBaseline(totals);
            resolve({ ...totals, driftPct: driftPercent() });
          } else {
            setTimeout(attempt, 16);
          }
        };
        attempt();
      }),
  };
}

main().catch((error: unknown) => {
  console.error(error);
  document.body.insertAdjacentHTML(
    "beforeend",
    `<pre style="position:fixed;inset:0;margin:0;padding:2rem;background:#200;color:#fbb;
      font:13px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow:auto">${
        error instanceof Error ? `${error.message}\n\n${error.stack ?? ""}` : String(error)
      }</pre>`,
  );
});
