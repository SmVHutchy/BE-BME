/**
 * WebGL2-Kontext und Texturen.
 *
 * RGBA32F ueber `EXT_color_buffer_float`. Halbe Genauigkeit waere hier keine
 * Option: Die Massensumme laeuft ueber 512^2 = 262144 Zellen, und in float16
 * (rund drei signifikante Stellen) waere der Summationsfehler groesser als die
 * 2 % Drift, die nachgewiesen werden sollen.
 */

export interface GlContext {
  gl: WebGL2RenderingContext;
  canvas: HTMLCanvasElement;
}

export function createContext(canvas: HTMLCanvasElement): GlContext {
  const gl = canvas.getContext("webgl2", {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    // Der Inhalt wird ueber Wochen fortgeschrieben; ein Verwerfen des Puffers
    // nach jedem Frame kostet nichts und vermeidet Ueberraschungen.
    preserveDrawingBuffer: false,
    powerPreference: "high-performance",
  });

  if (!gl) {
    throw new Error("WebGL2 nicht verfuegbar. Das Projekt setzt WebGL2 voraus (Exposé 7.2).");
  }

  // Ohne diese Erweiterung laesst sich nicht in Gleitkommatexturen rendern.
  // Kein Notbehelf moeglich: Ping-Pong-FBOs in 8 Bit wuerden die Felder auf
  // 256 Stufen quantisieren und jede Massenbilanz sinnlos machen.
  if (!gl.getExtension("EXT_color_buffer_float")) {
    throw new Error(
      "EXT_color_buffer_float fehlt. Ohne Gleitkomma-Renderziele ist keine " +
        "belastbare Massenbilanz moeglich.",
    );
  }
  // Lineares Filtern von 32F-Texturen: fuer die semi-lagrangesche Advektion.
  // Fehlt sie, wird auf Nearest zurueckgefallen - sichtbar grober, aber lauffaehig.
  const linearFloat = gl.getExtension("OES_texture_float_linear");
  if (!linearFloat) {
    console.warn(
      "OES_texture_float_linear fehlt - Advektion faellt auf Nearest zurueck. " +
        "Erwartete Folge: sichtbar kantigere Stroemung und hoehere Massendrift.",
    );
  }

  return { gl, canvas };
}

export function hasLinearFloat(gl: WebGL2RenderingContext): boolean {
  return gl.getExtension("OES_texture_float_linear") !== null;
}

/** Erzeugt eine RGBA32F-Textur in der Feldaufloesung. */
export function createFieldTexture(
  gl: WebGL2RenderingContext,
  width: number,
  height: number,
  data: Float32Array | null = null,
  linear = false,
): WebGLTexture {
  const texture = gl.createTexture();
  if (!texture) throw new Error("Textur konnte nicht angelegt werden");

  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, width, height, 0, gl.RGBA, gl.FLOAT, data);

  const filter = linear && hasLinearFloat(gl) ? gl.LINEAR : gl.NEAREST;
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
  // Umlaufende Ränder: Die Welt hat keinen Rand, an dem sich Masse staut.
  // Ein CLAMP_TO_EDGE wuerde Stroemung und Naehrstoff an den Kanten anreichern
  // und dort ein Artefakt erzeugen, das nichts mit dem Oekosystem zu tun hat.
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
  gl.bindTexture(gl.TEXTURE_2D, null);

  return texture;
}

export function createFramebuffer(
  gl: WebGL2RenderingContext,
  texture: WebGLTexture,
): WebGLFramebuffer {
  const framebuffer = gl.createFramebuffer();
  if (!framebuffer) throw new Error("Framebuffer konnte nicht angelegt werden");

  gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);

  const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
  if (status !== gl.FRAMEBUFFER_COMPLETE) {
    throw new Error(`Framebuffer unvollstaendig: 0x${status.toString(16)}`);
  }
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);

  return framebuffer;
}
