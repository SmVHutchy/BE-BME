# Mapping-Design: sechs Eingangsgroessen, sechs Angriffspunkte

Dieses Dokument fuehrt den Nachweis der zentralen Entwurfsregel aus Exposé §6.3
und ist als Vorlage fuer das Umsetzungskapitel der Arbeit angelegt.

> **Die Regel.** Jede Eingangsgroesse greift an genau einer Stelle an, keine
> ueberlappt. Der Grund ist nicht Sparsamkeit, sondern **Zuschreibbarkeit**:
> Sobald mehrere Groessen auf dieselbe Stelle wirken, entsteht ein diffuses
> Gesamtwackeln, in dem der Betrachter keine Ursache mehr erkennen kann — und
> die Kopplung verliert ihren Zweck.

---

## Die Tabelle

| # | Kanal | Eingangsgroesse | Quelle | Angriffspunkt in der Simulation | Zeitkonstante | Config-Schluessel | Abbildung in | Anwendung in |
|---|---|---|---|---|---|---|---|---|
| 1 | Klima | Sonnenstand & Bewoelkung | Open-Meteo `shortwave_radiation` | Lichtenergie *L* — Wachstum der Produzenten | Stunden | `coupling.light` | `core` | `sim`, Produzenten-Shader |
| 2 | Klima | Niederschlag | Open-Meteo `precipitation` | Eintrag in das Naehrstofffeld | Stunden | `coupling.nutrient_input` | `core` | `sim`, Naehrstoff-Shader |
| 3 | Klima | Temperatur | Open-Meteo `temperature_2m` | globale Prozessgeschwindigkeit (Zeitschritt) | Stunden | `coupling.rate` | `core` | `sim`, Taktgeber |
| 4 | Klima | Wind (Richtung, Staerke) | Open-Meteo `wind_direction_10m`, `wind_speed_10m` | Grundstroemung des Stroemungsfelds | Stunden | `coupling.wind` | `core` | `sim`, Stroemungs-Shader |
| 5 | Ereignis | Pegel Bassband | Audio, Band `audio.band_low_hz` | Impuls in das Stroemungsfeld (lokale Wirbel) | Sekunden | `coupling.pulse_low` | `core` | `sim`, Stroemungs-Shader |
| 6 | Ereignis | Pegel Hochtonband | Audio, Band `audio.band_high_hz` | punktuelle Naehrstoffpartikel | Sekunden | `coupling.pulse_high` | `core` | `sim`, Naehrstoff-Shader |

Sechs Zeilen, sechs verschiedene Angriffspunkte, keiner doppelt. Zeile 4 und 5
wirken beide auf das Stroemungsfeld, aber an unterschiedlichen Stellen: Wind
setzt die **Grundrichtung des gesamten Felds**, der Bassimpuls setzt einen
**lokalen, abklingenden Wirbel**. Ebenso Zeile 2 und 6: Niederschlag ist ein
**flaechiger Eintrag**, der Hochtonpuls ein **punktuelles Partikel**. Diese
Unterscheidung ist nicht kosmetisch — sie ist der Grund, warum sich die beiden
Kanaele im Erleben trennen lassen.

---

## Warum Sonnenstand und Bewoelkung eine Groesse sind

Das Exposé fasst beide bewusst zu einer einzigen Groesse *L* zusammen: „das ist
ein Angriffspunkt, kein zweiter" (§6.3).

Die Umsetzung macht sich das zunutze. `shortwave_radiation` ist die
tatsaechliche Globalstrahlung am Boden — sie enthaelt die Sonnengeometrie
(Tageszeit, Jahreszeit, Breitengrad) und die Wolkendaempfung bereits gemeinsam.
Es ist deshalb **nicht** noetig, `cloud_cover` zusaetzlich abzurufen und zu
verrechnen; das waere Doppelzaehlung und faktisch ein zweiter Eingang auf
denselben Angriffspunkt.

Nebeneffekt, der zur Arbeit passt: Der Tagesgang entsteht dadurch von selbst und
in der richtigen Phase fuer den tatsaechlichen Standort, ohne dass irgendwo eine
Uhrzeit-Heuristik im Code steht.

---

## Zeitkonstanten: der Abstand ist der Entwurf

