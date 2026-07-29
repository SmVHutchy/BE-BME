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

    SingleChronicle  ein einziger Modellaufruf mit striktem Prompt, ohne
                     Framework. PFLICHT-RUECKFALLEBENE.
    CrewChronicle    CrewAI Flow (@start/@listen/@router) mit genau zwei
                     Pflicht-Agenten - `chronicler` formuliert, `verifier`
                     prueft jede Aussage gegen die uebergebenen Zahlen und
                     verwirft, was nicht belegt ist. Ein dritter `editor` ist
                     optional und standardmaessig aus.

Warum die Rueckfallebene Pflicht ist: Zwei Agenten bedeuten zwei Modellaufrufe
pro Eintrag. Auf der Zielhardware (Mini-PC mit AMD-APU) kann das zu langsam
werden. Die Chronik ist im Expose Pflichtumfang, CrewAI nicht.

Das Modell laeuft lokal ueber einen OpenAI-kompatiblen Endpunkt. Kein
Cloud-Dienst, kein Netzverkehr auf diesem Pfad.
"""
