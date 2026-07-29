/**
 * Ping-Pong-FBO-Paar.
 *
 * Ein Fragment-Shader kann die Textur, in die er schreibt, nicht gleichzeitig
 * lesen. Jedes Feld existiert deshalb zweimal: gelesen wird aus `read`,
 * geschrieben nach `write`, danach werden beide getauscht.
 */

import { createFieldTexture, createFramebuffer } from "./context";

export class PingPong {
  private textures: [WebGLTexture, WebGLTexture];
  private framebuffers: [WebGLFramebuffer, WebGLFramebuffer];
  private current = 0;

  constructor(
    private readonly gl: WebGL2RenderingContext,
    readonly width: number,
    readonly height: number,
    initial: Float32Array | null = null,
    linear = false,
  ) {
    const a = createFieldTexture(gl, width, height, initial, linear);
    const b = createFieldTexture(gl, width, height, initial, linear);
    this.textures = [a, b];
    this.framebuffers = [createFramebuffer(gl, a), createFramebuffer(gl, b)];
  }

  /** Die Textur, aus der gelesen wird. */
  get read(): WebGLTexture {
    return this.textures[this.current]!;
  }

  /** Bindet das Ziel und setzt den Viewport auf die Feldgroesse. */
  bindWrite(): void {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffers[1 - this.current]!);
    gl.viewport(0, 0, this.width, this.height);
  }

  /** Tauscht Lese- und Schreibseite. Nach jedem Durchgang genau einmal aufrufen. */
  swap(): void {
    this.current = 1 - this.current;
  }

  /**
   * Schreibt Daten direkt in die Leseseite.
   *
   * Wird beim Wiederherstellen eines Snapshots gebraucht: Der Zustand kommt
   * dann nicht aus einem Shader, sondern von der Platte.
   */
  upload(data: Float32Array): void {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.read);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, this.width, this.height, gl.RGBA, gl.FLOAT, data);
    gl.bindTexture(gl.TEXTURE_2D, null);
  }

  /**
   * Liest die Leseseite vollstaendig zurueck - synchron.
   *
   * Nur fuer Snapshots. Der Aufruf haelt die Pipeline an; bei 512^2 RGBA32F
   * sind das 4 MB je Feld. Im Simulationstakt hat er nichts zu suchen, dort
   * laeuft der asynchrone Weg ueber `metrics/readback.ts`.
   */
  readAll(): Float32Array {
    const gl = this.gl;
    const pixels = new Float32Array(this.width * this.height * 4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffers[this.current]!);
    gl.readPixels(0, 0, this.width, this.height, gl.RGBA, gl.FLOAT, pixels);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return pixels;
  }
}
