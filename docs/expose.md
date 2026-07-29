# Exposé zur Bachelorarbeit

**Verfasser:** Liam Moosburger, Matrikelnummer 3676280
**Studiengang:** Media Engineering (B-ME), TH Nürnberg Georg Simon Ohm
**Betreuung:** [noch zu klären]
**Geplanter Bearbeitungszeitraum:** September 2026 – Februar 2027
**Stand:** Juli 2026

---

## 1. Arbeitstitel

Drei Vorschläge, von nüchtern nach prägnant:

1. **Gestaltung und Evaluation eines umweltgekoppelten künstlichen Ökosystems für den häuslichen Dauerbetrieb**
2. **Mapping-Design für generative Ökosysteme: Von der Galerieinstallation zum Wohnraumobjekt**
3. **Langsames Bild — Ein künstliches Ökosystem im Bilderrahmen**

Für die Anmeldung wird Titel 1 vorgeschlagen; Titel 2 benennt den Beitrag präziser und eignet sich als Untertitel.

---

## 2. Motivation und Problemstellung

Künstliche Ökosysteme haben in der Medienkunst eine gut dokumentierte Tradition. Die einschlägigen Arbeiten — von *Interactive Plant Growing* (Sommerer & Mignonneau 1992) über *Galápagos* (Sims 1997) bis *Eden* (McCormack 2001) — wurden ausnahmslos für den Galerieraum entworfen. Dort beträgt die Verweildauer eines Besuchers Minuten. Die zentrale Gestaltungsfrage lautet entsprechend: *Wie fessle ich jemanden sofort?* Die Systeme sind darauf ausgelegt, in kurzer Zeit ein Maximum an Reaktion, Rückkopplung und sichtbarer Veränderung zu liefern.

Verlagert man dasselbe Objekt in einen Wohnraum, kehrt sich die Frage um. Ein Bild an der Wand wird nicht einmal fünf Minuten lang betrachtet, sondern über Monate hinweg tausendfach gestreift. Alles, was im Galerieraum funktioniert — schnelle Reaktion, direkte Rückmeldung, hohe visuelle Dichte — wird im Wohnraum binnen Tagen zur Belästigung oder, schlimmer, zur Tapete. Der Bewohner gewöhnt sich. Die entscheidende Größe ist nicht mehr die Erstwirkung, sondern die Habituation.

Genau an dieser Stelle besteht eine Lücke. Für den Galerieraum existiert ein etablierter Entwurfsraum; für den häuslichen Dauerbetrieb generativer Systeme existiert er nicht. Die vorliegende Arbeit adressiert diese Verschiebung nicht theoretisch, sondern durch Entwurf, Bau und Erprobung eines konkreten Objekts.

**Der Gegenstand.** Ein Bilderrahmen an der Wand, in dem ein künstliches Ökosystem aus Mikroorganismen in Echtzeit lebt: ein Nährstofffeld mit Diffusion und Zerfall, zwei trophische Ebenen (Produzenten und Konsumenten), Vererbung mit kleiner Mutation und ein Strömungsfeld, das alles mitträgt. Der Stoffkreislauf ist geschlossen — was stirbt, zerfällt in das Nährstofffeld zurück. Diese Anforderung ist keine technische Spielerei, sondern folgt zwingend aus der Fragestellung: nur ein geschlossener Kreislauf kennt keinen Endzustand und kann prinzipiell unbegrenzt laufen. Ein System, das nach drei Wochen in ein stabiles Muster oder in einen leeren Zustand fällt, kann die Frage nach dem Dauerbetrieb gar nicht erst beantworten.

Das System ist an seine reale Umgebung gekoppelt, und zwar über zwei streng getrennte Kanäle: einen **langsamen Klimakanal** (das echte Wetter des Standorts) und einen **schnellen Ereigniskanal** (Musik im Raum, ausschließlich als Pegel und Frequenzband). Diese Trennung ist der zentrale Gestaltungsbeitrag der Arbeit. Sie bewirkt, dass sich das Bild in zwei völlig unterschiedlichen Zeitmaßstäben verändert: über Stunden und Tage träge und unauffällig, in einzelnen Momenten kurz und sichtbar. Die Vermutung, die die Arbeit prüft, lautet: Erst diese Doppelstruktur macht ein Objekt über Wochen betrachtenswert, weil sie sowohl beiläufiges Wahrnehmen als auch gelegentliches Hinsehen bedient.

Ergänzt wird das System um eine **Erzählschicht**: Ein lokal laufendes Sprachmodell führt aus dem Simulationszustand ein Logbuch der Welt. Der Grund ist wahrnehmungspsychologischer Natur: Kausalität, die sich über Tage entfaltet — eine Variante setzt sich durch, eine Front wandert, eine Zone wird leergefressen — ist für den Betrachter schlicht unsichtbar. Er sieht am Dienstag ein Bild und am Freitag ein anderes, aber nicht den Zusammenhang. Die Chronik macht diesen Zusammenhang nachträglich zugänglich.

---

## 3. Stand der Forschung

### 3.1 ALife-Kunst

