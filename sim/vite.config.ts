import { defineConfig } from "vite";

// Bewusst ohne Plugins und ohne Rendering-Bibliothek: WebGL2 direkt.
// Begruendung siehe Expose 7.2 - im Dauerbetrieb gut beherrschbar, laeuft auf
// integrierter wie dedizierter AMD-Grafik, benoetigt kein CUDA.
//
// GLSL-Quellen werden ueber Vites eingebautes `?raw` als Text geladen; ein
// Shader-Plugin waere eine zusaetzliche Abhaengigkeit ohne Gegenwert.
export default defineConfig({
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    target: "es2022",
    // Quellkarten auch im Build: Ein Absturz nach drei Wochen Laufzeit muss
    // auswertbar sein.
    sourcemap: true,
  },
});
