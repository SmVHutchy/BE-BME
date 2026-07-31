"""Chronikpipeline — das Logbuch der Welt.

Nimmt ein vom Regeldetektor erkanntes Ereignis samt Kennzahlen entgegen und
laesst daraus einen kurzen Logbucheintrag formulieren. Der Eintrag geht nach
SQLite und wird ueber GET /chronicle ausgeliefert.

Das Sprachmodell steht AUSSERHALB der Welt und beschreibt sie. Es erkennt keine
Ereignisse, es entscheidet nichts im Oekosystem, und es schreibt nie in den
Simulationszustand - in keiner Richtung, auch nicht "nur zum Ausgleichen".
Abgrenzung zu Park et al. 2023 (Expose 3.4).

Zwei Implementierungen hinter dem Interface `ChronicleBackend`, umschaltbar
ueber chronicle.backend in config/params.yaml, ohne Codeaenderung:

    SingleChronicle   ein einziger Modellaufruf mit striktem Prompt, ohne
                      Framework. PFLICHT-RUECKFALLEBENE.
    TwoStepChronicle  zwei schlichte httpx-Aufrufe nacheinander, ohne
                      Framework - `chronicler` formuliert (identisch zu
                      SingleChronicle), `verifier` prueft jede Aussage gegen
                      die uebergebenen Zahlen und korrigiert oder verwirft,
                      was nicht belegt ist.

Urspruenglich war fuer den zweiten Weg CrewAI vorgesehen. Gestrichen, weil das
Expose Agenten nur zweimal nennt, beide Male als Abgrenzung (Expose 3.4 und 5,
"kein Multi-Agenten-Dialogsystem") - die Zwei-Rollen-Idee bleibt, das Framework
faellt weg.

Warum die Rueckfallebene Pflicht ist: Zwei Rollen bedeuten zwei Modellaufrufe
pro Eintrag. Auf der Zielhardware (Mini-PC mit AMD-APU) kann das zu langsam
werden. Die Chronik ist im Expose Pflichtumfang, der zweistufige Weg nicht.

Das Modell laeuft lokal ueber einen OpenAI-kompatiblen Endpunkt. Kein
Cloud-Dienst, kein Netzverkehr auf diesem Pfad.
"""
