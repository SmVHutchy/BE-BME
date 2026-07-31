"""Auswertung eines Dauer- oder Zeitrafferlaufs.

Liest die Metrikdatenbank und das Health-Log und beantwortet die
Abnahmekriterien mit Zahlen statt mit Eindruecken:

  A12          Residualsaldo der Massenbilanz ueber den Lauf
  Risiko 1     Ueberlebt das Oekosystem? Bleibt die Masse im Korridor?
  DoD          Konvergiert die Biomasse auf einen Fixpunkt?
  Risiko 3     Haelt die GPU den Takt, oder werden Ticks verworfen?
  Risiko 8     Hat der Klimakanal getragen, und aus welcher Quelle?
  Expose 6.4   Sind Chronikeintraege entstanden, und sind ihre Zahlen belegt?

Aufruf nach einem Lauf:

    uv run --project core python scripts/soak_report.py

Der Residualsaldo wird NICHT hier neu implementiert, sondern ueber
`frame_core.metrics.balance.check_balance` gebildet - dieselbe Funktion, die
`core` zur Laufzeit benutzt und die getestet ist.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core" / "src"))

from frame_core.chronicle.guard import find_unsupported_numbers  # noqa: E402
from frame_core.config import load_config  # noqa: E402
from frame_core.metrics.balance import check_balance  # noqa: E402

OK = "  OK  "
FAIL = " FAIL "
INFO = "  --  "


def urteil(bestanden: bool) -> str:
    return OK if bestanden else FAIL


def lade_lauf(conn: sqlite3.Connection, run_id: int | None) -> sqlite3.Row:
    if run_id is None:
        row = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    else:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise SystemExit("Kein Lauf in der Datenbank. Erst einen Lauf durchfuehren.")
    return row


def auswerten(db_path: Path, health_path: Path, run_id: int | None) -> int:
    app = load_config(ROOT / "config" / "params.yaml")
    values = app.values

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    lauf = lade_lauf(conn, run_id)

    metriken = conn.execute(
        "SELECT * FROM metrics WHERE run_id = ? ORDER BY tick ASC", (lauf["id"],)
    ).fetchall()

    print("=" * 72)
    print(f"Lauf {lauf['id']}: {lauf['name']}")
    print(f"  Seed        {lauf['seed']}")
    print(f"  Config      {lauf['config_hash'][:16]}...")
    print(f"  Beginn      {lauf['started_at']}")
    print(f"  Stichproben {len(metriken)}")
    print("=" * 72)

    if len(metriken) < 2:
        print("\nZu wenige Messpunkte fuer eine Auswertung.")
        return 1

    alles_bestanden = True
    erste, letzte = metriken[0], metriken[-1]
    produzenten = [float(m["producer"]) for m in metriken]

    # --- Weltzeit ----------------------------------------------------------
    ticks = letzte["tick"] - erste["tick"]
    print(f"\nGerechnet: {ticks:,} Ticks".replace(",", "."))
    print(f"  entspricht rund {ticks * values.sim.dt_base / 86400:.2f} Welttagen "
          f"bei rate = 1")

    # --- Risiko 1: ueberlebt das System? -----------------------------------
    print("\n1. Ueberleben (Risiko 1)")
    lebt = produzenten[-1] > 0.0
    alles_bestanden &= lebt
    print(f"[{urteil(lebt)}] Biomasse am Ende: {produzenten[-1]:.1f} "
          f"(Beginn {produzenten[0]:.1f}, Maximum {max(produzenten):.1f})")
    if not lebt:
        print("        Das Oekosystem ist ausgestorben. Alles Weitere ist "
              "damit nur noch begrenzt aussagekraeftig.")

    # --- DoD: kein Fixpunkt ------------------------------------------------
    print("\n2. Keine Zustandskonvergenz (Definition of Done, Expose 4)")
    fenster = max(10, len(produzenten) // 10)
    letzte_varianz = statistics.pvariance(produzenten[-fenster:]) if fenster > 1 else 0.0
    fruehe_varianz = statistics.pvariance(produzenten[:fenster]) if fenster > 1 else 0.0
    bewegt = letzte_varianz > 0.0
    alles_bestanden &= bewegt
    print(f"[{urteil(bewegt)}] Varianz im letzten Zehntel: {letzte_varianz:.6g} "
          f"(im ersten: {fruehe_varianz:.6g})")
    print(f"[{INFO}] Spannweite gesamt: {min(produzenten):.1f} bis {max(produzenten):.1f}")
    if bewegt and letzte_varianz < fruehe_varianz / 100:
        print("        Hinweis: Die Varianz faellt stark ab - das System beruhigt "
              "sich. Ueber einen laengeren Lauf beobachten.")

    # --- A12: Massenbilanz -------------------------------------------------
    print("\n3. Massenbilanz (A12, Risiko 2)")
    residuen = []
    for m in metriken:
        ergebnis = check_balance(
            initial_total=float(erste["total"]),
            current_total=float(m["total"]),
            inflow_total=float(m["inflow_total"]) - float(erste["inflow_total"]),
            outflow_total=float(m["outflow_total"]) - float(erste["outflow_total"]),
            drift_tolerance_pct=values.mass.drift_tolerance_pct,
            corridor_min=values.mass.corridor_min,
            corridor_max=values.mass.corridor_max,
        )
        residuen.append(ergebnis)

    schlimmstes = max(residuen, key=lambda r: r.residual_pct)
    in_toleranz = schlimmstes.within_tolerance
    alles_bestanden &= in_toleranz
    print(f"[{urteil(in_toleranz)}] Groesstes Residuum: {schlimmstes.residual_pct:.3f} % "
          f"(Toleranz {values.mass.drift_tolerance_pct} %)")
    print(f"[{INFO}] Am Ende: {residuen[-1].residual_pct:.3f} %")
    print(f"[{INFO}] Eintrag gesamt {float(letzte['inflow_total']):.1f}, "
          f"Austrag gesamt {float(letzte['outflow_total']):.1f}")

    im_korridor = all(r.within_corridor for r in residuen)
    print(f"[{urteil(im_korridor)}] Gesamtmasse im Korridor "
          f"{values.mass.corridor_min}..{values.mass.corridor_max} "
          f"(erreicht {min(r.total_ratio for r in residuen):.3f} bis "
          f"{max(r.total_ratio for r in residuen):.3f})")
    alles_bestanden &= im_korridor

    # --- Klimakanal --------------------------------------------------------
    print("\n4. Klimakanal (Risiko 8)")
    env_zeilen = conn.execute(
        "SELECT * FROM env_applied WHERE run_id = ? ORDER BY id ASC", (lauf["id"],)
    ).fetchall()
    if env_zeilen:
        licht = [float(e["light"]) for e in env_zeilen]
        hell = sum(1 for w in licht if w > 0.05)
        wechsel = hell > 0 and hell < len(licht)
        alles_bestanden &= wechsel
        print(f"[{urteil(wechsel)}] Tag-Nacht-Wechsel: {hell} von {len(licht)} "
              f"Stichproben hell")
        if not wechsel:
            print("        Kein Wechsel - das Wetter stand still. Genau der "
                  "Fehler A11. Laeuft der Burst an core vorbei?")
        raten = [float(e["rate"]) for e in env_zeilen]
        an_klammer = sum(1 for r in raten
                         if abs(r - values.coupling.rate.output_max) < 1e-6
                         or abs(r - values.coupling.rate.output_min) < 1e-6)
        print(f"[{INFO}] Licht {min(licht):.3f} bis {max(licht):.3f}, "
              f"Rate {min(raten):.3f} bis {max(raten):.3f}")
        print(f"[{INFO}] Rate an der Klammer: {an_klammer} von {len(raten)} "
              f"({an_klammer / len(raten) * 100:.0f} %) - vgl. A13")
    else:
        alles_bestanden = False
        print(f"[{FAIL}] Keine env-Werte protokolliert. core hat nie Klimawerte "
              f"geschickt oder sim hat sie nie angefordert.")

    # --- Chronik -----------------------------------------------------------
    print("\n5. Chronik (Expose 6.4)")
    eintraege = conn.execute(
        "SELECT * FROM chronicle_entries WHERE run_id = ? ORDER BY id ASC", (lauf["id"],)
    ).fetchall()
    print(f"[{INFO}] {len(eintraege)} Eintrag/Eintraege")
    for eintrag in eintraege:
        ref = json.loads(eintrag["metrics_ref"])
        unbelegt = find_unsupported_numbers(eintrag["text"], ref)
        alles_bestanden &= not unbelegt
        print(f"[{urteil(not unbelegt)}] #{eintrag['id']} ({eintrag['backend']}, "
              f"Tick {eintrag['tick']}): "
              + (f"nicht belegt: {unbelegt}" if unbelegt
                 else "jede Zahl durch metrics_ref gedeckt"))
        print(f"        {eintrag['text'][:150]}")

    # --- Betrieb -----------------------------------------------------------
    print("\n6. Betrieb (Risiko 3)")
    if health_path.exists():
        zeilen = [json.loads(z) for z in health_path.read_text(encoding="utf-8").splitlines() if z.strip()]
        zeilen = [z for z in zeilen if z.get("run") == lauf["name"]]
        if zeilen:
            letzte_zeile = zeilen[-1]
            bildzeiten = [z["frame_ms"] for z in zeilen if z.get("frame_ms")]
            print(f"[{INFO}] {len(zeilen)} Health-Zeilen, Neustarts "
                  f"{letzte_zeile.get('restarts', 0)}")
            if bildzeiten:
                print(f"[{INFO}] Bildzeit im Mittel {statistics.mean(bildzeiten):.1f} ms, "
                      f"maximal {max(bildzeiten):.1f} ms")
            umgebung = letzte_zeile.get("environment", {})
            print(f"[{INFO}] Wetterquelle {umgebung.get('source')}, "
                  f"Ausfaelle in Folge {umgebung.get('consecutive_failures')}")
        else:
            print(f"[{INFO}] Keine Health-Zeilen fuer diesen Lauf.")
    else:
        print(f"[{INFO}] {health_path} nicht vorhanden.")

    conn.close()
    print("\n" + "=" * 72)
    print("GESAMT: " + ("BESTANDEN" if alles_bestanden else "NICHT BESTANDEN"))
    print("=" * 72)
    return 0 if alles_bestanden else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, default=None,
                        help="Lauf-ID (ohne Angabe: der juengste)")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--health", type=Path, default=None)
    args = parser.parse_args()

    app = load_config(ROOT / "config" / "params.yaml")
    db = args.db or ROOT / app.values.metrics.db_path
    health = args.health or ROOT / app.values.health.path

    if not db.exists():
        raise SystemExit(f"Keine Metrikdatenbank unter {db}. Erst einen Lauf durchfuehren.")
    return auswerten(db, health, args.run)


if __name__ == "__main__":
    raise SystemExit(main())
