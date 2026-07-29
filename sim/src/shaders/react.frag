#version 300 es
// Diffusion, Wachstum, Sterben, Eintrag, Austrag.
//
// Hier schliesst sich der Stoffkreislauf: Was stirbt, geht vollstaendig ins
// Naehrstofffeld zurueck (Exposé 6.2). Intern ist der Kreislauf damit
// verlustfrei; nach aussen ist er offen, und beide Richtungen werden gezaehlt.
//
// KANALBELEGUNG des Zustands:
//   R = Naehrstoff
//   G = Biomasse der Produzenten
//   B = kumulierter Eintrag  an dieser Zelle  (Niederschlag, Pulse, Refugium)
//   A = kumulierter Austrag  an dieser Zelle  (Sedimentation)
//
// B und A sind der Grund, warum die Massenbilanz ueberhaupt pruefbar ist: Die
// Reduktion summiert alle vier Kanaele, und daraus ergibt sich der
// Residualsaldo direkt (docs/annahmen.md A4).
//
// Zwei Angriffspunkte, sauber getrennt (docs/mapping.md):
//   Kopplung 1 (Licht)          -> Wachstumsterm der Produzenten
//   Kopplung 2 (Niederschlag)   -> flaechiger Eintrag
//   Kopplung 6 (Hochtonband)    -> punktuelles Partikel

out vec4 fragColor;

uniform sampler2D uState;
uniform vec2 uResolution;
uniform float uDt;
uniform uint uSeed;
uniform uint uTick;

// aus config: field.nutrient.*
uniform float uDiffusion;
uniform float uRemineralization;
uniform float uRefugeFloor;
uniform float uInputRate;        // je Weltsekunde bei nutrient_input = 1

// aus config: field.producer.*
uniform float uGrowthRate;       // je Weltsekunde bei Saettigung
uniform float uLightHalf;
uniform float uNutrientHalf;
uniform float uDeathRate;        // je Weltsekunde
uniform float uMaxDensity;

// aus config: mass.*
uniform float uSedimentationRate;

// aus dem Vertrag: env
uniform float uLight;
uniform float uNutrientInput;

// aus dem Vertrag: pulse.band = "high"
uniform vec2 uParticlePos;
uniform float uParticleAmount;
uniform float uParticleRadius;

void main() {
  vec2 cell = gl_FragCoord.xy;
  vec2 texel = 1.0 / uResolution;
  vec2 uv = cell * texel;

  vec4 state = texture(uState, uv);
  float nutrient = state.r;
  float producer = state.g;
  float inflowAcc = state.b;
  float outflowAcc = state.a;

  // --- Diffusion des Naehrstoffs -----------------------------------------
  // Fuenf-Punkt-Laplace. Der Operator ist konservativ: Was eine Zelle abgibt,
  // bekommen die Nachbarn - ueber das ganze Feld summiert aendert sich nichts.
  float left = texture(uState, uv - vec2(texel.x, 0.0)).r;
  float right = texture(uState, uv + vec2(texel.x, 0.0)).r;
  float down = texture(uState, uv - vec2(0.0, texel.y)).r;
  float up = texture(uState, uv + vec2(0.0, texel.y)).r;
  float laplacian = left + right + down + up - 4.0 * nutrient;
  nutrient += uDiffusion * uDt * laplacian;

  // --- Kopplung 1 und Wachstum -------------------------------------------
  // Michaelis-Menten in beiden Faktoren, dazu eine Dichtegrenze. Etablierte
  // Operatoren, keine neue Numerik (Exposé 7.3).
  float lightFactor = uLight / (uLight + uLightHalf);
  float nutrientFactor = nutrient / (nutrient + uNutrientHalf);
  float density = 1.0 - producer / uMaxDensity;
  float growth = uGrowthRate * lightFactor * nutrientFactor * producer * max(density, 0.0) * uDt;

  // Es kann nicht mehr wachsen, als an Naehrstoff da ist. Ohne diese Klammer
  // entstuende bei knappem Vorrat Biomasse aus dem Nichts - und die
  // Massenbilanz wuerde das zu Recht als unerklaerte Masse melden.
  growth = min(growth, max(nutrient, 0.0));

  nutrient -= growth;
  producer += growth;

  // --- Sterben und Remineralisierung -------------------------------------
  // Der geschlossene Kreislauf. Bei uRemineralization = 1.0 verlustfrei.
  float death = min(producer, uDeathRate * producer * uDt);
  producer -= death;
  nutrient += death * uRemineralization;

  // --- Kopplung 2: flaechiger Eintrag aus dem Niederschlag ---------------
  float rainfall = uInputRate * uNutrientInput * uDt;
  nutrient += rainfall;
  inflowAcc += rainfall;

  // --- Kopplung 6: punktuelle Partikel aus dem Hochtonband ---------------
  if (uParticleAmount > 0.0) {
    vec2 delta = cell - uParticlePos;
    delta -= uResolution * round(delta / uResolution);
    float distance = length(delta);
    if (distance < uParticleRadius) {
      float falloff = 1.0 - distance / uParticleRadius;
      float particle = uParticleAmount * falloff * falloff;
      nutrient += particle;
      inflowAcc += particle;
    }
  }

  // --- Austrag: Sedimentation --------------------------------------------
  // Steht dem Eintrag gegenueber, damit die Gesamtmasse nicht monoton waechst.
  // Sie ist zugleich der "Zerfall" des Naehrstofffelds aus Exposé 6.2 - beides
  // waere derselbe Vorgang, und zwei getrennte Senken waeren doppelt gezaehlt.
  float sediment = max(nutrient, 0.0) * uSedimentationRate * uDt;
  nutrient -= sediment;
  outflowAcc += sediment;

  // --- Refugium ----------------------------------------------------------
  // Garantierter Mindestvorrat (Risiko 1). Der Eingriff wird als Eintrag
  // gebucht statt stillschweigend zugegeben: Sonst waere er unerklaerte Masse,
  // und die Bilanz wuerde ihn - zu Recht - als Drift melden.
  if (nutrient < uRefugeFloor) {
    inflowAcc += uRefugeFloor - nutrient;
    nutrient = uRefugeFloor;
  }

  fragColor = vec4(max(nutrient, 0.0), clamp(producer, 0.0, uMaxDensity), inflowAcc, outflowAcc);
}
