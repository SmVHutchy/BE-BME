/**
 * Umrechnung der Konfiguration in Shader-Uniforms.
 *
 * Die einzige Stelle, an der Zeitkonstanten zu Raten werden. In
 * config/params.yaml stehen Stunden und Tage, weil sich das in der Arbeit
 * begruenden laesst und ein Zehnerfehler sofort auffaellt; der Shader braucht
 * Raten je Weltsekunde.
 *
 * Es entsteht hier kein neuer Zahlenwert. Jede Groesse geht auf einen
 * Config-Eintrag zurueck (Regel 7 in CLAUDE.md).
 */

export interface SimConfig {
  run: { seed: number; name: string };
  sim: {
    grid: { width: number; height: number };
    tick_hz: number;
    dt_base: number;
    speed: number;
    readback_interval_s: number;
    /** Deckelt den Abstand zweier Messpunkte in Weltzeit (A14). */
    max_world_seconds_per_sample: number;
  };
  field: {
    nutrient: {
      diffusion_coefficient: number;
      remineralization_rate: number;
      refuge_floor: number;
      input_per_day_at_max: number;
    };
    producer: {
      doubling_time_hours: number;
      light_half_saturation: number;
      nutrient_half_saturation: number;
      lifetime_hours: number;
      max_density: number;
    };
  };
  init: {
    nutrient_level: number;
    producer_level: number;
    producer_patch_scale: number;
    producer_patch_threshold: number;
  };
  flow: {
    curl_noise_scale: number;
    curl_noise_strength: number;
    advection_dissipation: number;
    base_current_gain: number;
  };
  mass: {
    sedimentation_half_life_days: number;
    corridor_min: number;
    corridor_max: number;
    drift_tolerance_pct: number;
  };
  coupling: {
    rate: { output_max: number };
    pulse_low: { gain: number; radius_cells: number; decay_seconds: number };
    pulse_high: {
      gain: number;
      amount: number;
      radius_cells: number;
      decay_seconds: number;
    };
  };
  health: { interval_s: number };
  snapshot: { interval_minutes: number; keep_last: number };
}

const SECONDS_PER_HOUR = 3600;
const SECONDS_PER_DAY = 86400;

/** Raten je Weltsekunde, wie der Shader sie erwartet. */
export interface DerivedRates {
  /** Wachstumsrate bei Licht- und Naehrstoffsaettigung. */
  growthRate: number;
  /** Sterberate der Biomasse. */
  deathRate: number;
  /** Sedimentation, der einzige Austrag. */
  sedimentationRate: number;
  /** Naehrstoffeintrag bei env.nutrient_input = 1. */
  inputRate: number;
}

export function deriveRates(config: SimConfig): DerivedRates {
  const producer = config.field.producer;
  const nutrient = config.field.nutrient;

  return {
    // Verdopplung in T Stunden entspricht exponentiellem Wachstum mit ln(2)/T.
    growthRate: Math.LN2 / (producer.doubling_time_hours * SECONDS_PER_HOUR),
    // Mittlere Lebensdauer T entspricht der Zerfallsrate 1/T.
    deathRate: 1 / (producer.lifetime_hours * SECONDS_PER_HOUR),
    // Halbwertszeit T entspricht ln(2)/T.
    sedimentationRate: Math.LN2 / (config.mass.sedimentation_half_life_days * SECONDS_PER_DAY),
    inputRate: nutrient.input_per_day_at_max / SECONDS_PER_DAY,
  };
}

/**
 * Prueft die Stabilitaetsgrenze der expliziten Diffusion.
 *
 * Wirft, statt still zu divergieren. Ein Lauf, der nach zwei Wochen in NaN
 * kippt, kostet zwei Wochen; ein Abbruch beim Start kostet eine Minute.
 */
export function assertStable(config: SimConfig): void {
  const limit = 0.25;
  const dtMax = config.sim.dt_base * config.coupling.rate.output_max;
  const factor = config.field.nutrient.diffusion_coefficient * dtMax;

  if (factor >= limit) {
    throw new Error(
      `Diffusion instabil: diffusion_coefficient * dt_base * rate.output_max = ` +
        `${factor.toFixed(4)} >= ${limit}. ` +
        `Entweder field.nutrient.diffusion_coefficient, sim.dt_base oder ` +
        `coupling.rate.output_max in config/params.yaml senken.`,
    );
  }
}

/** Weltsekunden, die pro Wanduhrsekunde vergehen - nur fuer die Anzeige. */
export function worldSecondsPerWallSecond(config: SimConfig, rate: number): number {
  return config.sim.dt_base * rate * config.sim.tick_hz * config.sim.speed;
}
