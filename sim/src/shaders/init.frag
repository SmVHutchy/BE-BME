#version 300 es
// Startzustand.
//
// Nur wirksam, wenn kein Snapshot wiederhergestellt wird. Das Muster entsteht
// hash-basiert aus run.seed: Derselbe Seed ergibt denselben Startzustand, ohne
// dass eine Datei mitgeliefert werden muss.
//
// Die Bilanzkanaele starten bei null. Die Startmasse ist damit die Bezugsgroesse
// aller spaeteren Bilanzpruefungen.

out vec4 fragColor;

uniform vec2 uResolution;
uniform uint uSeed;

// aus config: init.*
uniform float uNutrientLevel;
uniform float uProducerLevel;
uniform float uPatchScale;
uniform float uPatchThreshold;

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;

  // Wenige grosse Inseln statt eines feinen Startmusters: Das System soll seine
  // Struktur selbst entwickeln und sie nicht vom Anfangszustand vorgezeichnet
  // bekommen. Sonst waere Woche 6 dem Startmuster noch anzusehen.
  // "patch" waere hier ein reserviertes GLSL-Wort (Tessellation).
  float patchNoise = fbm(uv * uPatchScale, uSeed + 31u);
  float producer = patchNoise > uPatchThreshold ? uProducerLevel : 0.0;

  // Leichte Streuung des Vorrats, damit nicht jede Zelle identisch startet -
  // ein perfekt homogenes Feld wuerde erst durch numerisches Rauschen brechen.
  float jitter = 0.9 + 0.2 * valueNoise(uv * uPatchScale * 3.0, uSeed + 977u);

  fragColor = vec4(uNutrientLevel * jitter, producer, 0.0, 0.0);
}
