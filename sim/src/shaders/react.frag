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
uniform uint uSedimentInterval;

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

  // Es kann nicht mehr wachsen, als an Naehrstoff VERFUEGBAR ist - und
  // verfuegbar ist nur, was ueber dem Refugium liegt.
  //
  // DAS IST DAS REFUGIUM (Risiko 1), und es wirkt hier als ENTZUGSSCHUTZ.
  // Der erste Entwurf hat es stattdessen als Zufuhr gebaut: Faellt eine Zelle
  // unter den Mindestwert, wurde sie aufgefuellt. Das fuellt sie in JEDEM Tick
  // erneut, und wenn die Produzenten sie sofort wieder leerzehren, ist es eine
  // unbegrenzte Naehrstoffquelle. Gemessen ueber sieben Welttage: 163.817 von
  // 165.562 Eintrag kamen daher - 98,9 %, waehrend der Regen 1.746 beitrug.
  // Die Gesamtmasse stieg dadurch auf das 2,46-fache und der geschlossene
  // Stoffkreislauf aus Expose 6.2 war ausgehebelt (docs/annahmen.md A12).
  //
  // So herum bleibt die Zusage erhalten - keine Flaeche faellt dauerhaft tot -
  // ohne dass ein Gramm Masse entsteht.
  growth = min(growth, max(nutrient - uRefugeFloor, 0.0));

  // KOMPENSIERTE UEBERTRAGUNG. Nicht der gewuenschte Betrag wird gutgeschrieben,
  // sondern der tatsaechlich abgegangene.
  //
  // Der Grund ist float32. Der Naehrstoff liegt bei rund 0,4, die Biomasse bei
  // 0,06, und `growth` ist winzig. Der Abstand zweier darstellbarer Zahlen
  // betraegt bei 0,4 rund 3e-8 - ist `growth` kleiner, verschwindet der Abzug
  // beim Naehrstoff, waehrend die Gutschrift bei der Biomasse ankommt. Masse
  // aus dem Nichts, in jedem Tick, immer in dieselbe Richtung.
  //
  // Gemessen: Das Residuum wuchs linear mit 0,58 % je Welttag. Linear, nicht
  // wurzelfoermig - zufaellige Rundungsfehler waeren mit der Wurzel der
  // Schrittzahl gewachsen. Genau diese Linearitaet hat den systematischen Term
  // verraten (docs/annahmen.md A12).
  float nutrientAfterGrowth = nutrient - growth;
  float actualGrowth = nutrient - nutrientAfterGrowth;
  nutrient = nutrientAfterGrowth;
  producer += actualGrowth;

  // --- Sterben und Remineralisierung -------------------------------------
  // Der geschlossene Kreislauf. Bei uRemineralization = 1.0 verlustfrei -
  // und mit derselben Kompensation wie oben, hier in der Gegenrichtung.
  float death = min(producer, uDeathRate * producer * uDt);
  float producerAfterDeath = producer - death;
  float actualDeath = producer - producerAfterDeath;
  producer = producerAfterDeath;
  nutrient += actualDeath * uRemineralization;

  // --- Kopplung 2: flaechiger Eintrag aus dem Niederschlag ---------------
  // Kompensiert wie oben: gebucht wird, was tatsaechlich ankam.
  float rainfall = uInputRate * uNutrientInput * uDt;
  float nutrientAfterRain = nutrient + rainfall;
  inflowAcc += nutrientAfterRain - nutrient;
  nutrient = nutrientAfterRain;

  // --- Kopplung 6: punktuelle Partikel aus dem Hochtonband ---------------
  if (uParticleAmount > 0.0) {
    vec2 delta = cell - uParticlePos;
    delta -= uResolution * round(delta / uResolution);
    float distance = length(delta);
    if (distance < uParticleRadius) {
      float falloff = 1.0 - distance / uParticleRadius;
      float particle = uParticleAmount * falloff * falloff;
      float nutrientAfterParticle = nutrient + particle;
      inflowAcc += nutrientAfterParticle - nutrient;
      nutrient = nutrientAfterParticle;
    }
  }

  // --- Austrag: Sedimentation --------------------------------------------
  // Steht dem Eintrag gegenueber, damit die Gesamtmasse nicht monoton waechst.
  // Sie ist zugleich der "Zerfall" des Naehrstofffelds aus Exposé 6.2 - beides
  // waere derselbe Vorgang, und zwei getrennte Senken waeren doppelt gezaehlt.
  // Auch die Sedimentation greift das Refugium nicht an - sonst waere die
  // Zusage nach einigen Wochen doch aufgezehrt, nur langsamer.
  //
  // Kompensiert, und hier wiegt es am schwersten: Die Sedimentation entzieht je
  // Tick rund 5,7e-9, waehrend der float32-Abstand bei einem Naehrstoffwert von
  // 0,4 bei 3e-8 liegt. Der Abzug verschwindet also meist im Rundungsfehler,
  // waehrend der kleine Bilanzkanal den vollen Betrag bucht - Masse gilt als
  // ausgetragen und ist doch noch da. Das war der groesste verbliebene
  // Driftterm (docs/annahmen.md A12).
  //
  // Nur jeder N-te Tick traegt aus, dafuer mit dem N-fachen Betrag: Der Abzug
  // je Einzeltick laege sonst unter dem float32-Abstand und faende schlicht
  // nicht statt. Gleiche Gesamtwirkung, aber jeder Abzug kommt an.
  if (uSedimentInterval == 0u || uTick % uSedimentInterval == 0u) {
    float span = uSedimentInterval == 0u ? 1.0 : float(uSedimentInterval);
    float sediment = max(nutrient - uRefugeFloor, 0.0) * uSedimentationRate * uDt * span;
    float nutrientAfterSediment = nutrient - sediment;
    outflowAcc += nutrient - nutrientAfterSediment;
    nutrient = nutrientAfterSediment;
  }

  // --- Numerische Klammern, BILANZIERT -----------------------------------
  // Der urspruengliche Code schrieb hier schlicht max(nutrient, 0.0) und
  // clamp(producer, ...). Beides sind stille Massenquellen bzw. -senken, und
  // die Bilanz hat sie zu Recht als unerklaerte Masse angezeigt: 6,3 % nach
  // sieben Welttagen, mit steigender Tendenz, sobald die Gradienten steiler
  // wurden.
  //
  // Die explizite Diffusion kann an einem steilen Uebergang ueberschwingen und
  // eine Zelle kurz unter null druecken. Sie auf null zu heben ERZEUGT Masse -
  // ein Vorgang wie jeder andere, also gehoert er in den Eintrag.
  if (nutrient < 0.0) {
    inflowAcc += -nutrient;
    nutrient = 0.0;
  }

  // An der Dichteobergrenze wird BEWUSST NICHT geschnitten.
  //
  // Ein erster Versuch tat das und buchte den Ueberschuss als Austrag. Das war
  // falsch, und der Fehler ist lehrreich: Die masseerhaltende Advektion erhaelt
  // die Summe, verhindert aber keine LOKALE Konzentration - konvergente
  // Stroemung schiebt Masse zusammen, und das ist physikalisch richtig. Wer den
  // Ueberschuss dann abschneidet, loescht genau die Masse, die der neue
  // Operator gerade korrekt transportiert hat. Gemessen: Biomasse 5728 -> 55
  // binnen eines halben Welttages, waehrend der Austrag um denselben Betrag
  // stieg (docs/annahmen.md A12).
  //
  // `max_density` ist eine WACHSTUMSgrenze und wirkt bereits als solche, ueber
  // den Faktor (1 - producer/max_density) im Wachstumsterm oben. Laeuft eine
  // Zelle durch Advektion darueber, hoert sie auf zu wachsen und wird durch das
  // Sterben wieder abgebaut - ohne dass Masse verschwindet.
  //
  // Negative Werte sind etwas anderes: Sie sind numerisches Rauschen, kein
  // Transport, und muessen bilanziert werden.
  if (producer < 0.0) {
    inflowAcc += -producer;
    producer = 0.0;
  }

  fragColor = vec4(nutrient, producer, inflowAcc, outflowAcc);
}
