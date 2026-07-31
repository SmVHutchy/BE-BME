"""Watchdog fuer den Dauerbetrieb von `core`.

Expose 7.4 verlangt "Watchdog mit automatischem Neustart" und "taegliches
Health-Log". Dieses Skript deckt den ersten Teil ab und haengt sich in den
zweiten ein: Es startet `core` als Kindprozess, ueberwacht ihn, startet ihn
bei einem Absturz mit wachsender Wartezeit (Backoff) neu und schreibt jeden
Neustart als eigene Zeile in dasselbe Health-Log, das `core` selbst fuehrt
(data/health.jsonl, Format und Klasse siehe
core/src/frame_core/health/log.py). Der Neustartzaehler ist Teil der
Auswertung (siehe scripts/soak_report.py), kein Beiwerk - bei einem System,
das ueber Wochen unbeaufsichtigt laufen soll, ist die Zahl der Neustarts ein
Messergebnis.

Reines Python: Standardbibliothek plus das, was core/pyproject.toml bereits
mitbringt (pydantic, pyyaml - fuer das Lesen der Config und das Schreiben des
Health-Logs). Keine neuen Abhaengigkeiten. Die schweren Importe aus
`frame_core` geschehen erst NACH dem Parsen der Kommandozeile, damit
`--help` auch mit einem blanken Standard-Python laeuft, ohne core/.venv.

Aufruf aus dem Projektwurzelverzeichnis:

    python scripts/watchdog.py
    python scripts/watchdog.py --max-restarts 10 --backoff-base 10

Startbefehl fuer core, sofern nicht per --command ersetzt:

    uv run --project core uvicorn frame_core.api:app --host <host> --port <port>

Das laeuft bewusst aus dem Projektwurzelverzeichnis, nicht aus core/: Beim
Test dieses Skripts stellte sich heraus, dass `cd core && uv run uvicorn ...`
(die bisherige README-Fassung) an genau der Stelle scheitert, an der `core`
config/params.yaml relativ zum Arbeitsverzeichnis sucht - von core/ aus gibt
es das nicht. `--project core` findet das uv-Projekt unabhaengig vom
Arbeitsverzeichnis, und der Watchdog setzt zusaetzlich FRAME_CONFIG_PATH auf
den absoluten Pfad der geladenen Config, damit `core` unabhaengig vom eigenen
Arbeitsverzeichnis dieselbe Datei liest, die auch der Watchdog gelesen hat.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core" / "src"))


# --- Kommandozeile -----------------------------------------------------------
# Bewusst vor jedem Import aus frame_core: `--help` muss auch dann laufen,
# wenn core/.venv nicht aktiv ist - das ist die Abnahmebedingung.

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=None,
                        help="Pfad zu params.yaml (Default: config/params.yaml "
                             "im Projektwurzelverzeichnis)")
    parser.add_argument("--health", type=Path, default=None,
                        help="Pfad zum Health-Log (Default: health.path aus der Config)")
    parser.add_argument("--host", default=None,
                        help="Ueberschreibt server.host aus der Config")
    parser.add_argument("--port", type=int, default=None,
                        help="Ueberschreibt server.port aus der Config")
    parser.add_argument("--command", default=None,
                        help="Ersetzt den Startbefehl fuer core, als eine Zeile "
                             "(z. B. fuer einen Testlauf ohne echtes core). Default: "
                             "'uv run --project core uvicorn frame_core.api:app "
                             "--host <host> --port <port>'")
    parser.add_argument("--backoff-base", type=float, default=5.0,
                        help="Wartezeit vor dem ersten Neustart in Sekunden (Default 5)")
    parser.add_argument("--backoff-factor", type=float, default=2.0,
                        help="Faktor, um den die Wartezeit je aufeinanderfolgendem "
                             "Absturz waechst (Default 2)")
    parser.add_argument("--backoff-max", type=float, default=300.0,
                        help="Obergrenze der Wartezeit in Sekunden (Default 300 = 5 Min.)")
    parser.add_argument("--stable-after", type=float, default=120.0,
                        help="Lief core mindestens so lange in Sekunden, gilt der naechste "
                             "Absturz wieder als frisch und die Wartezeit beginnt erneut bei "
                             "--backoff-base, statt weiter zu wachsen (Default 120)")
    parser.add_argument("--max-restarts", type=int, default=None,
                        help="Bricht ab, sobald so viele Neustarts erreicht sind (Default: "
                             "unbegrenzt - im Dauerbetrieb soll der Watchdog nicht von "
                             "selbst aufgeben)")
    parser.add_argument("--shutdown-timeout", type=float, default=15.0,
                        help="Wartezeit auf ein sauberes Prozessende (core.terminate()), "
                             "bevor hart nachgeholfen wird (Default 15 s)")
    return parser


# --- Prozesssteuerung ---------------------------------------------------------

class _ShutdownFlag:
    """Wird von einem Signal-Handler gesetzt, ausserhalb jeder Blockade lesbar."""

    def __init__(self) -> None:
        self.requested = False

    def request(self, signum, frame) -> None:  # noqa: ARG002 - Signal-Handler-Signatur
        self.requested = True


def install_signal_handlers(flag: _ShutdownFlag) -> None:
    signal.signal(signal.SIGINT, flag.request)
    try:
        signal.signal(signal.SIGTERM, flag.request)
    except (AttributeError, ValueError):
        # SIGTERM ist unter Windows nicht in jeder Startart zustellbar - Ctrl+C
        # (SIGINT) bleibt der verlaessliche Weg dort.
        pass


def _start_child(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    """Startet core als Kindprozess.

    Bewusst kein `shell=True`: `command` bleibt eine reine Argumentliste ohne
    Quoting-Fallstricke.
    """
    return subprocess.Popen(command, cwd=str(cwd), env=env)  # noqa: S603


def _wait_for_exit(proc: subprocess.Popen, shutdown: _ShutdownFlag,
                   poll_interval: float = 0.5) -> int | None:
    """Blockiert, bis der Kindprozess endet oder ein Shutdown angefordert wird.

    Kein blosses `proc.wait()`: Der Watchdog muss auf Ctrl+C reagieren koennen,
    auch waehrend core laeuft.
    """
    while True:
        code = proc.poll()
        if code is not None:
            return code
        if shutdown.requested:
            return None
        time.sleep(poll_interval)


def _sleep_interruptible(seconds: float, shutdown: _ShutdownFlag,
                         poll_interval: float = 0.5) -> None:
    deadline = time.monotonic() + seconds
    while not shutdown.requested:
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            return
        time.sleep(min(poll_interval, remaining))


def _terminate(proc: subprocess.Popen, timeout: float) -> None:
    """Beendet den Kindprozess: erst hoeflich (terminate), dann hart (kill).

    Hinweis zur Plattform, keine fachliche Annahme im Sinn von
    docs/annahmen.md: `uv run ...` ersetzt sich unter Linux - der
    Zielplattform (CLAUDE.md Regel 6) - per exec() durch den eigentlichen
    Prozess, terminate() erreicht dort also core direkt. Unter Windows bleibt
    `uv` ein eigener Wrapper-Prozess; terminate() beendet dort zuverlaessig nur
    `uv` selbst, ein Enkelprozess koennte theoretisch verwaisen. Fuer den
    Entwicklungsbetrieb unschaedlich (der Kindprozess haengt nicht an
    Simulationszustand, ein Snapshot uebersteht das), auf der Zielplattform
    nicht relevant. Getestet in beiden Zweigen (Absturz und sauberer
    Shutdown), siehe Bericht zur Abnahme dieses Skripts.
    """
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _previous_restart_count(path: Path, run_name: str) -> int:
    """Liest den zuletzt bekannten Neustartzaehler aus einem vorhandenen Log.

    Ohne das wuerde ein neu gestarteter Watchdog (z. B. nach einem
    Systemneustart im Feldbetrieb) wieder bei null anfangen - der Zaehler soll
    aber ueber die gesamte Laufzeit eines benannten Laufs Bestand haben, nicht
    nur ueber eine einzelne Watchdog-Sitzung.
    """
    if not path.exists():
        return 0
    highest = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("source") != "watchdog" or record.get("run") != run_name:
                continue
            highest = max(highest, int(record.get("restarts", 0)))
    return highest


def _default_command(host: str, port: int) -> list[str]:
    return ["uv", "run", "--project", "core", "uvicorn", "frame_core.api:app",
            "--host", host, "--port", str(port)]


# --- Hauptschleife -------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    # Erst hier importiert - siehe Modul-Docstring: `--help` soll ohne diese
    # Abhaengigkeiten laufen.
    from frame_core.config import load_config  # noqa: PLC0415
    from frame_core.health.log import HealthLog  # noqa: PLC0415

    config_path = (args.config or ROOT / "config" / "params.yaml").resolve()
    app_config = load_config(config_path)
    values = app_config.values

    health_path = (args.health or ROOT / values.health.path).resolve()
    health = HealthLog(health_path)
    run_name = values.run.name
    health.restart_count = _previous_restart_count(health.path, run_name)

    host = args.host or values.server.host
    port = args.port or values.server.port

    if args.command:
        command = shlex.split(args.command, posix=(os.name != "nt"))
    else:
        command = _default_command(host, port)

    # FRAME_CONFIG_PATH als ABSOLUTER Pfad: `core` liest damit dieselbe Config,
    # die auch der Watchdog gelesen hat, unabhaengig vom Arbeitsverzeichnis, in
    # dem `command` tatsaechlich laeuft. FRAME_HOST/FRAME_PORT halten den
    # internen Konfigurationsstand (u. a. fuer GET /config) deckungsgleich mit
    # dem tatsaechlichen Bind, den --host/--port an uvicorn uebergeben.
    child_env = os.environ.copy()
    child_env["FRAME_CONFIG_PATH"] = str(config_path)
    child_env["FRAME_HOST"] = str(host)
    child_env["FRAME_PORT"] = str(port)

    shutdown = _ShutdownFlag()
    install_signal_handlers(shutdown)

    print(f"[watchdog] core: {' '.join(command)}", file=sys.stderr)
    print(f"[watchdog] Health-Log: {health.path}", file=sys.stderr)
    print(f"[watchdog] bisherige Neustarts fuer Lauf {run_name!r}: "
          f"{health.restart_count}", file=sys.stderr)

    health.append(source="watchdog", event="watchdog_started", run=run_name,
                  command=" ".join(command), cwd=str(ROOT))

    backoff = args.backoff_base
    attempt = 0
    exit_code = 0

    while not shutdown.requested:
        attempt += 1
        start = time.monotonic()
        try:
            proc = _start_child(command, ROOT, child_env)
        except OSError as exc:
            # Der Startbefehl selbst schlaegt fehl (z. B. `uv` nicht im PATH).
            # Das ist ebenfalls ein Fall fuer Neustart-mit-Backoff, nicht fuer
            # ein stilles Ende des Watchdogs - genau der Zustand, den ein
            # unbeaufsichtigtes System ueberleben soll.
            health.note_restart()
            health.append(source="watchdog", event="start_failed", run=run_name,
                          error=str(exc), attempt=attempt, backoff_s=round(backoff, 1))
            print(f"[watchdog] Start fehlgeschlagen: {exc}. Neuer Versuch "
                  f"Nr. {health.restart_count} in {backoff:.1f} s.", file=sys.stderr)
            _sleep_interruptible(backoff, shutdown)
            backoff = min(backoff * args.backoff_factor, args.backoff_max)
            continue

        code = _wait_for_exit(proc, shutdown)
        uptime = time.monotonic() - start

        if shutdown.requested:
            _terminate(proc, args.shutdown_timeout)
            health.append(source="watchdog", event="watchdog_stopped", run=run_name,
                          uptime_s=round(uptime, 1))
            print(f"[watchdog] Beenden angefordert, core gestoppt nach "
                  f"{uptime:.1f} s.", file=sys.stderr)
            break

        if uptime >= args.stable_after:
            # core lief lange genug, um als eigenstaendiger Absturz zu gelten,
            # nicht als Folge eines vorherigen. Die Wartezeit faengt wieder bei
            # der Basis an, statt unbegrenzt weiterzuwachsen - sonst wuerde ein
            # System, das ueber Wochen laeuft und alle paar Tage einmal
            # abstuerzt, am Ende minutenlange Wartezeiten fuer einen einzelnen,
            # isolierten Absturz ansammeln.
            backoff = args.backoff_base

        health.note_restart()
        health.append(source="watchdog", event="core_exited", run=run_name,
                      exit_code=code, uptime_s=round(uptime, 1), attempt=attempt,
                      backoff_s=round(backoff, 1))
        print(f"[watchdog] core beendet (Code {code}) nach {uptime:.1f} s. "
              f"Neustart Nr. {health.restart_count} in {backoff:.1f} s.", file=sys.stderr)

        if args.max_restarts is not None and health.restart_count >= args.max_restarts:
            health.append(source="watchdog", event="max_restarts_reached", run=run_name)
            print(f"[watchdog] Obergrenze von {args.max_restarts} Neustarts erreicht. "
                  f"Ende.", file=sys.stderr)
            exit_code = 1
            break

        _sleep_interruptible(backoff, shutdown)
        backoff = min(backoff * args.backoff_factor, args.backoff_max)

    return exit_code


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