**Sommerer & Mignonneau** etablieren mit *Interactive Plant Growing* (1992) und *A-Volve* (1994) das Grundmuster: Das Publikum gestaltet Kreaturen mit, deren Geburt, Fortpflanzung und Evolution es beeinflusst. Die Interaktion ist unmittelbar und formend — der Besucher greift ein und sieht sofort das Ergebnis.

**Karl Sims** verschiebt in *Galápagos* (1997) den Fokus auf Selektion: Galeriebesucher evolvieren Kreaturen durch Auswahl, ästhetische Präferenz wird zur Fitnessfunktion. Der Mensch ist Selektionsdruck.

**Jon McCormack** verbindet in *Eden* (2001) beides mit dem Raum: Die physische Anwesenheit des Publikums, erfasst über Infrarotkameras, versorgt die virtuelle Welt mit Energie; die Kreaturen erzeugen Klänge, um Aufmerksamkeit anzuziehen. *Eden* ist der direkte Vorläufer der vorliegenden Arbeit und muss präzise abgegrenzt werden:

| | *Eden* (2001) | Diese Arbeit |
|---|---|---|
| Ort | Galerie | Wohnraum |
| Zeithorizont | Minuten pro Besucher | Wochen bis Monate |
| Rolle des Menschen | Energiequelle des Systems | Bewohner, nicht Ressource |
| Verhalten des Systems | wirbt aktiv um Aufmerksamkeit | fordert keine Aufmerksamkeit ein |
| Externe Kopplung | Anwesenheit | Wetter (langsam) + Klang (schnell), getrennt |
| Zeitliche Erschließung | keine | Chronik als Erzählschicht |

Der entscheidende Unterschied ist der Zielkonflikt: *Eden* optimiert auf Aufmerksamkeitsgewinnung, weil ein Galeriewerk ignoriert zu werden nicht überlebt. Ein Wohnraumobjekt, das um Aufmerksamkeit wirbt, wird abgeschaltet. Die vorliegende Arbeit untersucht den entgegengesetzten Entwurfsfall und leitet daraus eine andere Kopplungslogik ab.

### 3.2 Simulationsgrundlagen

**Lenia** (Chan 2018) zeigt als kontinuierlicher zellulärer Automat, dass aus wenigen kontinuierlichen Regeln über 400 lebensähnliche Muster emergieren. **Flow-Lenia** entwickelt den Ansatz masseerhaltend weiter und ist damit für die Anforderung eines geschlossenen Stoffkreislaufs unmittelbar einschlägig. **Reaction-Diffusion-Systeme** liefern die zweite Grundlage: Diffusion, Zerfall und lokale Reaktion als Kernoperatoren eines Feldes.

Abgrenzung: Beide Ansätze arbeiten in einem geschlossenen Regelsystem ohne äußere Eingaben und ohne trophische Struktur. Die vorliegende Arbeit übernimmt ihre Mechanik, ergänzt sie um zwei trophische Ebenen, Vererbung und externe Kopplung — und verlagert die Forschungsfrage von der Emergenz der Muster auf deren Gestaltung im Gebrauch.

### 3.3 Calm Technology und Ambient Displays

**Weiser & Brown** (1998) formulieren mit *The Coming Age of Calm Technology* das Prinzip, Information in der Peripherie der Aufmerksamkeit zu platzieren und nur bei Bedarf ins Zentrum treten zu lassen. **Wisneski, Ishii et al.** (1998) übersetzen dies mit *Ambient Displays* in konkrete Objekte; die Linie *Informative Art* verfolgt dasselbe mit bildhaften Mitteln.

Abgrenzung: Ambient Displays bilden in der Regel *eine* Datenquelle *lesbar* ab — der Aktienkurs, die Abfahrtszeit, der Stromverbrauch. Lesbarkeit ist dort das Entwurfsziel. Die vorliegende Arbeit bricht damit bewusst: Das Wetter soll nicht angezeigt, sondern verstoffwechselt werden. Der Betrachter muss die Kopplung nicht entschlüsseln können; er soll lediglich bemerken, dass das Bild mit draußen zusammenhängt. Ob und ab wann Bewohner diesen Zusammenhang überhaupt herstellen, ist eine der empirischen Fragen der Arbeit.

### 3.4 Ausdrückliche Abgrenzung

**Park et al.** (2023), *Generative Agents*, wird ausschließlich zur Abgrenzung herangezogen. Die vorliegende Arbeit verfolgt **keinen** Multi-Agenten-Dialogansatz. Das Sprachmodell ist kein Akteur innerhalb der Simulation, sondern ein Beobachter außerhalb; es hat keinerlei Einfluss auf den Simulationszustand und trifft keine Entscheidungen im System.

### 3.5 Datenquelle

**Open-Meteo** liefert stündlich aktualisierte Wetterdaten für Europa, benötigt keinen API-Schlüssel und ist für nichtkommerzielle Nutzung bis 10.000 Aufrufe täglich frei. Die Daten stehen unter CC BY 4.0 mit Attributionspflicht; die Attribution wird in der Dokumentation und am Objekt geführt. Der geplante Bedarf liegt bei 24 Aufrufen täglich.

