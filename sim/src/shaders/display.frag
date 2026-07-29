#version 300 es
// Anzeige.
//
// AUSDRUECKLICH KEIN LOOK-DEVELOPMENT. Farbgebung und finale Darstellung sind
// laut Aufgabenstellung nicht Teil von Prototyp 0. Dies hier ist ein
// Diagnosebild: Man soll sehen, ob Naehrstoff und Biomasse sich raeumlich
// sinnvoll verhalten, mehr nicht.
//
// Zwei Kanaele, zwei Farben, keine Nachbearbeitung.

out vec4 fragColor;

uniform sampler2D uState;
uniform vec2 uResolution;
uniform float uMaxDensity;

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;
  vec4 state = texture(uState, uv);

  float nutrient = clamp(state.r, 0.0, 1.0);
  float producer = clamp(state.g / uMaxDensity, 0.0, 1.0);

  // Naehrstoff dunkelblau, Biomasse gruen. Bewusst flach und ohne Verlauf,
  // damit man Zahlen und nicht Gestaltung sieht.
  vec3 color = vec3(0.0, 0.0, nutrient * 0.35) + vec3(0.1, 0.85, 0.3) * producer;

  fragColor = vec4(color, 1.0);
}
