#version 300 es
// Semi-lagrangesche Advektion.
//
// Rueckwaerts verfolgt: Woher kaeme das, was jetzt in dieser Zelle liegt?
// Etablierter Operator, wie in Exposé 7.3 gefordert - keine eigene Numerik.
//
// Bewegt werden nur die beiden PHYSIKALISCHEN Kanaele (Naehrstoff, Biomasse).
// Die beiden Bilanzkanaele bleiben ortsfest: Sie zaehlen, wieviel an dieser
// Stelle insgesamt ein- und ausgetragen wurde, und duerfen nicht mitstroemen -
// sonst waere die Bilanz selbst der Advektionsdrift ausgesetzt, die sie messen
// soll.

out vec4 fragColor;

uniform sampler2D uState;      // R=Naehrstoff  G=Biomasse  B=Eintrag  A=Austrag
uniform sampler2D uVelocity;
uniform vec2 uResolution;
uniform float uDt;             // dt_eff = dt_base * rate
uniform float uDissipation;

void main() {
  vec2 cell = gl_FragCoord.xy;
  vec2 uv = cell / uResolution;

  vec2 velocity = texture(uVelocity, uv).xy;

  // Rueckwaertsschritt in Zellkoordinaten. Die Textur laeuft um (REPEAT),
  // deshalb braucht es hier keine Randbehandlung.
  vec2 source = (cell - velocity * uDt) / uResolution;

  vec4 advected = texture(uState, source);
  vec4 here = texture(uState, uv);

  fragColor = vec4(
    advected.rg * uDissipation,  // Naehrstoff und Biomasse stroemen mit
    here.ba                      // Bilanzkanaele bleiben, wo sie sind
  );
}