### 3.6 Noch zu recherchieren

Für folgende Bereiche ist die Literaturrecherche zum Zeitpunkt dieses Exposés nicht abgeschlossen; es werden hier bewusst keine Quellen benannt, um keine unbelegten Angaben einzuführen:

- Habituation und Novelty-Effekt in der Mensch-Computer-Interaktion
- Langzeit- und In-the-wild-Feldstudien zu ambienten Displays
- Der Diskursstrang „Slow Technology"
- Methodenliteratur zur qualitativen Auswertung halbstrukturierter Interviews
- Ökologische Modellbildung (Räuber-Beute-Dynamik, Lotka-Volterra-Charakteristik)

---

## 4. Forschungsfrage und Zielsetzung

### Hauptfrage

> **Wie muss ein umweltgekoppeltes künstliches Ökosystem gestaltet sein, damit es im häuslichen Dauerbetrieb über mehrere Wochen wiederholt Aufmerksamkeit erhält, ohne sie einzufordern?**

Die Frage ist als Entwurfsfrage formuliert und in einem Satz beantwortbar: Die Antwort besteht aus einer begründeten und empirisch geprüften Menge von Gestaltungsregeln, im Kern der Trennung von langsamem Klimakanal und schnellem Ereigniskanal mit jeweils genau einem Angriffspunkt.

### Operationalisierung des Kernbegriffs

„Betrachtenswert bleiben" ist als Formulierung unscharf und wird für diese Arbeit in drei prüfbare Kriterien zerlegt:

1. **Zuwendung über Zeit** — Die im Tagebuch protokollierte, unaufgeforderte Zuwendung nimmt über den Studienzeitraum nicht monoton ab.
2. **Kein Störungserleben** — Das Objekt wird nicht als aufdringlich beschrieben und nicht abgeschaltet.
3. **Keine Zustandskonvergenz** — Der Systemzustand konvergiert technisch messbar nicht: Die Varianz der Biomasse-Zeitreihen im gleitenden Fenster bleibt über den gesamten Zeitraum oberhalb eines definierten Schwellenwerts, und die Massenbilanz driftet nicht aus einem festgelegten Korridor.

Kriterien 1 und 2 stammen aus der Feldstudie, Kriterium 3 aus der technischen Messung. Erst zusammen tragen sie die Hauptfrage.

### Teilfragen

**TF1 (Schwerpunkt Gestaltung).** Wie müssen Klimakanal und Ereigniskanal gegeneinander ausgelegt sein — in Zeitkonstante, Amplitude und Angriffspunkt —, damit Bewohner einen Zusammenhang zwischen Bild und Umgebung bemerken, ohne das Bild als Anzeige zu lesen?

**TF2 (Schwerpunkt Technik).** Unter welchen Bedingungen bleibt eine GPU-basierte Ökosystemsimulation mit geschlossenem Stoffkreislauf über mehrere Wochen in einem Zustandsraum, der weder in einen stabilen Endzustand noch in Auslöschung oder numerische Divergenz fällt?

**TF3 (Schwerpunkt Evaluation).** Welchen Beitrag leistet eine textuelle Chronik dafür, dass Bewohner langsame, über Tage verteilte Kausalität im System überhaupt wahrnehmen?

### Zielsetzung

Ergebnis der Arbeit sind zwei Dinge: erstens ein funktionsfähiges, im Dauerbetrieb erprobtes Artefakt, zweitens — und wissenschaftlich vorrangig — eine dokumentierte, aus Entwurf und Feldstudie abgeleitete Menge von Gestaltungsregeln für generative Systeme im häuslichen Dauerbetrieb. Das Artefakt ist Mittel der Erkenntnis, nicht Selbstzweck.

---

## 5. Abgrenzung: Was die Arbeit ausdrücklich nicht leistet

- **Kein Beitrag zur ALife-Grundlagenforschung.** Es wird keine neue Simulationsklasse entwickelt und nicht behauptet, Open-Ended Evolution im Sinne der ALife-Theorie zu erreichen. Es wird ein hinreichend offener Zustandsraum für den Betrachtungszeitraum von Wochen angestrebt, nicht mehr.
- **Keine ökologische Modellvalidierung.** Das System wird nicht gegen reale ökologische Daten geprüft. Maßstab ist Plausibilität im Erleben, nicht biologische Korrektheit.
- **Kein Multi-Agenten-Dialogsystem** (Abgrenzung zu Park et al. 2023). Das Sprachmodell beschreibt, es handelt nicht.
- **Keine Inhaltsanalyse von Audio.** Aus dem Audiosignal werden ausschließlich Pegel in zwei Frequenzbändern gewonnen. Es findet keine Spracherkennung auf diesem Pfad statt, es wird nichts gespeichert.
- **Keine statistisch belastbare Nutzerstudie.** Bei drei bis vier Haushalten sind keine Signifikanzaussagen möglich und werden nicht getroffen.
- **Kein Produkt.** Keine Serienfertigung, kein Businessplan, keine Kostenoptimierung, keine Fertigungsreife des Rahmens.
- **Kein Modelltraining.** Es werden ausschließlich vorhandene, lokal lauffähige Modelle eingesetzt.

