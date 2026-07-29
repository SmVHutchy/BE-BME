# Arbeitsregeln für dieses Repository

Projektkontext: [`PLAN.md`](PLAN.md). Verbindliche Spezifikation:
[`docs/expose.md`](docs/expose.md) — bei jedem Konflikt gewinnt das Exposé.

---

## Die harten Regeln

Diese sieben Punkte sind nicht Stilfragen. Jeder von ihnen entspricht einer
Festlegung im Exposé; wer einen davon aufhebt, ändert den Gegenstand der Arbeit.

### 1. Eine Eingangsgröße, ein Angriffspunkt

Sechs Eingangsgrößen, sechs Angriffspunkte, keine Überlappung
([`docs/mapping.md`](docs/mapping.md)). Der Grund ist Zuschreibbarkeit: Sobald
mehrere Größen auf dieselbe Stelle wirken, entsteht ein diffuses Gesamtwackeln,
in dem der Betrachter keine Ursache mehr erkennen kann.

**Keine siebte Kopplung.** Luftfeuchte, Luftdruck, Tageslänge, Mondphase sind
ausdrücklich nicht vorgesehen.

### 2. Kein Sprachmodell im Simulationstakt

Die Simulation läuft mit 30–60 Hz über Wochen. Ein Modellaufruf darin ist weder
latenzverträglich noch reproduzierbar.

### 3. Kein Sprachmodell in der Ereigniserkennung

Der Detektor ist reines Python: Schwellenwerte auf Zeitreihen, deterministisch,
testbar. Das Exposé steht und fällt damit, dass keine Ereignisse beschrieben
werden, die nie stattgefunden haben (§6.4). Das Modell erhält das **bereits
erkannte** Ereignis samt Kennzahlen und formuliert daraus einen Text.

### 4. Der Chronikpfad liest, er greift nicht ein

Kein Schreibzugriff auf den Simulationszustand — in keiner Richtung, auch nicht
„nur zum Ausgleichen". `core` kann `sim` ausschließlich über `env` und `pulse`
beeinflussen, und das sind die sechs Kopplungen.

Keine Agenten als Bewohner der Welt: Kein Agent repräsentiert einen Organismus,
keiner entscheidet im Ökosystem. Die Agenten stehen außerhalb und beschreiben
(Abgrenzung zu Park et al. 2023, Exposé §3.4).

### 5. Kein Netzverkehr auf dem Chronikpfad

Das Modell läuft lokal über einen OpenAI-kompatiblen Endpunkt, Modellname aus
der Config. Keine Cloud-LLMs. Ebenso verlässt kein Audiosignal das Gerät
(§7.5).

### 6. Nichts CUDA-Abhängiges

Entwicklungshardware ist eine AMD RX 7600 XT, Zielhardware ein Mini-PC mit
AMD-APU. Alles läuft über OpenGL/Vulkan bzw. WebGL2.

### 7. Keine Magic Numbers

Es gibt keinen Zahlenwert im Shader, im Detektor oder im Mapping, der nicht aus
[`config/params.yaml`](config/params.yaml) stammt. In der Arbeit muss jeder
Parameter dokumentiert und begründet werden. Neue Parameter kommen **mit** einer
begründenden Kommentarzeile in die Config, nicht als Literal in den Code.

---

## Die offene Entscheidung: Interaktionsform

Die Form, in der Bewohner mit dem Objekt in Kontakt treten — Sprachinteraktion
(A), Anwesenheitserkennung (B) oder beides (C) — ist laut Exposé §6.5
**ausdrücklich offen** und fällt dokumentiert erst am Ende von Monat 1.

Sie darf auch nicht **implizit** festgelegt werden: nicht durch ein
Config-Feld, nicht durch ein Modul, nicht durch eine Vertragsnachricht, nicht
durch eine Schnittstelle, die nur eine der drei Optionen bedienen kann.

**Wenn eine Stelle begegnet, an der die Entscheidung fallen müsste: anhalten und
fragen.** Nicht die naheliegende Variante wählen und weiterbauen.

Das Entwickler-Overlay aus Prototyp 0 ist keine Interaktionsform, sondern ein
Diagnosewerkzeug, und wird auch so benannt.

---

## Sprache

- **Code und Bezeichner:** Englisch. Auch Config-Schlüssel, Tabellenspalten,
  Commit-Nachrichten.
- **Dokumentation, Kommentare, `CLAUDE.md`:** Deutsch.
- **Chronikeinträge:** Deutsch (`chronicle.language`) — die Haushalte der
  Feldstudie lesen sie, und sie sind Gegenstand von TF3.

---

## Annahmen

