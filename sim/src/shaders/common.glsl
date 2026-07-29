// Gemeinsame Bausteine aller Shader.
//
// REPRODUZIERBARKEIT: Jeder Zufall entsteht hier hash-basiert aus (seed, tick,
// Position). Es gibt keinen Aufruf, der Wanduhrzeit, Frame-Zeit oder einen
// ungeseedeten Generator benutzt. Nur deshalb rekonstruieren run.seed,
// params.yaml und der Wetter-Rohlog einen Lauf vollstaendig - und nur deshalb
// ist ein Zeitrafferlauf bitgleich mit einem Echtzeitlauf.

precision highp float;
precision highp int;

// --- Ganzzahl-Hash ---------------------------------------------------------
// PCG-artige Durchmischung. Ganzzahlig und damit auf jeder GPU bitgleich -
// float-basierte Hashes wie fract(sin(x)*43758.5453) streuen zwischen
// Herstellern und waeren fuer eine reproduzierbare Arbeit unbrauchbar.

uint hashUint(uint x) {
  x += (x << 10u);
  x ^= (x >> 6u);
  x += (x << 3u);
  x ^= (x >> 11u);
  x += (x << 15u);
  return x;
}

uint hashCombine(uint a, uint b) {
  return hashUint(a ^ (b + 0x9e3779b9u + (a << 6) + (a >> 2)));
}

/** Gleichverteilt in [0,1) aus drei Ganzzahlen. */
float hashToUnit(uint a, uint b, uint c) {
  uint h = hashCombine(hashCombine(a, b), c);
  return float(h & 0x00ffffffu) / float(0x01000000u);
}

/** Rauschwert fuer eine Zelle, abhaengig von Seed, Tick und Position. */
float cellNoise(uvec2 cell, uint seed, uint tick) {
  return hashToUnit(cell.x * 1973u + cell.y * 9277u, seed, tick);
}

// --- Wertrauschen mit Interpolation ---------------------------------------
// Fuer das Stroemungsfeld und das Startmuster. Deterministisch aus dem Seed,
// ohne Zeitabhaengigkeit: Das Stroemungsmuster soll ueber die Zeit wandern,
// nicht in jedem Tick neu gewuerfelt werden.

float valueNoise(vec2 p, uint seed) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  // Smoothstep-Gewichte: stetig differenzierbar, damit das abgeleitete
  // Curl-Feld keine sichtbaren Kanten bekommt.
  vec2 w = f * f * (3.0 - 2.0 * f);

  uvec2 base = uvec2(ivec2(i) + 4096);
  float a = hashToUnit(base.x, base.y, seed);
  float b = hashToUnit(base.x + 1u, base.y, seed);
  float c = hashToUnit(base.x, base.y + 1u, seed);
  float d = hashToUnit(base.x + 1u, base.y + 1u, seed);

  return mix(mix(a, b, w.x), mix(c, d, w.x), w.y);
}

/** Mehrere Oktaven - grosse ruhige Wirbel mit feiner Struktur darin. */
float fbm(vec2 p, uint seed) {
  float sum = 0.0;
  float amplitude = 0.5;
  for (int octave = 0; octave < 3; octave++) {
    sum += amplitude * valueNoise(p, seed + uint(octave) * 977u);
    p *= 2.0;
    amplitude *= 0.5;
  }
  return sum;
}

// --- Hilfsgroessen ---------------------------------------------------------

/** Meteorologische Windrichtung (Richtung, AUS der er weht) in einen
 *  Stroemungsvektor (Richtung, IN die er blaest). */
vec2 windToFlow(float dirDeg) {
  float radians = radians(dirDeg);
  // 0 Grad = Nord = Wind kommt von oben, blaest also nach unten (-y).
  return vec2(-sin(radians), -cos(radians));
}
