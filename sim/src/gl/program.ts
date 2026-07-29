/**
 * Shader uebersetzen, binden und mit Uniforms versorgen.
 *
 * Alle Uniformwerte stammen aus config/params.yaml, das `sim` beim Start ueber
 * GET /config holt. Es gibt keinen Zahlenwert im Shader, der nicht von dort
 * kommt - das ist Regel 7 aus CLAUDE.md und die Voraussetzung dafuer, dass in
 * der Arbeit jeder Parameter begruendet werden kann.
 */

/**
 * Ein Vollbild-Dreieck statt eines Quads.
 *
 * Deckt den Bildschirm mit drei statt sechs Vertices ab und vermeidet die
 * diagonale Naht, an der ein Quad seine beiden Dreiecke doppelt beschattet.
 */
const VERTEX_SHADER = `#version 300 es
void main() {
  vec2 position = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  gl_Position = vec4(position * 2.0 - 1.0, 0.0, 1.0);
}`;

function compile(gl: WebGL2RenderingContext, type: number, source: string): WebGLShader {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("Shader konnte nicht angelegt werden");

  gl.shaderSource(shader, source);
  gl.compileShader(shader);

  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader) ?? "(kein Log)";
    // Zeilennummern dazu: Ein GLSL-Fehler ohne Zeilenbezug ist in einem
    // zusammengesetzten Shader kaum zu finden.
    const numbered = source
      .split("\n")
      .map((line, index) => `${String(index + 1).padStart(4)} | ${line}`)
      .join("\n");
    gl.deleteShader(shader);
    throw new Error(`Shader-Uebersetzung fehlgeschlagen:\n${log}\n\n${numbered}`);
  }
  return shader;
}

export class Program {
  readonly program: WebGLProgram;
  private readonly uniforms = new Map<string, WebGLUniformLocation | null>();

  constructor(
    private readonly gl: WebGL2RenderingContext,
    fragmentSource: string,
    readonly name: string,
  ) {
    const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
    const fragment = compile(gl, gl.FRAGMENT_SHADER, fragmentSource);

    const program = gl.createProgram();
    if (!program) throw new Error("Programm konnte nicht angelegt werden");
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const log = gl.getProgramInfoLog(program) ?? "(kein Log)";
      throw new Error(`Programm ${name} nicht linkbar: ${log}`);
    }
    gl.deleteShader(vertex);
    gl.deleteShader(fragment);
    this.program = program;
  }

  use(): void {
    this.gl.useProgram(this.program);
  }

  private location(name: string): WebGLUniformLocation | null {
    if (!this.uniforms.has(name)) {
      this.uniforms.set(name, this.gl.getUniformLocation(this.program, name));
    }
    return this.uniforms.get(name) ?? null;
  }

  setFloat(name: string, value: number): void {
    const location = this.location(name);
    if (location) this.gl.uniform1f(location, value);
  }

  setInt(name: string, value: number): void {
    const location = this.location(name);
    if (location) this.gl.uniform1i(location, value);
  }

  setVec2(name: string, x: number, y: number): void {
    const location = this.location(name);
    if (location) this.gl.uniform2f(location, x, y);
  }

  /** Bindet eine Textur an eine Einheit und setzt das zugehoerige Sampler-Uniform. */
  setTexture(name: string, texture: WebGLTexture, unit: number): void {
    const gl = this.gl;
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    this.setInt(name, unit);
  }
}

/** Zeichnet das Vollbild-Dreieck in das gerade gebundene Ziel. */
export function drawFullscreen(gl: WebGL2RenderingContext): void {
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}