---

## 6. Konzept

### 6.1 Das Objekt

Ein Displaypanel in einem tiefen Rahmen (Schattenfuge), hinter matter, entspiegelter Scheibe. Rechner und Verkabelung sitzen im Rahmen; nach außen führt ein einziges Kabel. Ein Umgebungslichtsensor passt die Helligkeit an das Raumlicht an — im Dauerbetrieb keine Nebensache, sondern die Voraussetzung dafür, dass das Objekt abends nicht als Lampe wirkt. Ein physischer Schalter trennt die Audioerfassung hardwareseitig.

[ANNAHME] Panelgröße und Format sind noch offen; angesetzt wird ein Panel im Bereich 24–27 Zoll, Ausrichtung nach Look-Development in Phase 1. Das Budget ist zu klären (siehe offene Punkte).

### 6.2 Die Simulation

Vier Komponenten, alle als Felder auf der GPU:

1. **Nährstofffeld** mit Diffusion, Zerfall und Remineralisierung.
2. **Zwei trophische Ebenen.** Produzenten wachsen aus Licht und Nährstoff; Konsumenten fressen Produzenten. Die Kopplung erzeugt räuber-beute-typische Schwingungen, die das System dauerhaft in Bewegung halten — der Hauptgrund, warum das Bild nicht zur Ruhe kommt.
3. **Vererbung mit kleiner Mutation.** Wenige Genwerte je Linie (Wachstumsrate, Fraßradius, Strömungswiderstand, Pigment) werden bei Fortpflanzung mit gaußschem Rauschen weitergegeben. Dies ist der einzige Mechanismus, der Woche 6 strukturell von Woche 1 unterscheidet.
4. **Strömungsfeld**, das alle Felder advektiv mitträgt.

**Geschlossener Stoffkreislauf — präzisiert.** Intern ist der Kreislauf verlustfrei: Absterbende Biomasse geht vollständig in das Nährstofffeld zurück. Der Niederschlag trägt jedoch von außen Masse ein. Damit die Gesamtmasse nicht monoton wächst, wird dem Eintrag ein langsamer Austrag (Sedimentation) gegenübergestellt, der so parametrisiert ist, dass die Gesamtmasse in einem definierten Korridor schwingt. Die Massenbilanz wird zur Laufzeit gemessen; sie ist gleichzeitig Stabilitätsmetrik (TF2) und Nachweis, dass der Kreislauf hält.

### 6.3 Die Kopplung — zwei Kanäle, jede Größe mit genau einem Angriffspunkt

| Kanal | Eingangsgröße | Quelle | Angriffspunkt in der Simulation | Zeitkonstante |
|---|---|---|---|---|
| Klima | Sonnenstand & Bewölkung | Open-Meteo | Lichtenergie *L* (Wachstum der Produzenten) | Stunden |
| Klima | Niederschlag | Open-Meteo | Eintrag in das Nährstofffeld | Stunden |
| Klima | Temperatur | Open-Meteo | globale Prozessgeschwindigkeit (Zeitschritt) | Stunden |
| Klima | Wind (Richtung, Stärke) | Open-Meteo | Grundströmung des Strömungsfelds | Stunden |
| Ereignis | Pegel Bassband | Audio | Impuls in das Strömungsfeld (lokale Wirbel) | Sekunden |
| Ereignis | Pegel Hochtonband | Audio | punktuelle Nährstoffpartikel | Sekunden |

**Die Entwurfsregel:** Jede Eingangsgröße greift an genau einer Stelle an, keine überlappt. Der Grund ist nicht Sparsamkeit, sondern Zuschreibbarkeit. Sobald mehrere Größen auf dieselbe Stelle wirken, entsteht ein diffuses Gesamtwackeln, in dem der Betrachter keine Ursache mehr erkennen kann — und die Kopplung damit ihren Zweck verliert. Sonnenstand und Bewölkung bilden hierbei bewusst gemeinsam eine einzige Größe *L*; das ist ein Angriffspunkt, kein zweiter.

Die beiden Kanäle unterscheiden sich in ihrer Zeitkonstante um etwa drei Größenordnungen. Genau diese Distanz macht sie im Erleben trennbar und ist die zu prüfende Kernannahme von TF1.

### 6.4 Die Erzählschicht

Ein Metrikdienst aggregiert den Simulationszustand fortlaufend in eine Zeitreihe (Biomasse je trophischer Ebene, Anzahl aktiver Linien, Median der Genwerte, Frontposition, räumliche Verteilung). Ein **regelbasierter** Detektor erkennt darin Ereignistypen über Schwellenwerte: Blüte, Kollaps, Aussterben einer Linie, Durchsetzung einer Variante, Wanderung einer Front, leergefressene Zone.

**Wichtig:** Die Ereigniserkennung leistet der Regeldetektor, nicht das Sprachmodell. Das Modell erhält ausschließlich das erkannte Ereignis samt Kennzahlen und Wetterlage und formuliert daraus einen kurzen Logbucheintrag. Diese Trennung ist bewusst gesetzt: Sie hält die Chronik reproduzierbar und schließt aus, dass Ereignisse beschrieben werden, die im System nie stattgefunden haben.

