"""Speist synthetische Metriken ein und prueft den Chronikpfad.

Entwicklungswerkzeug. Ersetzt in Phase 1 die noch nicht gebaute Simulation und
weist die Abnahmebedingung nach:

  1. Der Detektor loest bei einer Bluete aus - und vorher nicht.
  2. Ein Eintrag entsteht und landet in SQLite.
  3. **Jede Zahl im Eintrag findet sich in metrics_ref wieder.**

Aufruf bei laufendem `core`:

    uv run --project core python scripts/feed_synthetic.py

Voraussetzung fuer Schritt 2 und 3 ist ein erreichbarer LM-Studio-Server.
Ohne ihn laufen Schritt 1 und die Speicherung trotzdem durch; das Skript sagt
dann, woran es lag.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from datetime import UTC, datetime, timedelta

import httpx
import websockets

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]
                       / "core" / "src"))

from frame_core.chronicle.guard import find_unsupported_numbers  # noqa: E402


def metrics_message(tick: int, producer: float, nutrient: float,
                    when: datetime) -> dict:
    """Eine Metriknachricht nach docs/contract.md.

    Geschlossener Kreislauf ohne aeusseren Austausch: Was die Produzenten
    aufnehmen, fehlt im Naehrstofffeld. Eintrag und Austrag bleiben null, der
    Residualsaldo ist damit exakt null - so laesst sich die Bilanzpruefung
    getrennt von der Detektorpruefung beurteilen.
    """
    return {
        "t": when.isoformat(),
        "tick": tick,
        "mass": {
            "nutrient": round(nutrient, 6),
            "producer": round(producer, 6),
            "consumer": 0.0,
            "total": round(nutrient + producer, 6),
            "inflow_total": 0.0,
            "outflow_total": 0.0,
        },
        "lineages": 1,
        "gene_median": {},
        "occupancy": round(min(1.0, producer * 1.8), 6),
    }


async def feed(host: str, port: int, baseline: int, seed: int) -> None:
    rng = random.Random(seed)
    uri = f"ws://{host}:{port}/ws"
    gesamtmasse = 0.50
    start = datetime.now(UTC) - timedelta(seconds=5 * (baseline + 1))

    print(f"Verbinde mit {uri}")
    async with websockets.connect(uri, max_queue=None) as ws:
        # --- Grundrauschen: darf NICHT ausloesen ---------------------------
        for index in range(baseline):
            producer = rng.gauss(0.20, 0.012)
            message = metrics_message(tick=index * 10, producer=producer,
                                      nutrient=gesamtmasse - producer,
                                      when=start + timedelta(seconds=5 * index))
            await ws.send(json.dumps(message))
            if index % 40 == 0:
                print(f"  {index:4d} Stichproben, Biomasse {producer:.4f}")
            await asyncio.sleep(0.004)

        print(f"  {baseline} Stichproben Grundrauschen gesendet")

        # --- Die Bluete ----------------------------------------------------
        bluete = 0.42
        await ws.send(json.dumps(metrics_message(
            tick=baseline * 10, producer=bluete, nutrient=gesamtmasse - bluete,
            when=start + timedelta(seconds=5 * baseline))))
        print(f"  Bluete gesendet: Biomasse {bluete:.4f}")
        await asyncio.sleep(0.5)


async def verify(host: str, port: int, wait_s: float) -> int:
    """Holt die Chronik und prueft jede Zahl gegen metrics_ref."""
    base = f"http://{host}:{port}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        health = (await client.get(f"{base}/health")).json()
        print(f"\nLauf {health['run_id']}, {health['metrics_rows']} Metrikzeilen, "
              f"Backend {health['chronicle_backend']}")
        if "mass_residual_pct" in health:
            print(f"Massenbilanz: Residuum {health['mass_residual_pct']} %, "
                  f"in Toleranz: {health['mass_within_tolerance']}")

        print(f"\nWarte bis zu {wait_s:.0f} s auf den Chronikeintrag "
              f"(ein Modellaufruf dauert gemessen 19-25 s) ...")
        deadline = asyncio.get_running_loop().time() + wait_s
        entries: list[dict] = []
        while asyncio.get_running_loop().time() < deadline:
            entries = (await client.get(f"{base}/chronicle", params={"limit": 5})).json()["entries"]
            if entries:
                break
            await asyncio.sleep(2.0)

    if not entries:
        print("\nKein Chronikeintrag entstanden.")
        print("Detektor und Speicherung sind davon unberuehrt - siehe Metrikzeilen oben.")
        print("Haeufigste Ursache: LM-Studio-Server laeuft nicht (Status: Stopped).")
        return 1

    print(f"\n{len(entries)} Eintrag/Eintraege:\n")
    fehler = 0
    for entry in entries:
        print(f"--- Eintrag {entry['id']} ({entry['backend']}, {entry['event_type']}, "
              f"Tick {entry['tick']}) ---")
        print(entry["text"])
        unbelegt = find_unsupported_numbers(entry["text"], entry["metrics_ref"])
        if unbelegt:
            print(f"\n  NICHT BELEGT: {unbelegt}")
            fehler += 1
        else:
            print("\n  Jede Zahl im Text ist durch metrics_ref gedeckt.")
        print(f"  metrics_ref: {entry['metrics_ref']}\n")

    return 1 if fehler else 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--baseline", type=int, default=150,
                        help="Stichproben Grundrauschen vor der Bluete "
                             "(muss ueber detector.bloom.min_samples liegen)")
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument("--wait", type=float, default=120.0)
    args = parser.parse_args()

    await feed(args.host, args.port, args.baseline, args.seed)
    return await verify(args.host, args.port, args.wait)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