Wo Information fehlt: **fragen**. Wo eine Annahme getroffen wird: im Code als
`# ANNAHME:` markieren **und** in [`docs/annahmen.md`](docs/annahmen.md)
eintragen, mit Begründung und Auflösungsweg.

Der Grund ist nicht Buchhaltung: Eine Annahme, die sechs Monate später niemand
mehr als Annahme erkennt, wird stillschweigend zur Tatsache — und ist in der
Verteidigung nicht mehr zu halten.

---

## Tests

Nur dort, wo sie tragen. **Massenbilanz und Regeldetektor sind reine Funktionen
und werden getestet.** Den Shader nicht mit Testinfrastruktur zupflastern; er
wird über Zeitrafferläufe und die Massenbilanz geprüft, nicht über Unit-Tests.

Zur Massenbilanz: Geprüft wird der **Residualsaldo**, nicht die Konstanz der
Gesamtmasse. Niederschlag trägt Masse ein, Sedimentation trägt aus (§6.2) — die
Gesamtmasse *soll* sich ändern. Was nicht passieren darf, ist unerklärte Masse.

---

## Reproduzierbarkeit

`run.seed` + `config/params.yaml` + Wetter-Rohlog rekonstruieren einen Lauf
vollständig.

Daraus folgt für den Code:

- Zufall **ausschließlich** aus `seed` und `tick`. Nie aus Wanduhrzeit, nie aus
  Frame-Zeit, nie aus einem ungeseedeten RNG. Im Shader hash-basiertes Rauschen
  aus `(seed, tick, Position)`.
- Wetterdaten werden **roh** mitgeloggt, nicht nur interpoliert.
- Jeder Snapshot und jeder Lauf trägt den Hash der Config.

---

## Betrieb

Der Simulationstakt ist von der Bildrate entkoppelt — im Dauerbetrieb wird
deutlich langsamer getaktet als gerendert. Wer beides koppelt, macht die
Rückfallebene aus Risiko 3 (Takt senken statt Auflösung senken) unmöglich.

Der Zeitraffer (`sim.speed`, 1–100) muss **von Anfang an** funktionieren, nicht
nachgerüstet werden. Er ist im Exposé die Hauptgegenmaßnahme gegen Risiko 1.

---

## Vor jedem größeren Schritt

- **CrewAI:** Aktuelle API über Context7 holen (`resolve-library-id` →
  `query-docs`), bevor eine Zeile geschrieben wird. Die 1.x-Linie hat
  wöchentliche Releases; die Syntax nicht aus dem Gedächtnis schreiben.
  Bekannte Stolperstelle: CrewAI hat LiteLLM entfernt — lokale Endpunkte laufen
  über `LLM(..., custom_openai=True, base_url=...)`, nicht über ein
  `openai/`-Präfix.

  Vier Festlegungen, die beim Bau der Crew nicht verhandelbar sind:

  - **Telemetrie aus.** CrewAI sendet standardmäßig anonyme Nutzungsdaten.
    `CREWAI_DISABLE_TELEMETRY=true` und `OTEL_SDK_DISABLED=true` — sonst liegt
    Netzverkehr auf dem Chronikpfad (Regel 5).
  - **`memory=False`, keine `knowledge_sources`.** CrewAI-Memory nutzt ohne
    eigenen Embedder OpenAIs `text-embedding-3-large`, also einen Cloud-Aufruf.
    Unabhängig davon würde Memory frühere Einträge einmischen und damit die
    Garantie brechen, dass ein Eintrag nur die übergebenen Zahlen enthält.
  - **`Process.sequential`, nicht `hierarchical`.** Hierarchisch fügt einen
    Manager-LLM und damit einen dritten Modellaufruf hinzu — genau das, wogegen
    die Rückfallebene existiert.
  - **Guardrail vor Verifier.** Ob jede Zahl im Text in den übergebenen
    Kennzahlen vorkommt, prüft eine reine Python-Funktion über `guardrail` und
    `guardrail_max_retries` — deterministisch und testbar. Der `verifier`
    beurteilt danach die inhaltlichen Aussagen. Nicht umgekehrt: Was Python
    mechanisch prüfen kann, wird nicht einem Modell überlassen.
- **Python:** Projektlokal 3.13 über `uv`. Das systemweite 3.14 ist unbrauchbar,
  weil CrewAI `>=3.10,<3.14` verlangt.

---

## Rechtliches

Open-Meteo steht unter **CC BY 4.0 mit Attributionspflicht**. Die Attribution
gehört an zwei Stellen: [`README.md`](README.md) und das Overlay am Objekt.
Beim Umbau der Anzeige darf sie nicht verschwinden.

Keine Secrets im Repo. Auf diesem Pfad gibt es auch keine: Open-Meteo braucht
keinen Schlüssel, LM Studio läuft lokal.
