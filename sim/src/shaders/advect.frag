#version 300 es
// Masseerhaltende Advektion (Reintegration Tracking).
//
// Der erste Entwurf war semi-lagrangesch: Je Zielzelle wurde rueckwaerts
// gesampelt, woher die Masse kaeme. Das ist der Lehrbuchoperator, aber er ist
// NICHT konservativ - die bilineare Interpolation glaettet, und ueber Millionen
// Ticks laeuft die Bilanz weg. Gemessen wurden 4,5 % unerklaerte Masse ueber
// sieben Welttage bei 2 % Toleranz (docs/annahmen.md A12).
//
// Reintegration Tracking dreht die Richtung um. Jede Quellzelle verteilt ihre
// Masse mit bilinearen Gewichten auf die vier Zellen um ihren Zielort. Was eine
// Zelle abgibt, kommt vollstaendig woanders an - die Summe ueber das Feld
// bleibt exakt erhalten, unabhaengig vom Stroemungsfeld.
//
// Im Fragment-Shader laesst sich nicht streuen (kein atomares Schreiben),
// deshalb die Gather-Fassung: Je ZIELzelle wird ueber die 3x3-Nachbarschaft
// der Quellzellen summiert, wieviel von deren Masse hier landet. Das ist
// dasselbe Ergebnis, solange die Verschiebung je Schritt unter einer Zelle
// bleibt - bei rund 0,21 Zellen gilt das mit grossem Abstand.
//
// Das Verfahren stammt aus Flow-Lenia, das Expose 3.2 bereits als Grundlage
// fuehrt. Es loest zugleich ein Gestaltungsproblem: Dieselbe Dissipation, die
// Masse verliert, verwischt die Raender zwischen den Kolonien
// (docs/lookdev.md).
//
// Bewegt werden nur die beiden PHYSIKALISCHEN Kanaele (Naehrstoff, Biomasse).
// Die Bilanzkanaele bleiben ortsfest: Sie zaehlen, wieviel an dieser Stelle
// ein- und ausgetragen wurde, und duerfen nicht mitstroemen - sonst waere die
// Bilanz selbst der Drift ausgesetzt, die sie messen soll.

out vec4 fragColor;

uniform sampler2D uState;      // R=Naehrstoff  G=Biomasse  B=Eintrag  A=Austrag
uniform sampler2D uVelocity;
uniform vec2 uResolution;
uniform float uDt;             // dt_eff = dt_base * rate
uniform float uDissipation;

/** Zellkoordinate auf dem Torus - die Welt hat umlaufende Raender. */
ivec2 wrapCell(ivec2 cell) {
  ivec2 size = ivec2(uResolution);
  return ((cell % size) + size) % size;
}

void main() {
  ivec2 target = ivec2(gl_FragCoord.xy);
  vec2 gathered = vec2(0.0);

  // Ueber die neun moeglichen Quellzellen. Weiter kann nichts herkommen,
  // solange die Verschiebung unter einer Zelle bleibt.
  for (int dy = -1; dy <= 1; dy++) {
    for (int dx = -1; dx <= 1; dx++) {
      ivec2 source = wrapCell(target + ivec2(dx, dy));
      vec2 sourceUv = (vec2(source) + 0.5) / uResolution;

      vec2 velocity = texture(uVelocity, sourceUv).xy;
      vec2 shift = velocity * uDt;
      // Sicherheitsklammer. Wuerde die Verschiebung eine Zelle ueberschreiten,
      // reichte die 3x3-Nachbarschaft nicht mehr und Masse ginge unbemerkt
      // verloren. Eine gebremste Stroemung ist das kleinere Uebel - und der
      // Fall ist bei den ausgelieferten Parametern rund fuenfmal entfernt.
      shift = clamp(shift, vec2(-1.0), vec2(1.0));

      // Wohin diese Quellzelle zielt, relativ zur Zielzelle.
      vec2 landing = vec2(source) + shift - vec2(target);
      // Auf dem Torus den kuerzesten Weg nehmen.
      landing -= uResolution * round(landing / uResolution);

      // Bilinearer Anteil, der in der Zielzelle landet: Ueberlappung des um
      // `landing` verschobenen Einheitsquadrats mit dieser Zelle.
      vec2 overlap = max(vec2(0.0), 1.0 - abs(landing));
      float weight = overlap.x * overlap.y;
      if (weight <= 0.0) continue;

      gathered += texture(uState, sourceUv).rg * weight;
    }
  }

  // Die Gewichte einer Quellzelle summieren sich exakt zu 1, das Feld ist damit
  // masseerhaltend. uDissipation steht auf 1.0; jeder kleinere Wert waere ein
  // bewusster Austrag und muesste bilanziert werden.
  vec4 here = texture(uState, (vec2(target) + 0.5) / uResolution);
  fragColor = vec4(gathered * uDissipation, here.ba);
}
