#version 300 es
// Stroemungsfeld.
//
// Zwei Angriffspunkte treffen sich hier, aber an unterschiedlichen Stellen -
// das ist der Grund, warum die 1:1-Regel gewahrt bleibt (docs/mapping.md):
//
//   Kopplung 4 (Wind)      -> Grundrichtung des GESAMTEN Feldes
//   Kopplung 5 (Bassband)  -> lokaler, abklingender Wirbel
//
// Der Curl eines Rauschfeldes ist quellenfrei (Divergenz null). Das ist keine
// Aesthetik, sondern eine Voraussetzung der Massenbilanz: Ein Stroemungsfeld
// mit Quellen wuerde bei der Advektion Masse anhaeufen oder verduennen.

out vec4 fragColor;

uniform vec2 uResolution;
uniform uint uSeed;
uniform uint uTick;
uniform float uWorldTime;      // akkumulierte Weltsekunden

// aus config: flow.*
uniform float uCurlScale;
uniform float uCurlStrength;
uniform float uBaseCurrentGain;

// aus dem Vertrag: env.wind
uniform float uWindDirDeg;
uniform float uWindSpeed;

// aus dem Vertrag: pulse.band = "low", abklingend
uniform vec2 uPulsePos;        // Zellkoordinate des juengsten Bassimpulses
uniform float uPulseStrength;  // bereits mit der Abklingkurve verrechnet
uniform float uPulseRadius;

float potential(vec2 p) {
  return fbm(p, uSeed);
}

void main() {
  vec2 cell = gl_FragCoord.xy;
  vec2 uv = cell / uResolution;

  // --- Curl-Noise ---------------------------------------------------------
  // Das Potenzialfeld wandert langsam mit der Weltzeit, damit die Wirbel nicht
  // ortsfest stehen. Die Drift stammt aus uWorldTime, nicht aus der
  // Wanduhrzeit - sonst waere der Lauf nicht reproduzierbar.
  vec2 p = uv * uCurlScale + vec2(uWorldTime * 1.0e-5, 0.0);
  float eps = 1.0 / uCurlScale * 0.01;
  float dx = potential(p + vec2(eps, 0.0)) - potential(p - vec2(eps, 0.0));
  float dy = potential(p + vec2(0.0, eps)) - potential(p - vec2(0.0, eps));
  // Curl in 2D: senkrecht zum Gradienten.
  vec2 curl = vec2(dy, -dx) / (2.0 * eps);

  vec2 velocity = curl * uCurlStrength;

  // --- Kopplung 4: Grundstroemung aus dem Wind ----------------------------
  velocity += windToFlow(uWindDirDeg) * uWindSpeed * uBaseCurrentGain;

  // --- Kopplung 5: lokaler Wirbel aus dem Bassband ------------------------
  if (uPulseStrength > 0.0) {
    // Kuerzester Abstand auf dem Torus - die Welt hat umlaufende Raender.
    vec2 delta = cell - uPulsePos;
    delta -= uResolution * round(delta / uResolution);
    float distance = length(delta);
    if (distance < uPulseRadius && distance > 0.001) {
      // Tangential statt radial: ein Wirbel, keine Explosion. Eine radiale
      // Auslenkung haette eine Divergenz und wuerde Masse verschieben statt
      // umruehren.
      vec2 tangential = vec2(-delta.y, delta.x) / distance;
      float falloff = 1.0 - distance / uPulseRadius;
      velocity += tangential * falloff * falloff * uPulseStrength;
    }
  }

  fragColor = vec4(velocity, 0.0, 1.0);
}
