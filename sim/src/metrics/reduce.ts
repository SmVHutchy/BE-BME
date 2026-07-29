/**
 * Massenreduktion und asynchroner Readback.
 *
 * Die Bilanz wird JEDEN Tick auf der GPU gerechnet - eine Kette von
 * Halbierungen bis auf 1x1. Uebertragen wird nur alle
 * `sim.readback_interval_s` Sekunden, und zwar asynchron.
 *
 * Warum asynchron: `gl.readPixels` synchronisiert CPU und GPU und wartet, bis
 * alle offenen Zeichenbefehle fertig sind. In einem System, das monatelang
 * durchlaeuft und bei speed = 100 tausend Ticks je Sekunde rechnet, waere das
 * ein regelmaessiger Einbruch. Ueber `fenceSync` wird stattdessen gefragt, ob
 * das Ergebnis schon bereitliegt, und erst dann gelesen.
 */

import { createFieldTexture, createFramebuffer } from "../gl/context";
import { Program, drawFullscreen } from "../gl/program";

export interface MassTotals {
  nutrient: number;
  producer: number;
  inflow: number;
  outflow: number;
  total: number;
}

interface Level {
  size: number;
  texture: WebGLTexture;
  framebuffer: WebGLFramebuffer;
}

export class MassReducer {
  private readonly levels: Level[] = [];
  private readonly pixel = new Float32Array(4);
  private pending: { sync: WebGLSync; buffer: WebGLBuffer } | null = null;

  constructor(
    private readonly gl: WebGL2RenderingContext,
    private readonly program: Program,
    width: number,
    height: number,
  ) {
    if (width !== height || (width & (width - 1)) !== 0) {
      throw new Error(
        `Feldaufloesung ${width}x${height} ist nicht quadratisch mit Zweierpotenz. ` +
          `Die Reduktionskette halbiert bis 1x1 und setzt das voraus.`,
      );
    }

    // Kette 256, 128, ... 1. Die erste Halbierung liest das Zustandsfeld selbst.
    for (let size = width >> 1; size >= 1; size >>= 1) {
      const texture = createFieldTexture(gl, size, size);
      this.levels.push({ size, texture, framebuffer: createFramebuffer(gl, texture) });
    }
  }

  /** Fuehrt die Reduktionskette aus. Ergebnis bleibt auf der GPU. */
  reduce(source: WebGLTexture, sourceSize: number): void {
    const gl = this.gl;
    this.program.use();

    let input = source;
    let inputSize = sourceSize;

    for (const level of this.levels) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, level.framebuffer);
      gl.viewport(0, 0, level.size, level.size);
      this.program.setTexture("uSource", input, 0);
      this.program.setVec2("uSourceResolution", inputSize, inputSize);
      drawFullscreen(gl);
      input = level.texture;
      inputSize = level.size;
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  /**
   * Stoesst einen asynchronen Readback des 1x1-Ergebnisses an.
   *
   * Tut nichts, wenn noch einer aussteht - dann war das Intervall kuerzer als
   * die Latenz der GPU, und ein zweiter Auftrag wuerde nur die Warteschlange
   * fuellen.
   */
  requestReadback(): void {
    if (this.pending) return;

    const gl = this.gl;
    const last = this.levels[this.levels.length - 1];
    if (!last) return;

    const buffer = gl.createBuffer();
    if (!buffer) return;

    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, buffer);
    gl.bufferData(gl.PIXEL_PACK_BUFFER, 16, gl.STREAM_READ);
    gl.bindFramebuffer(gl.FRAMEBUFFER, last.framebuffer);
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.FLOAT, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);

    const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
    if (!sync) {
      gl.deleteBuffer(buffer);
      return;
    }
    this.pending = { sync, buffer };
  }

  /**
   * Liefert die Summen, sobald die GPU fertig ist - sonst `null`.
   *
   * Wird jeden Frame aufgerufen und blockiert nie.
   */
  poll(): MassTotals | null {
    if (!this.pending) return null;

    const gl = this.gl;
    const status = gl.clientWaitSync(this.pending.sync, 0, 0);
    if (status === gl.TIMEOUT_EXPIRED || status === gl.WAIT_FAILED) {
      return null;
    }

    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, this.pending.buffer);
    gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, 0, this.pixel);
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);

    gl.deleteSync(this.pending.sync);
    gl.deleteBuffer(this.pending.buffer);
    this.pending = null;

    const nutrient = this.pixel[0] ?? 0;
    const producer = this.pixel[1] ?? 0;
    return {
      nutrient,
      producer,
      inflow: this.pixel[2] ?? 0,
      outflow: this.pixel[3] ?? 0,
      // Konsumenten kommen erst in Prototyp 1; bis dahin ist ihr Beitrag null.
      total: nutrient + producer,
    };
  }
}
