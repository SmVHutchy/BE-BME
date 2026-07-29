/**
 * Entwickler-Overlay.
 *
 * AUSDRUECKLICH EIN DIAGNOSEWERKZEUG UND KEINE INTERAKTIONSFORM. Die Form, in
 * der Bewohner mit dem Objekt in Kontakt treten, ist laut Exposé 6.5 offen und
 * faellt erst am Ende von Monat 1. Dieses Overlay ist fuer die Entwicklung da,
 * wird im Feldbetrieb abgeschaltet und praejudiziert nichts: Es reagiert auf
 * keine Anwesenheit, hoert nichts und beantwortet keine Fragen.
 *
 * Die Open-Meteo-Attribution steht hier fest verdrahtet. Sie ist nach CC BY 4.0
 * Pflicht und gehoert an zwei Stellen - README und Objekt (Exposé 3.5). Beim
 * Umbau der Anzeige darf sie nicht verschwinden.
 */

export interface OverlayState {
  tick: number;
  worldTime: number;
  speed: number;
  frameMs: number;
  simHz: number;
  connected: boolean;
  env: { light: number; nutrient_input: number; rate: number; wind: { dir_deg: number; speed: number } } | null;
  mass: { nutrient: number; producer: number; total: number; inflow: number; outflow: number } | null;
  initialTotal: number | null;
  driftPct: number | null;
  driftTolerancePct: number;
  droppedTicks: number;
  chronicle: { t: string; text: string }[];
}

function formatWorldTime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${days} d ${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export class Overlay {
  private readonly element: HTMLElement;

  constructor(container: HTMLElement) {
    this.element = container;
    this.element.hidden = false;
    Object.assign(this.element.style, {
      position: "fixed",
      top: "0",
      left: "0",
      padding: "10px 14px",
      font: "12px/1.5 ui-monospace, SFMono-Regular, Consolas, monospace",
      color: "#cfe8d4",
      background: "rgba(0,0,0,0.62)",
      whiteSpace: "pre",
      pointerEvents: "none",
      maxWidth: "min(46ch, 90vw)",
    } satisfies Partial<CSSStyleDeclaration>);
  }

  render(state: OverlayState): void {
    const env = state.env;
    const mass = state.mass;

    const lines = [
      `Tick    ${state.tick.toLocaleString("de-DE")}   Weltzeit ${formatWorldTime(state.worldTime)}`,
      `Takt    ${state.simHz.toFixed(0)} Hz   Zeitraffer ${state.speed}x   Bild ${state.frameMs.toFixed(1)} ms`,
      state.droppedTicks > 0
        ? `        ${state.droppedTicks.toLocaleString("de-DE")} Ticks verworfen (GPU haelt den Takt nicht)`
        : "",
      "",
      `Vertrag ${state.connected ? "verbunden" : "getrennt - letzte env-Werte gelten weiter"}`,
    ];

    if (env) {
      lines.push(
        `  Licht        ${env.light.toFixed(3)}      Naehrstoff ${env.nutrient_input.toFixed(3)}`,
        `  Rate         ${env.rate.toFixed(3)}      Wind ${env.wind.dir_deg.toFixed(0)}deg / ${env.wind.speed.toFixed(2)}`,
      );
    } else {
      lines.push("  (noch keine Klimawerte)");
    }

    lines.push("");
    if (mass) {
      lines.push(
        `Masse   Naehrstoff ${mass.nutrient.toFixed(1)}  Biomasse ${mass.producer.toFixed(1)}`,
        `        gesamt ${mass.total.toFixed(1)}   Eintrag ${mass.inflow.toFixed(1)}  Austrag ${mass.outflow.toFixed(1)}`,
      );
      if (state.driftPct !== null) {
        const ok = Math.abs(state.driftPct) <= state.driftTolerancePct;
        lines.push(
          `        Residuum ${state.driftPct >= 0 ? "+" : ""}${state.driftPct.toFixed(3)} % ` +
            `${ok ? "in Toleranz" : "AUSSERHALB"} (${state.driftTolerancePct} %)`,
        );
      }
      if (state.initialTotal) {
        lines.push(`        Korridor ${(mass.total / state.initialTotal).toFixed(3)} der Startmasse`);
      }
    } else {
      lines.push("Masse   (warte auf Readback)");
    }

    if (state.chronicle.length > 0) {
      lines.push("", "Chronik");
      for (const entry of state.chronicle.slice(0, 2)) {
        const when = entry.t.slice(0, 16).replace("T", " ");
        lines.push(`  ${when}`, ...wrap(entry.text, 44).map((line) => `    ${line}`));
      }
    }

    lines.push("", "Wetterdaten: Open-Meteo.com, CC BY 4.0");

    this.element.textContent = lines.filter((line) => line !== "").join("\n");
  }
}

function wrap(text: string, width: number): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    if (current.length + word.length + 1 > width) {
      if (current) lines.push(current);
      current = word;
    } else {
      current = current ? `${current} ${word}` : word;
    }
  }
  if (current) lines.push(current);
  return lines;
}
