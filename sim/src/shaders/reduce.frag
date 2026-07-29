#version 300 es
// Progressive Halbierung zur Summe.
//
// Jeder Durchgang summiert 2x2 Zellen in eine. Nach log2(512) = 9 Durchgaengen
// steht in einer einzigen Zelle die Summe aller vier Kanaele:
//
//   R = Naehrstoff gesamt   G = Biomasse gesamt
//   B = Eintrag gesamt      A = Austrag gesamt
//
// Daraus ergibt sich der Residualsaldo unmittelbar - deshalb liefert dieser
// eine Shader alles, was die Massenbilanz braucht.
//
// Summiert wird in 32 Bit. In float16 waere der Fehler beim Aufaddieren von
// 262144 Werten groesser als die 2 % Drift, die nachgewiesen werden sollen.

out vec4 fragColor;

uniform sampler2D uSource;
uniform vec2 uSourceResolution;

void main() {
  // Die vier Quellzellen, die zu dieser Zielzelle gehoeren.
  vec2 base = floor(gl_FragCoord.xy) * 2.0;
  vec2 texel = 1.0 / uSourceResolution;

  vec4 sum = vec4(0.0);
  sum += texture(uSource, (base + vec2(0.5, 0.5)) * texel);
  sum += texture(uSource, (base + vec2(1.5, 0.5)) * texel);
  sum += texture(uSource, (base + vec2(0.5, 1.5)) * texel);
  sum += texture(uSource, (base + vec2(1.5, 1.5)) * texel);

  fragColor = sum;
}
