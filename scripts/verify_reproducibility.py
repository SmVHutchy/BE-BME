"""Reproduzierbarkeitspruefung zweier Laeufe.

Die Definition of Done in PLAN.md verlangt: "Reproduzierbar sind Lauf,
Ereignisse und Kennzahlen: Gleicher Seed, gleiche Config und gleicher
Wetterlog erzeugen dieselben Ereignisse zu denselben Ticks." Dieses Skript
prueft genau das an zwei tatsaechlich durchgefuehrten Laeufen aus
`data/metrics.sqlite` (Vorgabe: die zwei juengsten, ueber `--run-a`/`--run-b`
waehlbar).

Aufruf:

    uv run --project core python scripts/verify_reproducibility.py
    uv run --project core python scripts/verify_reproducibility.py --run-a 3 --run-b 4

Exit-Codes:

    0   reproduzierbar - alle Kriterien erfuellt
    1   verglichen, aber NICHT reproduzierbar - mindestens ein Kriterium verletzt,
        einschliesslich verletzter Vorbedingungen (verschiedener Seed/Config)
    2   Vergleich nicht moeglich (weniger als zwei Laeufe in der Datenbank,
        angegebener Lauf nicht gefunden, Datenbank fehlt)


VORBEDINGUNGEN

Ohne gleichen `seed` und gleichen `config_hash` ist ein Vergleich der
Kennzahlen sinnlos - die Laeufe waeren gegen unterschiedliche Sollwerte
gemessen. Beide werden zuerst geprueft; bei Verletzung bricht die Pruefung
sofort ab, bevor irgendein Zahlenvergleich versucht wird (siehe Abschnitt 0
der Ausgabe).


DAS KRITERIUM FUER "REPRODUZIERBAR TROTZ GLEITKOMMAABWEICHUNG"

Zwei GPU-Laeufe sind praktisch nie bitweise identisch: Gleitkommaoperationen
auf der GPU koennen je nach Ausfuehrungsreihenfolge und Treiberzustand
minimal abweichen, und ueber tausende Ticks reaktions-diffusiver Integration
koennen sich solche Abweichungen aufsummieren. Ein Vergleich mit `==` waere
deshalb wertlos: Er wuerde entweder (fast) immer FAIL liefern oder - schlimmer
- eine echte Divergenz durch eine zu grosszuegige globale Toleranz verdecken.

Der gewaehlte Ansatz hat zwei Ebenen, die den beiden Haelften der DoD-Zeile
entsprechen ("dieselben Ereignisse zu denselben Ticks" UND "dieselben
Kennzahlen"):

1. MASSGEBLICH ist Abschnitt 3: Wurden bei gleichem Tick dieselben
   Chronikereignisse erkannt? Der Regeldetektor (frame_core.detect.bloom) ist
   reine Schwellenwertlogik auf der Kennzahl `producer` (Expose 6.4) - er
   ist genau dann stabil gegen numerisches Rauschen, wenn die Kennzahl es
   ist. Zwei Laeufe, die in der sechsten Nachkommastelle abweichen, aber zu
   denselben Ticks dieselben Ereignistypen melden, erfuellen die Definition
   of Done vollstaendig; das ist das erwuenschte, nicht das unerwuenschte
   Ergebnis.

2. UNTERSTUETZEND ist Abschnitt 2: die Kennzahlen selbst (`producer`,
   `nutrient`, `total`, `occupancy`) je gemeinsamem Tick. Hierfuer wird nicht
   Gleichheit, sondern die RELATIVE ABWEICHUNG samt ihrem VERLAUF UEBER DIE
   ZEIT bewertet:

     - relative Abweichung je Tick: |a - b| / max(|a|, |b|, NOISE_FLOOR)
     - Median dieser Abweichung im ersten und im letzten Zehntel des Laufs
     - Wachstumsfaktor = Median(letztes Zehntel) / Median(erstes Zehntel)

   Reines Rundungsrauschen bleibt ueber einen Lauf ungefaehr GLEICH GROSS
   oder waechst hoechstens langsam (Random-Walk- bzw. lineare Akkumulation).
   Chaotisches Auseinanderlaufen - sensitive Abhaengigkeit von den
   Anfangsbedingungen, das eigentliche Gegenteil von Reproduzierbarkeit -
   waechst dagegen EXPONENTIELL mit der Tick-Zahl. Ein Feld gilt als
   strukturell (nicht mehr numerisch) abweichend, wenn entweder

     a) die Abweichung am Ende des Laufs ueber REL_DEV_NOISE_CEILING liegt,
        oder
     b) sie um mehr als GROWTH_FACTOR_STRUCTURAL vom ersten zum letzten
        Zehntel gewachsen ist (und dabei messbar von Null verschieden bleibt).

   REL_DEV_NOISE_CEILING = 1e-3 (0,1 %): float32 hat rund 7 signifikante
   Dezimalstellen (Maschinenepsilon ~1,2e-7 je Operation). Die Simulation
   reduziert das Feld ueber Millionen Gleitkommaoperationen (Diffusion,
   Reaktion, Advektion, Reduktion auf der GPU) zu einer einzelnen Kennzahl je
   Tick - Rundungsfehler koennen sich aufsummieren, aber selbst grosszuegig
   gerechnet bleibt das weit unter einem Promille relativer Abweichung. Das
   ist ausdruecklich ein ANDERER Wert als `mass.drift_tolerance_pct` (2 %):
   Jener toleriert PHYSIKALISCHE Zu- und Abgaenge (Niederschlag,
   Sedimentation) ueber einen ganzen Lauf, dieser hier toleriert
   GLEITKOMMARAUSCHEN zwischen zwei ansonsten identischen Laeufen.

   GROWTH_FACTOR_STRUCTURAL = 50: grosszuegig genug, um normales Rauschen
   (das ueber Zehntel-Fenster kaum systematisch waechst) nicht faelschlich zu
   meckern, eng genug, um eine echte exponentielle Divergenz zu fassen, bevor
   sie die Kennzahl vollstaendig dominiert.

   Die Fensterbreite orientiert sich an `scripts/soak_report.py`
   (`fenster = max(10, n // 10)`), hier robust nach unten und oben
   begrenzt, weil ein Kennzahlenvergleich mit sehr wenigen gemeinsamen
   Ticks nicht sinnvoll in Zehntel geteilt werden kann.


WETTER-ROHLOG

`data/weather_raw.jsonl` ist Voraussetzung fuer Reproduzierbarkeit "unterhalb"
von Seed und Config: Ohne identisches Wetter ist sie nicht einmal
theoretisch gegeben (siehe CLAUDE.md, Abschnitt Reproduzierbarkeit). Jede
Zeile traegt `config_hash` und `run_name`, aber KEINE `run_id` - und bei
gleichem Config-Hash (Vorbedingung fuer alles Weitere) sind beide auch fuer
zwei verschiedene Laeufe identisch, koennen also nicht zur Zuordnung dienen.
Zugeordnet wird deshalb ueber den ZEITSTEMPEL `logged_at`: Jede Logzeile
faellt in das Intervall zwischen dem Start ihres Laufs (`runs.started_at`)
und dem Start des naechstjuengeren Laufs. Verglichen werden je Variable die
Stundenwerte, die in beiden Zeitfenstern protokolliert wurden (exakter
Vergleich, mit kleiner Gleitkommatoleranz gegen Rundung beim JSON-Parsing -
die Werte sind Rohkopien der API-Antwort und sollten andernfalls exakt
uebereinstimmen).


ANGEWANDTE KLIMAWERTE (env_applied)

Dieser Abschnitt ist bewusst NUR INFORMATIV und geht NICHT ins Gesamturteil
ein - das ist eine Entwurfsentscheidung, keine Nachlaessigkeit. Die Tabelle
`env_applied` (core/src/frame_core/metrics/store.py) fuehrt weder `tick` noch
`world_time`, sondern nur den Wanduhr-Zeitstempel, zu dem `core` einen Wert
an `sim` geschickt hat (Push-Rhythmus `environment.push_interval_s`, an
Wanduhrzeit gekoppelt, nicht an Ticks). Ein Vergleich "derselbe Tick" ist aus
dieser Tabelle also nicht rekonstruierbar; das Skript vergleicht ersatzweise
ORDINAL (n-te protokollierte Zeile gegen n-te protokollierte Zeile). Das ist
nur eine Naeherung: Bei Zeitkonstanten von 20-90 Minuten (`smoothing_minutes`)
kann schon eine Verschiebung um einen Push-Zyklus reale Wertunterschiede
erzeugen, die nichts mit fehlender Reproduzierbarkeit zu tun haben. Deshalb
Warnhinweis statt Urteil - siehe Abschnitt 4 der Ausgabe.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core" / "src"))

from frame_core.config import load_config  # noqa: E402

OK = "  OK  "
FAIL = " FAIL "
INFO = "  --  "

# Siehe Moduldocstring, Abschnitt "DAS KRITERIUM...", fuer die Begruendung
# dieser beiden Werte.
NOISE_FLOOR = 1e-9
REL_DEV_NOISE_CEILING = 1e-3
GROWTH_FACTOR_STRUCTURAL = 50.0

# Siehe Moduldocstring, Abschnitt "ANGEWANDTE KLIMAWERTE": rein informativ,
# deutlich grosszuegiger als REL_DEV_NOISE_CEILING, weil der ordinale
# Vergleich Verschiebungen durch Push-Timing nicht von echten Abweichungen
# trennen kann.
ENV_REL_DEV_INFO_CEILING = 0.15

FERNE_ZUKUNFT = datetime(9999, 1, 1, tzinfo=UTC)

FELDER_KENNZAHLEN = ("producer", "nutrient", "total", "occupancy")
FELDER_ENV = ("light", "nutrient_input", "rate", "wind_dir_deg", "wind_speed")


def urteil(bestanden: bool) -> str:
    return OK if bestanden else FAIL


def relative_abweichung(a: float, b: float) -> float:
    nenner = max(abs(a), abs(b), NOISE_FLOOR)
    return abs(a - b) / nenner


# --- Laeufe laden ------------------------------------------------------------

def lade_laufpaar(conn: sqlite3.Connection, run_a_id: int | None,
                  run_b_id: int | None) -> tuple[sqlite3.Row, sqlite3.Row] | None:
    if run_a_id is not None or run_b_id is not None:
        if run_a_id is None or run_b_id is None:
            print("--run-a und --run-b muessen zusammen angegeben werden.")
            return None
        a = conn.execute("SELECT * FROM runs WHERE id = ?", (run_a_id,)).fetchone()
        b = conn.execute("SELECT * FROM runs WHERE id = ?", (run_b_id,)).fetchone()
        fehlend = [str(i) for i, r in ((run_a_id, a), (run_b_id, b)) if r is None]
        if fehlend:
            print(f"Lauf/Laeufe nicht gefunden: {', '.join(fehlend)}")
            return None
        return a, b

    rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 2").fetchall()
    if len(rows) < 2:
        print(f"Nur {len(rows)} Lauf/Laeufe in der Datenbank - ein "
              f"Reproduzierbarkeitsvergleich braucht mindestens zwei. Erst einen zweiten "
              f"Lauf mit gleichem Seed, gleicher Config und gleichem Wetter durchfuehren.")
        return None
    # rows[0] ist der juengste; chronologisch ordnen fuer lesbarere Ausgabe.
    return rows[1], rows[0]


# --- Wetter-Rohlog ------------------------------------------------------------

def lese_wetterlog(path: Path) -> list[dict]:
    zeilen = []
    for zeile in path.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if zeile:
            zeilen.append(json.loads(zeile))
    return zeilen


def wetter_fenster(conn: sqlite3.Connection) -> dict[int, tuple[datetime, datetime]]:
    """Zeitfenster [start, ende) je Lauf, in dem seine Wetterabfragen protokolliert wurden.

    Begruendung siehe Moduldocstring, Abschnitt "WETTER-ROHLOG".
    """
    rows = conn.execute("SELECT id, started_at FROM runs ORDER BY started_at ASC").fetchall()
    fenster: dict[int, tuple[datetime, datetime]] = {}
    for i, row in enumerate(rows):
        start = datetime.fromisoformat(row["started_at"])
        ende = (datetime.fromisoformat(rows[i + 1]["started_at"])
                if i + 1 < len(rows) else FERNE_ZUKUNFT)
        fenster[row["id"]] = (start, ende)
    return fenster


def wetter_fuer_lauf(records: list[dict], config_hash: str,
                     start: datetime, ende: datetime) -> dict[str, dict[str, object]]:
    """variable -> {Stundenzeitpunkt: Wert}, aus allen passenden Logzeilen zusammengefuehrt.

    Bei ueberlappenden Abrufen (Cache-Refresh) gewinnt die spaetere Zeile - das
    ist der zuletzt gueltige Stand, der auch tatsaechlich interpoliert wurde.
    """
    ergebnis: dict[str, dict[str, object]] = {}
    for rec in records:
        if rec.get("config_hash") != config_hash:
            continue
        zeitpunkt = datetime.fromisoformat(rec["logged_at"])
        if not (start <= zeitpunkt < ende):
            continue
        hourly = rec.get("response", {}).get("hourly", {})
        stunden = hourly.get("time", [])
        for variable, werte in hourly.items():
            if variable == "time" or werte is None:
                continue
            zielmap = ergebnis.setdefault(variable, {})
            for stunde, wert in zip(stunden, werte):
                if wert is not None:
                    zielmap[stunde] = wert
    return ergebnis


def werte_gleich(a: object, b: object) -> bool:
    if a is None or b is None:
        return a == b
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return a == b


# --- Kennzahlen ----------------------------------------------------------------

def hole_metriken(conn: sqlite3.Connection, run_id: int) -> dict[int, sqlite3.Row]:
    rows = conn.execute(
        "SELECT * FROM metrics WHERE run_id = ? ORDER BY tick ASC", (run_id,)
    ).fetchall()
    return {row["tick"]: row for row in rows}


@dataclass(frozen=True)
class FeldErgebnis:
    name: str
    n: int
    max_dev: float
    first_window_median: float
    last_window_median: float
    growth_factor: float
    ok: bool
    hinweis: str


def bewerte_feld(name: str, metrics_a: dict[int, sqlite3.Row],
                 metrics_b: dict[int, sqlite3.Row], ticks: list[int]) -> FeldErgebnis:
    abweichungen = [relative_abweichung(float(metrics_a[t][name]), float(metrics_b[t][name]))
                    for t in ticks]

    n = len(abweichungen)
    fenstergroesse = max(1, min(max(3, n // 10), n // 2 or 1))
    erster_median = statistics.median(abweichungen[:fenstergroesse])
    letzter_median = statistics.median(abweichungen[-fenstergroesse:])
    wachstum = letzter_median / max(erster_median, NOISE_FLOOR)

    ueber_rauschgrenze = letzter_median > REL_DEV_NOISE_CEILING
    exponentiell = (wachstum > GROWTH_FACTOR_STRUCTURAL
                    and letzter_median > NOISE_FLOOR * 10)
    ok = not (ueber_rauschgrenze or exponentiell)

    hinweis = ""
    if ueber_rauschgrenze:
        hinweis = (f"Abweichung am Ende des Laufs ({letzter_median:.2e}) liegt ueber der "
                  f"Rauschgrenze ({REL_DEV_NOISE_CEILING:.0e}) - mehr, als Gleitkomma-"
                  f"rauschen ueber diesen Lauf erklaeren kann.")
    elif exponentiell:
        hinweis = (f"Abweichung waechst um Faktor {wachstum:.0f} vom ersten zum letzten "
                  f"Zehntel des Laufs - das Muster exponentieller (chaotischer) "
                  f"Divergenz, nicht das eines stabilen Rauschbodens.")

    return FeldErgebnis(name=name, n=n, max_dev=max(abweichungen),
                        first_window_median=erster_median, last_window_median=letzter_median,
                        growth_factor=wachstum, ok=ok, hinweis=hinweis)


# --- Chronik ---------------------------------------------------------------

def hole_ereignisse(conn: sqlite3.Connection, run_id: int) -> list[tuple[int, str]]:
    rows = conn.execute(
        "SELECT tick, event_type FROM chronicle_entries WHERE run_id = ? "
        "ORDER BY tick ASC, id ASC", (run_id,)
    ).fetchall()
    return [(row["tick"], row["event_type"]) for row in rows]


# --- Angewandte Klimawerte ---------------------------------------------------

def hole_env_reihe(conn: sqlite3.Connection, run_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM env_applied WHERE run_id = ? ORDER BY id ASC", (run_id,)
    ).fetchall()


# --- Ablauf --------------------------------------------------------------------

def vergleichen(conn: sqlite3.Connection, lauf_a: sqlite3.Row, lauf_b: sqlite3.Row,
                weather_log_path: Path) -> int:
    print("=" * 78)
    print(f"Lauf A: #{lauf_a['id']} {lauf_a['name']}  (Beginn {lauf_a['started_at']})")
    print(f"Lauf B: #{lauf_b['id']} {lauf_b['name']}  (Beginn {lauf_b['started_at']})")
    print("=" * 78)

    # --- 0. Vorbedingungen --------------------------------------------------
    print("\n0. Vorbedingungen")
    seed_gleich = lauf_a["seed"] == lauf_b["seed"]
    print(f"[{urteil(seed_gleich)}] Seed gleich: A={lauf_a['seed']}  B={lauf_b['seed']}")
    hash_gleich = lauf_a["config_hash"] == lauf_b["config_hash"]
    print(f"[{urteil(hash_gleich)}] Config-Hash gleich: "
          f"A={lauf_a['config_hash'][:16]}...  B={lauf_b['config_hash'][:16]}...")

    if not (seed_gleich and hash_gleich):
        print("\nAbbruch: Die Vorbedingungen der Reproduzierbarkeit sind verletzt.")
        if not seed_gleich:
            print("  Verschiedene Seeds -> jeder Zufallsprozess (Shader-Rauschen, "
                  "Startmuster, Mutation) startet an einer anderen Stelle. Die Laeufe "
                  "koennen allenfalls zufaellig aehnlich aussehen, sind aber per "
                  "Definition nicht derselbe Lauf.")
        if not hash_gleich:
            print("  Verschiedene Config-Hashes -> mindestens ein Parameter in "
                  "params.yaml unterscheidet sich. Ein Vergleich der Kennzahlen waere "
                  "gegen unterschiedliche Sollwerte gemessen und aussagelos.")
        print("\nEin Vergleich der Kennzahlen, Ereignisse oder des Wetters ist unter "
              "diesen Umstaenden nicht aussagekraeftig und wird nicht durchgefuehrt.")
        return 1

    alles_bestanden = True

    # --- 1. Wetter-Rohlog -----------------------------------------------------
    print("\n1. Wetter-Rohlog")
    if not weather_log_path.exists():
        alles_bestanden = False
        print(f"[{FAIL}] {weather_log_path} nicht vorhanden. Ohne Rohlog ist selbst bei "
              f"gleichem Seed und gleicher Config nicht nachweisbar, dass beide Laeufe "
              f"dasselbe Wetter sahen.")
    else:
        records = lese_wetterlog(weather_log_path)
        fenster = wetter_fenster(conn)
        start_a, ende_a = fenster[lauf_a["id"]]
        start_b, ende_b = fenster[lauf_b["id"]]
        wetter_a = wetter_fuer_lauf(records, lauf_a["config_hash"], start_a, ende_a)
        wetter_b = wetter_fuer_lauf(records, lauf_b["config_hash"], start_b, ende_b)

        zeilen_a = sum(1 for r in records if r.get("config_hash") == lauf_a["config_hash"]
                       and start_a <= datetime.fromisoformat(r["logged_at"]) < ende_a)
        zeilen_b = sum(1 for r in records if r.get("config_hash") == lauf_b["config_hash"]
                       and start_b <= datetime.fromisoformat(r["logged_at"]) < ende_b)
        print(f"[{INFO}] Rohantworten protokolliert: A={zeilen_a}  B={zeilen_b}")

        gemeinsame_gesamt = 0
        abweichend_gesamt = 0
        beispiele: list[tuple[str, str, object, object]] = []
        for variable in sorted(set(wetter_a) | set(wetter_b)):
            a_map = wetter_a.get(variable, {})
            b_map = wetter_b.get(variable, {})
            gemeinsame = sorted(set(a_map) & set(b_map))
            gemeinsame_gesamt += len(gemeinsame)
            for stunde in gemeinsame:
                if not werte_gleich(a_map[stunde], b_map[stunde]):
                    abweichend_gesamt += 1
                    if len(beispiele) < 5:
                        beispiele.append((variable, stunde, a_map[stunde], b_map[stunde]))
            print(f"        {variable}: {len(a_map)} Std. (A), {len(b_map)} Std. (B), "
                  f"{len(gemeinsame)} gemeinsam")

        if gemeinsame_gesamt == 0:
            print(f"[{INFO}] Keine gemeinsamen Wetterstunden gefunden - Vergleich nicht "
                  f"moeglich (unterschiedliche Zeitfenster abgefragt, oder noch kein "
                  f"Poll gelaufen). Zaehlt nicht gegen das Gesamturteil.")
        else:
            wetter_ok = abweichend_gesamt == 0
            alles_bestanden &= wetter_ok
            print(f"[{urteil(wetter_ok)}] {gemeinsame_gesamt} gemeinsame Stundenwerte "
                  f"geprueft, {abweichend_gesamt} abweichend")
            for variable, stunde, a_wert, b_wert in beispiele:
                print(f"        Beispiel: {variable} @ {stunde}: A={a_wert}  B={b_wert}")

    # --- 2. Kennzahlen je Tick -------------------------------------------------
    print("\n2. Kennzahlen je Tick")
    metrics_a = hole_metriken(conn, lauf_a["id"])
    metrics_b = hole_metriken(conn, lauf_b["id"])
    gemeinsame_ticks = sorted(set(metrics_a) & set(metrics_b))
    print(f"[{INFO}] Messpunkte: A={len(metrics_a)}  B={len(metrics_b)}  "
          f"gemeinsame Ticks={len(gemeinsame_ticks)}")

    if len(gemeinsame_ticks) < 10:
        print(f"[{INFO}] Zu wenige gemeinsame Ticks fuer eine aussagekraeftige "
              f"Abweichungsanalyse. Zaehlt nicht gegen das Gesamturteil.")
    else:
        for feld in FELDER_KENNZAHLEN:
            ergebnis = bewerte_feld(feld, metrics_a, metrics_b, gemeinsame_ticks)
            alles_bestanden &= ergebnis.ok
            print(f"[{urteil(ergebnis.ok)}] {feld}: groesste rel. Abweichung "
                  f"{ergebnis.max_dev:.2e}; Median letztes Zehntel "
                  f"{ergebnis.last_window_median:.2e} (erstes Zehntel "
                  f"{ergebnis.first_window_median:.2e}, Faktor "
                  f"{ergebnis.growth_factor:.1f})")
            if not ergebnis.ok:
                print(f"        {ergebnis.hinweis}")

    # --- 3. Chronikereignisse ---------------------------------------------------
    print("\n3. Chronikereignisse")
    ereignisse_a = hole_ereignisse(conn, lauf_a["id"])
    ereignisse_b = hole_ereignisse(conn, lauf_b["id"])
    print(f"[{INFO}] Ereignisse: A={len(ereignisse_a)}  B={len(ereignisse_b)}")

    if not ereignisse_a and not ereignisse_b:
        print(f"[{INFO}] Keine Ereignisse in beiden Laeufen protokolliert - der "
              f"Chronikvergleich prueft damit nichts und zaehlt nicht gegen das "
              f"Gesamturteil. Fuer einen aussagekraeftigen Vergleich muss mindestens "
              f"einer der beiden Laeufe lang genug laufen, um eine Bluete auszuloesen.")
    else:
        zaehler_a = Counter(ereignisse_a)
        zaehler_b = Counter(ereignisse_b)
        nur_a = zaehler_a - zaehler_b
        nur_b = zaehler_b - zaehler_a
        ereignisse_ok = not nur_a and not nur_b
        alles_bestanden &= ereignisse_ok
        print(f"[{urteil(ereignisse_ok)}] Ereignisse (Tick, event_type) stimmen ueberein")
        for tick, typ in sorted(nur_a):
            print(f"        nur in A: Tick {tick} ({typ})")
        for tick, typ in sorted(nur_b):
            print(f"        nur in B: Tick {tick} ({typ})")

    # --- 4. Angewandte Klimawerte (informativ) -----------------------------------
    print("\n4. Angewandte Klimawerte (env_applied, ordinalgestuetzter Vergleich)")
    env_a = hole_env_reihe(conn, lauf_a["id"])
    env_b = hole_env_reihe(conn, lauf_b["id"])
    print(f"[{INFO}] Zeilen: A={len(env_a)}  B={len(env_b)}")
    if not env_a or not env_b:
        print(f"[{INFO}] Mindestens ein Lauf hat keine env-Werte protokolliert - "
              f"Vergleich nicht moeglich.")
    else:
        # env_applied hat weder tick- noch world_time-Spalte (siehe Moduldocstring) -
        # der Vergleich laeuft ordinal ueber die Einfuegereihenfolge. Das geht NICHT
        # in alles_bestanden ein, siehe Begruendung im Moduldocstring.
        n = min(len(env_a), len(env_b))
        schlimmste = {}
        for feld in FELDER_ENV:
            abweichungen = [relative_abweichung(float(env_a[i][feld]), float(env_b[i][feld]))
                            for i in range(n)]
            schlimmste[feld] = max(abweichungen)
        env_auffaellig = any(v > ENV_REL_DEV_INFO_CEILING for v in schlimmste.values())
        print(f"[{INFO}] groesste rel. Abweichung je Feld (ordinal, {n} Zeilenpaare): "
              + ", ".join(f"{k}={v:.2e}" for k, v in schlimmste.items()))
        if env_auffaellig:
            print("        Auffaellig grosse Abweichung in mindestens einem Feld - kann "
                  "am Push-Timing liegen (siehe Moduldocstring) oder ein echter "
                  "Hinweis sein. Nicht Teil des Gesamturteils, von Hand pruefen.")

    print("\n" + "=" * 78)
    print("GESAMT: " + ("REPRODUZIERBAR" if alles_bestanden else "NICHT REPRODUZIERBAR"))
    print("=" * 78)
    return 0 if alles_bestanden else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=None,
                        help="Pfad zur Metrikdatenbank (Vorgabe: metrics.db_path aus params.yaml)")
    parser.add_argument("--weather-log", type=Path, default=None,
                        help="Pfad zum Wetter-Rohlog (Vorgabe: metrics.weather_log_path)")
    parser.add_argument("--run-a", type=int, default=None,
                        help="Lauf-ID des ersten Laufs (mit --run-b zusammen angeben)")
    parser.add_argument("--run-b", type=int, default=None,
                        help="Lauf-ID des zweiten Laufs (ohne beide: die zwei juengsten Laeufe)")
    args = parser.parse_args()

    app = load_config(ROOT / "config" / "params.yaml")
    db_path = args.db or ROOT / app.values.metrics.db_path
    weather_log_path = args.weather_log or ROOT / app.values.metrics.weather_log_path

    if not db_path.exists():
        print(f"Keine Metrikdatenbank unter {db_path}. Erst zwei Laeufe durchfuehren.")
        return 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        lauf_paar = lade_laufpaar(conn, args.run_a, args.run_b)
        if lauf_paar is None:
            return 2
        lauf_a, lauf_b = lauf_paar
        return vergleichen(conn, lauf_a, lauf_b, weather_log_path)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