Die beiden Kanaele unterscheiden sich um etwa drei Groessenordnungen. Genau
diese Distanz macht sie im Erleben trennbar und ist die zu pruefende Kernannahme
von **TF1**. Sie ist in der Konfiguration direkt ablesbar:

| Kanal | Parameter | Wertebereich |
|---|---|---|
| Klima | `smoothing_minutes` | 20–90 Minuten |
| Ereignis | `decay_seconds` | 2–4 Sekunden |

Verhaeltnis rund 1 : 1000. Wer diese Werte einander annaehert, hebt den
Gestaltungsbeitrag der Arbeit auf — beide Kanaele verschmelzen dann zu einem.

---

## Der Sonderfall Zeitschritt

Auf den Zeitschritt wirken **zwei** Faktoren:

```
dt_eff = sim.dt_base * coupling.rate * sim.speed
```

Das sieht auf den ersten Blick wie ein Verstoss gegen die 1:1-Regel aus. Es ist
keiner, und die Unterscheidung gehoert festgehalten, weil sie sonst bei jeder
Durchsicht neu diskutiert wird:

- **`rate`** ist eine echte Kopplung. Sie stammt aus der Temperatur, ist Zeile 3
  der Tabelle und wirkt im Feldbetrieb.
- **`sim.speed`** ist der Zeitraffer — eine **Betriebsgroesse**, keine
  Umweltkopplung. Sie hat keine Quelle in der Umgebung des Objekts, sondern wird
  vom Entwickler gesetzt, um sechs simulierte Wochen in wenigen Stunden zu
  pruefen (Hauptgegenmassnahme gegen Risiko 1). Im Feldbetrieb steht sie
  konstant auf `1.0`.

Damit die Unterscheidung nachpruefbar bleibt und nicht nur behauptet ist, wird
`sim.speed` in jedem Health-Log-Eintrag und in jedem Snapshot mitgeschrieben.
Ein Abschnitt der Zeitreihe laesst sich so jederzeit daraufhin pruefen, ob er im
Zeitraffer entstanden ist.

---

## Abbildungskennlinien

Die Kennlinie ist Teil des Mapping-Designs, nicht Implementierungsdetail. Alle
Parameter stehen in `config/params.yaml` unter `coupling`.

| Kopplung | Kennlinie | Begruendung |
|---|---|---|
| `light` | linear, 0–900 W/m² → 0–1 | Die Globalstrahlung bringt ihren Tagesgang bereits mit; eine zusaetzliche Kruemmung wuerde ihn verzerren. |
| `nutrient_input` | Wurzel, 0–10 mm/h → 0–1 | Niederschlagsintensitaet ist stark rechtsschief. Linear abgebildet blieben normale Regenfaelle nahezu unsichtbar, und nur Starkregen waere ueberhaupt wahrnehmbar. |
| `rate` | Q10, Referenz 15 °C, geklammert auf 0.4–1.8 | Stoffwechselraten verdoppeln sich je 10 K — eine lehrbuchueblich etablierte Beziehung, kein selbst hergeleitetes Modell (Exposé §7.3). Die Klammern verhindern, dass ein Kaeltesturz das Bild einfriert oder ein Hitzetag die Numerik ueber die Stabilitaetsgrenze treibt. |
| `wind` | Richtung unveraendert; Betrag linear 0–40 km/h → 0–1 | Die Richtung wird in meteorologischer Konvention weitergereicht, damit der Wetterlog ohne Umrechnung mit der Quelle vergleichbar bleibt. |
| `pulse_low` / `pulse_high` | linearer Pegel ueber Schwelle, exponentielles Abklingen | Die Schwelle verhindert, dass Raumgrundrauschen das Bild dauerhaft in Bewegung haelt — ein Objekt, das staendig zuckt, wird abgeschaltet. |

---

## Was hier nicht steht

Es gibt keine siebte Zeile, und es wird keine geben. Kandidaten, die sich im
Verlauf anbieten werden — Luftfeuchte, Luftdruck, Tageslaenge, Mondphase,
Anwesenheit im Raum — sind ausdruecklich **nicht** vorgesehen. Jede zusaetzliche
Groesse muss entweder einen bislang unbelegten Angriffspunkt finden oder einen
bestehenden verdraengen. Beides ist eine Aenderung am Kern der Arbeit und gehoert
in Absprache mit der Betreuung entschieden, nicht nebenbei im Code.
