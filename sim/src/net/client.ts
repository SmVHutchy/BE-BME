/**
 * Der Vertrag, Seite `sim`.
 *
 * Massgeblich ist docs/contract.md. `sim` verbindet sich als Client zu `core`,
 * empfaengt `env` und `pulse` und sendet Metriken und Health.
 *
 * Bei Verbindungsverlust wird mit Backoff neu verbunden - und die Simulation
 * laeuft mit den zuletzt empfangenen env-Werten weiter. Das ist die geforderte
 * Betriebseigenschaft: Ein Ausfall des Klimakanals darf im Bild nicht sichtbar
 * werden (Exposé Risiko 8).
 */

import type { SimConfig } from "../sim/params";

export interface EnvValues {
  light: number;
  nutrient_input: number;
  rate: number;
  wind: { dir_deg: number; speed: number };
}

export interface PulseValues {
  band: "low" | "high";
  level: number;
}

export interface MetricsPayload {
  t: string;
  tick: number;
  mass: {
    nutrient: number;
    producer: number;
    consumer: number;
    total: number;
    inflow_total: number;
    outflow_total: number;
  };
  lineages: number;
  gene_median: Record<string, number>;
  occupancy: number;
}

export interface HealthPayload {
  t: string;
  tick: number;
  frame_ms: number;
  sim_hz: number;
  heap_mb: number | null;
  gl_context_lost: number;
  speed: number;
}

/** Holt config/params.yaml als JSON. `core` ist die Quelle der Wahrheit. */
export async function fetchConfig(
  baseUrl: string,
): Promise<{ config: SimConfig; configHash: string }> {
  const response = await fetch(`${baseUrl}/config`);
  if (!response.ok) {
    throw new Error(
      `GET /config fehlgeschlagen (${response.status}). Laeuft core? ` +
        `sim holt jeden Parameter von dort und startet ohne die Konfiguration nicht.`,
    );
  }
  const payload = (await response.json()) as { config: SimConfig; config_hash: string };
  return { config: payload.config, configHash: payload.config_hash };
}

export class ContractClient {
  private socket: WebSocket | null = null;
  private reconnectDelay = 1000;
  private readonly maxDelay = 30000;
  private closed = false;

  /** Zuletzt empfangene Klimawerte. Ueberleben eine Trennung bewusst. */
  env: EnvValues | null = null;

  onPulse: ((pulse: PulseValues) => void) | null = null;
  onEnv: ((env: EnvValues) => void) | null = null;

  constructor(private readonly url: string) {}

  get connected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    if (this.closed) return;

    const socket = new WebSocket(this.url);
    this.socket = socket;

    socket.addEventListener("open", () => {
      console.info(`Vertrag: verbunden mit ${this.url}`);
      this.reconnectDelay = 1000;
    });

    socket.addEventListener("message", (event) => {
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(event.data as string) as Record<string, unknown>;
      } catch {
        console.warn("Vertrag: Nachricht ist kein gueltiges JSON");
        return;
      }
      // Unterscheidung am Schluessel, kein Envelope. Unbekannte Nachrichten
      // werden schweigend ignoriert, damit ein neueres core dieses sim nicht
      // zerreisst (docs/contract.md).
      if ("env" in payload) {
        this.env = payload["env"] as EnvValues;
        this.onEnv?.(this.env);
      } else if ("pulse" in payload) {
        this.onPulse?.(payload["pulse"] as PulseValues);
      }
    });

    socket.addEventListener("close", () => {
      if (this.closed) return;
      console.warn(
        `Vertrag: getrennt. Neuer Versuch in ${this.reconnectDelay} ms. ` +
          `Die Simulation laeuft mit den letzten bekannten env-Werten weiter.`,
      );
      window.setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay);
    });

    socket.addEventListener("error", () => {
      socket.close();
    });
  }

  send(payload: MetricsPayload | { health: HealthPayload }): void {
    if (this.connected) {
      this.socket?.send(JSON.stringify(payload));
    }
    // Bei getrennter Verbindung wird verworfen und NICHT nachgesendet. Eine
    // Luecke in der Zeitreihe ist ehrlicher als nachtraeglich eingefuegte Werte,
    // und der Detektor arbeitet ohnehin stichprobenbasiert.
  }

  close(): void {
    this.closed = true;
    this.socket?.close();
  }
}