[ANNAHME] Register der Einträge: nüchtern-beobachtend, kein Ich-Erzähler der Welt. Wird im Look-Development geprüft.

### 6.5 Bewusst offene Entwurfsentscheidung: die Interaktionsform

Die Form, in der Bewohner mit dem Objekt in Kontakt treten, wird in diesem Exposé **nicht** festgelegt. Sie ist die zentrale Entwurfsentscheidung der Phase 1 und wird dort dokumentiert getroffen. Drei Optionen stehen zur Wahl:

**A — Reine Sprachinteraktion.** Der Bewohner fragt, das Objekt antwortet aus der Chronik.
*Dafür:* Die Chronik wird nur auf Abruf sichtbar; das Bild bleibt frei von Text. Nachfragen sind möglich („Was ist gestern passiert?").
*Dagegen:* Setzt ein dauerhaft aktives Mikrofon mit Wortverarbeitung voraus — datenschutzseitig die schwerste Variante. Erfordert eine vollständige lokale Sprachpipeline auf der Zielhardware. Widerspricht tendenziell dem Prinzip der Calm Technology, weil es eine explizite Gesprächshandlung verlangt.

**B — Reine Anwesenheitserkennung.** Nähe oder Verweilen vor dem Objekt verändert dessen Verhalten, etwa indem der jüngste Logbucheintrag eingeblendet wird.
*Dafür:* Kein Aufwand für den Bewohner, fügt sich in die Peripherie ein, technisch schlank, kein Mikrofon für die Interaktion nötig.
*Dagegen:* Keine Nachfragen möglich, die Chronik erreicht den Bewohner nur passiv. Anwesenheitssensorik ist datenschutzseitig ebenfalls erklärungsbedürftig, und Fehlauslösungen im Alltagsbetrieb sind wahrscheinlich.

**C — Beides.** Anwesenheit steuert die Aufmerksamkeitsstufe, Sprache erlaubt die Nachfrage.
*Dafür:* Deckt beide Zugänge ab.
*Dagegen:* Verdoppelt Implementierungs- und Evaluationsaufwand. Vor allem: Es lässt sich in einer Studie mit drei bis vier Haushalten nicht mehr trennen, welcher Kanal welche Wirkung erzeugt hat. Für die Aussagekraft der Arbeit ist das ein ernstes Problem.

**Entscheidungskriterien:** gemessene Latenz der Sprachpipeline auf der Zielhardware, Akzeptanz der Haushalte gegenüber einem Mikrofon (wird in der Rekrutierung abgefragt), Implementierungsaufwand gegenüber dem Restplan, und Trennschärfe der Evaluation. Die Entscheidung fällt am Ende von Monat 1 und wird im Methodenkapitel begründet.

---

## 7. Technische Umsetzung

### 7.1 Architektur

| Schicht | Aufgabe | Werkzeug |
|---|---|---|
| Simulationskern | Felder, Trophie, Vererbung, Advektion | GLSL-Fragment-Shader, Ping-Pong-FBOs |
| Umweltdienst | Open-Meteo abrufen, cachen, interpolieren | lokaler Dienst (TypeScript/Node) |
| Audiodienst | FFT, zwei Bänder, Hüllkurve, Normalisierung | lokal, nur Pegel verlassen das Modul |
| Metrik & Chronik | Zeitreihe, Regeldetektor, Formulierung | SQLite + kleines lokales Sprachmodell |
| Interaktion | gemäß Entwurfsentscheidung (A/B/C) | ggf. lokale STT/TTS |
| Betrieb | Autostart, Watchdog, Zustandssicherung | Systemdienst |

### 7.2 Plattformwahl

Primär **WebGL2 mit TypeScript** im Kioskbetrieb. Begründung: läuft auf integrierter wie dedizierter AMD-Grafik, ist im Dauerbetrieb gut beherrschbar, entspricht dem vorhandenen Kompetenzprofil und benötigt kein CUDA. **TouchDesigner** wird als Werkzeug für schnelles Look-Development in Phase 1 genutzt, aber nicht als Laufzeitplattform gesetzt. WebGPU (mit Compute-Shadern) wird nur dann herangezogen, wenn sich die Individuenverwaltung über Fragment-Shader als nicht praktikabel erweist; das erhöhte Stabilitätsrisiko im Wochenbetrieb spricht zunächst dagegen.

Sämtliche eingesetzten Werkzeuge laufen über OpenGL/Vulkan bzw. WebGL. **Keine CUDA-abhängige Software** (also weder ALIEN noch NVIDIA ACE), da die Entwicklungshardware eine AMD RX 7600 XT ist.

### 7.3 Anspruch an den Simulationskern

Der Kern verwendet ausschließlich etablierte, gut dokumentierte Operatoren: Laplace-Diffusion, semi-lagrangesche Advektion, schwellwertbasierte Wachstums- und Fraßregeln, gaußsches Mutationsrauschen. Es wird keine neue Numerik hergeleitet und kein mathematisch anspruchsvoller Kern konstruiert. Der Beitrag der Arbeit liegt im Mapping-Design und in der Evaluation, nicht in der Simulationsmathematik. Das ist eine bewusste Zuschneidung des Risikos.

### 7.4 Zielhardware und Dauerbetrieb

Entwicklung auf dem vorhandenen Rechner (Ryzen 7 5800X, RX 7600 XT 16 GB, 32 GB RAM). Für das Objekt ist ein Mini-PC mit AMD-APU vorgesehen. [ANNAHME] Die Simulation wird bei moderater Feldauflösung mit entkoppelter Simulations- und Bildrate (Simulationstakt deutlich unter der Bildrate) auf integrierter Grafik lauffähig sein; dies ist in Monat 1 zu verifizieren und ist der erste Meilenstein mit Abbruchrelevanz.

Das Sprachmodell wird quantisiert lokal ausgeführt (Größenordnung 1–8 Mrd. Parameter). Da Chronikeinträge asynchron und selten entstehen — im Minuten- bis Stundentakt —, ist die Generierungslatenz unkritisch. Anders bei Option A/C der Interaktionsform: Dort wird Latenz zum harten Kriterium, weshalb sie in die Entwurfsentscheidung eingeht.

**Für den Dauerbetrieb vorgesehen:** Watchdog mit automatischem Neustart; **periodische Sicherung des vollständigen Simulationszustands** auf Datenträger, damit ein Absturz nicht Wochen an Evolutionsgeschichte vernichtet (bei einem System, dessen ganzer Sinn die Geschichte ist, ist das kein Komfortmerkmal, sondern eine Kernanforderung); tägliches Health-Log mit Bildzeit, Speicherverbrauch, GPU-Temperatur, Massenbilanz und Neustartzähler.

### 7.5 Datenschutz

Ein dauerhaft betriebenes Mikrofon in einem Wohnraum ist begründungspflichtig. Vorgesehen sind:

- **Ausschließlich lokale Verarbeitung.** Kein Audiosignal verlässt das Gerät. Kein Cloud-Dienst auf diesem Pfad.
- **Keine Speicherung.** Es existiert kein Puffer über das FFT-Fenster hinaus. Aus dem Modul treten nur zwei Pegelwerte aus.
- **Physischer Stummschalter**, der die Erfassung hardwareseitig trennt, für die Bewohner sichtbar und jederzeit erreichbar.
- **Betrieb ohne Audiokanal möglich.** Fällt der Ereigniskanal weg, läuft das System auf dem Klimakanal weiter. Ob Haushalte davon Gebrauch machen, wird protokolliert und ist selbst ein Ergebnis.
- Informationsblatt und Einwilligung für alle Studienhaushalte. [noch zu klären: Vorgaben und Vorlagen der TH Nürnberg]

**Offener Punkt.** Die Projektbeschreibung nennt „Audio-Loopback". Loopback erfasst die Audioausgabe des eigenen Rechners und wäre datenschutzseitig unproblematisch — setzt aber voraus, dass das Objekt selbst die Musikquelle ist. In einem realen Haushalt kommt die Musik in aller Regel von einem anderen Gerät. Die realistische Variante ist daher ein Raummikrofon mit den oben genannten Einschränkungen. Diese Diskrepanz ist vor der Umsetzung zu entscheiden (siehe offene Punkte).

---

## 8. Evaluation

### 8.1 Methode

**In-the-wild-Feldstudie mit drei bis vier Haushalten.** Da nur ein Objekt existiert, laufen die Durchgänge nacheinander, je ein bis zwei Wochen. Erhoben werden:

1. **Kurztagebuch**, täglich wenige Minuten, drei feste Fragen: Wann habe ich hingesehen? Wann ist es mir gar nicht aufgefallen? Wurde es angesprochen (von mir, von Gästen)? Ergänzend freie Notizen bei auffälligen Beobachtungen.
2. **Halbstrukturiertes Interview** zum Abschluss (30–45 min) entlang eines Leitfadens: Erstwahrnehmung gegenüber späterer Wahrnehmung; Verlauf der Gewöhnung; ob und wann ein Zusammenhang zum Wetter oder zur Musik vermutet wurde und ob diese Zuschreibung zutraf; Rolle der Chronik; Störungserleben (Helligkeit, Unruhe, Geräusch); Wunsch nach Eingriffsmöglichkeit.
3. **Technische Dauermessung** über den gesamten Zeitraum von mindestens sechs Wochen: Laufzeitstabilität, Massenbilanz, Populationsmetriken, Neustarts, API-Ausfälle. Diese Messung beantwortet TF2 unabhängig von der Haushaltsstudie.

Auswertung qualitativ, thematisch codiert. [noch zu recherchieren: konkrete Methodenliteratur]

### 8.2 Warum keine Laborstudie

Eine Laborstudie wäre hier methodisch falsch, und zwar aus drei Gründen:

Erstens misst ein Labor die Erstwirkung. Genau die ist nicht der Gegenstand. Die Arbeit untersucht, was *nach* dem Neuigkeitseffekt passiert — ein Effekt, den eine Sitzung von dreißig Minuten nicht einmal streift.

Zweitens ist der Untersuchungsgegenstand konstitutiv an die reale Umgebung gebunden. Das echte Wetter des Standorts, echte Musik in echter Lautstärke, echte Wege durch den Raum. Im Labor müsste all das simuliert werden — womit man ein anderes Objekt untersucht als das gebaute.

Drittens ist die zentrale abhängige Größe die beiläufige, unaufgeforderte Zuwendung. Eine Laborsituation stellt Aufmerksamkeit her; sie kann daher nicht messen, ob Aufmerksamkeit von selbst entsteht.

**Grenzen der Methode, offen benannt.** Drei bis vier Haushalte erlauben keine verallgemeinerbaren Häufigkeitsaussagen. Der Anspruch ist ein anderer: Identifikation gestaltungsrelevanter Phänomene und Prüfung, ob die formulierten Entwurfsregeln im realen Betrieb tragen oder scheitern. Auch ein Scheitern wäre ein verwertbares Ergebnis.

---

## 9. Zeitplan

| Monat | Arbeitspakete | Meilenstein |
|---|---|---|
| **1 — September 2026** | Literaturrecherche abschließen; **Hardware sofort beschaffen** (Panel, Mini-PC, Rahmen, Sensorik — Lieferzeiten!); Lauffähigkeit auf Zielhardware verifizieren; Look-Development; Simulationskern (Nährstofffeld, Diffusion, Produzenten); **Entwurfsentscheidung Interaktionsform** | Entscheidung dokumentiert; Kern läuft 24 h stabil auf der Zielhardware; Hardware im Haus |
| **2 — Oktober 2026** | Konsumenten, Vererbung, Strömungsfeld; geschlossener Stoffkreislauf mit Massenbilanz; Klimakopplung (Open-Meteo); Audiokopplung; **Zeitraffer-Testläufe** (10–50-fache Simulationsgeschwindigkeit) | Alle sechs Kopplungen wirksam und dokumentiert; 7-Tage-Dauerlauf ohne Absturz; Mapping-Design schriftlich fixiert |
| **3 — November 2026** | Metrikdienst, Regeldetektor, Chronikschicht; Interaktionsschicht gemäß Entscheidung; **Rahmenbau und Montage**; Selbstversuch im eigenen Wohnraum (14 Tage); Studienmaterial (Leitfaden, Tagebuch, Einwilligung); Haushalte rekrutieren | Objekt fertig montiert und im Dauerbetrieb; Pilotdurchlauf abgeschlossen; fünf Haushalte zugesagt |
| **4 — Dezember 2026 bis Mitte Januar 2027** | Feldstudie sequentiell, drei bis vier Haushalte à ein bis zwei Wochen; Interviews führen und transkribieren; parallel Verschriftlichung der Kapitel 1–4 (Einleitung, Stand der Forschung, Konzept, Umsetzung) | Alle Durchgänge abgeschlossen, Interviews transkribiert; Kapitel 1–4 im Rohentwurf |
| **5 — Mitte Januar bis Februar 2027** | Auswertung und Codierung; Kapitel 5–7 (Evaluation, Diskussion, Fazit); Gesamtdurchsicht; Korrektorat; **zwei Wochen Puffer** | Abgabe |

**Anmerkungen zum Plan.** Der physische Aufbau ist mit vier Wochen in Monat 3 angesetzt, die Beschaffung liegt aber bereits in Woche 1 — Lieferzeiten sind der häufigste Grund, warum Hardwareprojekte kippen. Die Feldstudie überlappt bewusst mit dem Schreiben, da während der Durchgänge ohnehin Wartezeit entsteht. Die Weihnachtsferien fallen mitten in Monat 4; deshalb sollen mindestens zwei Durchgänge **vor** dem 20. Dezember abgeschlossen sein. Der Puffer am Ende ist ein echter Puffer und in keinem Arbeitspaket verplant.

---

## 10. Risiken und Gegenmaßnahmen

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| 1 | **Die Simulation kippt im Langzeitbetrieb** — alle Konsumenten sterben aus, oder eine Population explodiert und das Bild wird statisch. | Ab Monat 1 automatisierte **Zeitrafferläufe** mit 10–50-facher Geschwindigkeit: sechs Wochen Betrieb in wenigen Stunden testbar, lange bevor das Objekt gebaut ist. Zusätzlich Refugien mit garantiertem Mindestnährstoff, harte Obergrenzen für Populationsdichten und eine „Sporenbank", die eine ausgestorbene Ebene nach längerer Abwesenheit sanft wieder einträgt. Jeder solche Eingriff wird protokolliert und in der Arbeit ausgewiesen. |
| 2 | **Numerische Drift des Stoffkreislaufs** — die Advektion verliert oder erzeugt Masse, die Bilanz läuft über Wochen weg. | Massenbilanz als Laufzeitmetrik mit definiertem Korridor; masseerhaltende Advektion in Anlehnung an Flow-Lenia; bei Bedarf Renormalisierung pro Zeitschritt. Rückfallebene: gröberes Gitter mit halbiertem Zeitschritt. |
| 3 | **Zielhardware zu schwach** — Simulation und Sprachmodell laufen nicht gemeinsam auf dem Mini-PC. | Verifikation als allererster Meilenstein in Monat 1, nicht später. Rückfallebenen in dieser Reihenfolge: Feldauflösung reduzieren; Simulationstakt senken (bei einem bewusst langsamen System kaum sichtbar); kleineres Sprachmodell; im äußersten Fall Chronikgenerierung auf einem zweiten Rechner im Heimnetz, mit ausgewiesener Einschränkung der Autonomie des Objekts. |
| 4 | **Rahmenbau verzögert sich oder das Panel wird beschädigt.** | Beschaffung in Woche 1–2. Abgestufte Rückfallebene: gekaufter Schattenfugenrahmen statt Eigenbau, notfalls ein Monitor mit aufgesetztem Rahmenprofil. Die Forschungsfrage hängt an der Kopplung, nicht am Gehäusedetail — das muss im Zweifel als Erstes reduziert werden. |
| 5 | **Zu wenige Haushalte oder Abbruch während des Durchgangs.** | Fünf Haushalte für drei bis vier Plätze akquirieren. Mindestdauer je Durchgang auf sieben Tage reduzierbar. Im Notfall ersetzt der eigene Selbstversuch einen Haushalt, mit klar ausgewiesener methodischer Einschränkung. |
| 6 | **Datenschutzbedenken gegenüber dem Mikrofon.** | Der Ereigniskanal ist abschaltbar, das System läuft auf dem Klimakanal weiter. Akzeptanz wird bereits in der Rekrutierung abgefragt. Ein Haushalt, der abschaltet, liefert ein eigenes Ergebnis statt eines Datenausfalls. |
| 7 | **Scope Creep** — die Erzähl- und Interaktionsschicht wächst und frisst die Zeit der Feldstudie. | Verbindliches Stufenmodell: **Pflicht** sind Simulation, beide Kopplungen, Chronik als Text und die Feldstudie. **Kür** sind Sprachinteraktion, Anwesenheitserkennung und alles darüber hinaus. Die Grenze wird zu Beginn schriftlich mit dem Betreuer fixiert. |
| 8 | **Ausfall oder Änderung der Open-Meteo-Nutzungsbedingungen.** | Lokaler Cache der letzten 30 Tage; bei Ausfall Fortschreibung der letzten bekannten Werte, danach synthetisches Wetter aus historischen Daten. Der Ausfall ist damit nicht sichtbar, wird aber protokolliert. |

---

## 11. Literatur

> **Hinweis:** Es sind ausschließlich die im Projektkontext belegten Quellen aufgeführt. Die vollständigen bibliografischen Angaben (Seitenzahlen, Verlagsorte, DOI) sind vor Abgabe zu verifizieren und in der Literaturverwaltung zu vervollständigen; bei einzelnen Einträgen ist die Jahresangabe zu prüfen. Es wurde nichts ergänzt, was nicht belegt ist.

**Medienkunst / ALife**

- Sommerer, C.; Mignonneau, L. (1992): *Interactive Plant Growing*. [Installation]
- Sommerer, C.; Mignonneau, L. (1994): *A-Volve*. [Installation]
- Sims, K. (1997): *Galápagos*. [Installation]
- McCormack, J. (2001): *Eden: An Evolutionary Sonic Ecosystem*. [Publikationsangaben zu verifizieren]

**Simulation**

- Chan, B. W.-C. (2018): *Lenia — Biology of Artificial Life*. [Publikationsorgan und ggf. abweichendes Erscheinungsjahr der Zeitschriftenfassung zu verifizieren]
- *Flow-Lenia* — masseerhaltende Weiterentwicklung von Lenia. [Autoren, Jahr und Publikationsorgan noch zu recherchieren]
- Reaction-Diffusion-Systeme. [Referenzquelle noch zu bestimmen]

**Theoretischer Rahmen**

- Weiser, M.; Brown, J. S. (1998): *The Coming Age of Calm Technology*. [Jahresangabe gemäß Projektvorgabe; frühere Fassung möglicherweise 1996/97 — zu prüfen]
- Wisneski, C.; Ishii, H. et al. (1998): *Ambient Displays*. [vollständige Autorenliste und Publikationsangaben zu verifizieren]
- *Informative Art*. [Referenzquelle noch zu bestimmen]

**Abgrenzung**

- Park, J. S. et al. (2023): *Generative Agents*. [vollständige Autorenliste und Publikationsangaben zu verifizieren]

**Datenquelle**

- Open-Meteo. Wetterdaten unter CC BY 4.0, Attributionspflicht. Nichtkommerzielle Nutzung bis 10.000 Aufrufe täglich frei, kein API-Schlüssel erforderlich, stündliche Aktualisierung für Europa.

**Noch zu recherchieren** (vgl. Abschnitt 3.6): Habituation und Novelty-Effekt in der HCI; Langzeit-Feldstudien zu ambienten Displays; Slow Technology; Methodenliteratur zur qualitativen Auswertung; ökologische Modellbildung.
