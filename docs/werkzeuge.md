# Werkzeuge

Welche Agenten-Werkzeuge in diesem Projekt eingesetzt werden, und nach welchem
Maßstab über neue entschieden wird.

---

## Warum dieses Dokument existiert

Ein *Skill* ist keine Bibliothek, sondern **Anweisungstext, den der Agent
befolgt**. Ihn zu installieren heißt, jemand Fremdes einen Teil des Prompts
schreiben zu lassen.

In diesem Repository ist das kein abstraktes Risiko. Es gibt sieben nicht
verhandelbare Regeln ([`CLAUDE.md`](../CLAUDE.md)), und ein beiläufiger Satz in
einem fremden Skill — „nutze Subagenten für Teilaufgaben", „ergänze Telemetrie",
„setze sinnvolle Standardwerte" — kann eine siebte Kopplung einführen, einen
Cloud-Aufruf auf den Chronikpfad legen, Zahlenwerte am Config-Weg vorbei in den
Code bringen oder die laut Exposé §6.5 offene Interaktionsform stillschweigend
festlegen.

Auffallen würde das frühestens in der Verteidigung. Deshalb die Regel unten.

---

## Der Prüfmaßstab

Bevor ein Skill oder Plugin aktiviert wird, muss es alle fünf Punkte erfüllen.

**1. Herkunft.** Nur Erstanbieter (`author: Anthropic`) oder ein Hersteller für
sein eigenes Produkt. Verzeichnisseiten wie skillsclaude.org,
claudemarketplaces.com oder skillsmp.com sind **kein** Herkunftsnachweis —
sie spiegeln GitHub, und Auszeichnungen wie „trust-graded" sind kein Audit,
sondern Suchmaschinenoptimierung.

**2. Was es beiträgt.** Reine Werkzeuge (`lspServers`, MCP-Server) sind
unbedenklich: Sie liefern Funktionen, keinen Anweisungstext. Alles mit
`skills/`, `commands/` oder Hooks wird **vollständig gelesen**, bevor es
aktiviert wird — mitgelieferte Skripte ebenso.

**3. Gegen die sieben Regeln geprüft.** Fordert es Subagenten? Cloud-Aufrufe?
Nennt es feste Zahlenwerte als „Best Practice"? Setzt es Sprach- oder
Anwesenheitserkennung voraus? Dann nicht.

**4. Pflege.** Letzter Commit, offene Issues, erkennbare Versionierung. Ein
Werkzeug, das über die sechs Monate Bearbeitungszeit verwaist, ist eine
Altlast.

**5. Im Zweifel nicht.** Der Nutzen eines Skills wiegt selten das Risiko einer
stillen Regelverletzung in einer Abschlussarbeit auf.

### Bereits geprüft und abgelehnt

Stand 30.07.2026, recherchiert über die einschlägigen Sammlungen:

| Kandidat | Grund der Ablehnung |
|---|---|
| `great_cto` | Orchestriert sieben Subagenten. Arbeitet direkt gegen Risiko 7 (Scope Creep frisst die Feldstudie). |
| `overkill` | Schlägt systematisch „fortgeschrittenere Alternativen" vor — Scope Creep als Werkzeug. |
| `software-architecture`, `subagent-driven-development` | Setzen Subagenten und Architekturmuster voraus, die dieses Projekt nicht braucht. Kriterium 1 zusätzlich unerfüllt. |
| `anydesign` | Sachlich interessant für das Look-Development, aber Einzelmaintainer ohne Audit. Kriterium 1 unerfüllt. Erneut prüfbar, wenn Monat 1 es tatsächlich verlangt. |

---

## Eingesetzt

### Sprachserver (eingerichtet am 30.07.2026)

Beide aus `anthropics/claude-plugins-official`, `author: Anthropic`. Im
Marketplace-Manifest deklarieren sie **ausschließlich `lspServers`** — keine
Skills, keine Commands, keine Hooks. Sie steuern damit keinerlei Anweisungstext
bei und erfüllen Kriterium 2 im engsten Sinn.

| Plugin | Server | Deckt ab |
|---|---|---|
| `typescript-lsp` | `typescript-language-server` 5.3.0 | `sim/` |
| `pyright-lsp` | `pyright-langserver` 1.1.411 | `core/` |

Installation:

```bash
npm install -g typescript-language-server typescript
uv tool install pyright
```

Pyright bewusst über `uv` statt `npm -g`: `uv` ist ohnehin das Werkzeug dieses
Projekts, und Pyright ist Entwicklungswerkzeug — es gehört nicht in
`core/pyproject.toml`, wo es als Laufzeitabhängigkeit erschiene.

> **Stolperstelle, hier aufgetreten:** npm war auf dem Entwicklungsrechner auf
> `C:\Users\liam\.npm-global` umkonfiguriert, dieses Verzeichnis stand aber
> nicht im PATH. Damit war *jedes* global installierte npm-Paket unerreichbar,
> nicht nur dieses. Der Pfad wurde dem User-PATH ergänzt.

Der Nutzen ist konkret: Beim Umbau des Shader-Uniform-Satzes oder der
Pydantic-Config-Modelle zeigt typbewusste Navigation sofort, welche Stellen
brechen. In Phase 2 fiel das mehrfach erst beim Programmstart auf.

### Vorhandene Skills, nach Arbeitspaket

Damit nicht extern gesucht wird, was ohnehin bereitsteht:

| Arbeitspaket | Skill |
|---|---|
| Look-Development (Monat 1) | `design:design-critique`, `design:design-system`, `anthropic-skills:frontend-design` |
| Anzeige und Overlay | `design:accessibility-review`, `design:ux-copy`, `design:design-handoff` |
| **Studienmaterial (Monat 3)** | **`design:user-research`** — Leitfaden, Tagebuchstudie, Einwilligung |
| **Auswertung (Monat 5)** | **`design:research-synthesis`** — thematische Codierung, Verdichtung zu Mustern |
| Diagramme für die Arbeit | `dataviz` |
| Codepflege | `simplify`, `/code-review`, `/security-review` |
| Abgabe, Transkripte | `anthropic-skills:docx`, `anthropic-skills:pdf`, `anthropic-skills:xlsx` |
| Kapitelentwürfe | `anthropic-skills:doc-coauthoring` |

Die beiden hervorgehobenen sind für die Arbeit die wertvollsten und bisher
ungenutzt: Sie decken genau den Bereich ab, den Exposé §3.6 noch als
„Methodenliteratur zur qualitativen Auswertung: noch zu recherchieren" führt.
Sie ersetzen die Literatur nicht — aber sie strukturieren Leitfaden, Codierung
und Verdichtung, und das ist der Teil von §8, der sonst am Ende unter Zeitdruck
entsteht.
