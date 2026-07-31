"""FastAPI-Anwendung: WebSocket-Server, Auslieferung, Hintergrundaufgaben.

Fuehrt die Dienste zusammen und haelt den Vertrag aus docs/contract.md ein.

Die eine Regel, die dieses Modul durchsetzt: **`core` kann `sim` ausschliesslich
ueber `env` und `pulse` beeinflussen.** Es gibt keinen Weg, ueber den von hier
aus Felder gesetzt, Masse korrigiert oder Organismen erzeugt werden koennten -
auch nicht "nur zum Ausgleichen". Die Chronikpipeline liest, sie greift nicht
ein (Expose 3.4 und 6.4).
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from frame_core.audio.stub import StubPulseSource
from frame_core.chronicle.base import ChronicleBackend, DetectedEvent
from frame_core.chronicle.single import SingleChronicle
from frame_core.config import AppConfig, load_config
from frame_core.contract import EnvValues, MetricsMessage, parse_incoming
from frame_core.detect.bloom import evaluate_bloom
from frame_core.environment.rawlog import WeatherRawLog
from frame_core.environment.service import EnvironmentService
from frame_core.health.log import HealthLog
from frame_core.metrics.balance import check_balance
from frame_core.metrics.store import MetricsStore

logger = logging.getLogger(__name__)


def build_chronicle_backend(config: AppConfig,
                            client: httpx.AsyncClient | None = None) -> ChronicleBackend:
    """Waehlt das Backend allein anhand der Konfiguration.

    Der Wechsel zwischen `single` und `crew` ist eine Zeile in params.yaml und
    erfordert keine Codeaenderung - das ist die geforderte Rueckfallebene.
    """
    if config.values.chronicle.backend == "crew":
        # Phase 3. Bis dahin ist `single` der einzige gebaute Weg, und ein
        # stiller Rueckfall waere schlechter als ein deutlicher Hinweis.
        from frame_core.chronicle.crew import CrewChronicle  # noqa: PLC0415

        return CrewChronicle(config.values.chronicle)
    return SingleChronicle(config.values.chronicle, client)


@dataclass
class AppState:
    """Laufzeitzustand. Haelt keinen Simulationszustand - der lebt in `sim`."""

    config: AppConfig
    store: MetricsStore
    run_id: int
    environment: EnvironmentService
    pulses: StubPulseSource
    health: HealthLog
    chronicle: ChronicleBackend
    connections: set[WebSocket] = field(default_factory=set)
    tasks: list[asyncio.Task] = field(default_factory=list)

    last_event_world_time: float | None = None
    """Weltzeit des letzten erkannten Ereignisses. `None`, solange im Lauf noch
    keines aufgetreten ist. In Weltzeit, nicht in Stichproben - die Sperrzeit
    soll eine biologische Dauer sein und nicht von `sim.speed` abhaengen
    (docs/annahmen.md A14)."""
    world_time: float = 0.0
    """Zuletzt von `sim` gemeldete Weltzeit in Sekunden. Bestimmt, welches
    Wetter gilt - nicht die Wanduhrzeit (docs/annahmen.md A11)."""
    last_metrics: MetricsMessage | None = None
    last_health: dict = field(default_factory=dict)
    last_env: EnvValues | None = None
    chronicle_task: asyncio.Task | None = None

    async def broadcast(self, payload: dict) -> None:
        """Sendet an alle verbundenen `sim`-Instanzen."""
        for connection in list(self.connections):
            try:
                await connection.send_json(payload)
            except (WebSocketDisconnect, RuntimeError):
                self.connections.discard(connection)


def _state(app: FastAPI) -> AppState:
    return app.state.frame


# --- Hintergrundaufgaben ----------------------------------------------------

async def environment_poll_loop(state: AppState) -> None:
    """Haelt die Stundenwerte passend zur WELTZEIT nach.

    Zwei Ausloeser. Der stuendliche Takt deckt den Feldbetrieb ab, in dem die
    Weltzeit mit der Wanduhr laeuft. `needs_refresh` deckt den Zeitraffer ab, wo
    die Weltzeit die geladene Spanne binnen Sekunden durchlaeuft - ohne diese
    zweite Bedingung bliebe der Lauf im Wetter des Startzeitpunkts stecken, und
    genau daran ist der erste Zeitrafferlauf gescheitert.
    """
    interval = state.config.values.environment.poll_interval_min * 60.0
    elapsed = interval  # beim Start sofort abrufen
    async with httpx.AsyncClient(
            timeout=state.config.values.environment.request_timeout_s) as client:
        while True:
            if elapsed >= interval or state.environment.needs_refresh(state.world_time):
                await state.environment.refresh(state.world_time, client)
                elapsed = 0.0
            await asyncio.sleep(1.0)
            elapsed += 1.0


async def environment_push_loop(state: AppState) -> None:
    """Schickt geglaettete Klimawerte an `sim`, wenn sie sich geaendert haben."""
    interval = state.config.values.environment.push_interval_s
    while True:
        await asyncio.sleep(interval)
        env = state.environment.current_env(state.world_time)
        if env is None:
            continue
        if state.last_env is not None and env == state.last_env:
            continue
        state.last_env = env
        state.store.insert_env(state.run_id, env)
        await state.broadcast({"env": env.model_dump(mode="json")})


async def pulse_forward_loop(state: AppState) -> None:
    """Reicht Ereignispulse an `sim` weiter."""
    while True:
        pulse = await state.pulses.next_pulse()
        await state.broadcast({"pulse": pulse.model_dump(mode="json")})


async def health_loop(state: AppState) -> None:
    """Schreibt in festem Abstand eine Zeile ins Health-Log."""
    config = state.config.values
    while True:
        await asyncio.sleep(config.health.interval_s)
        state.health.append(
            run=config.run.name,
            config_hash=state.config.config_hash,
            connections=len(state.connections),
            metrics_rows=state.store.metrics_count(state.run_id),
            environment=state.environment.status_dict(state.world_time),
            **state.last_health,
        )


# --- Detektor und Chronik ---------------------------------------------------

def evaluate_and_build_event(state: AppState, message: MetricsMessage) -> DetectedEvent | None:
    """Prueft die Bluete-Regel und baut daraus das Ereignis fuer die Chronik.

    Reines Python, kein Modellaufruf. Das Modell bekommt spaeter das **bereits
    erkannte** Ereignis samt Kennzahlen und formuliert daraus einen Text
    (Expose 6.4).
    """
    bloom_config = state.config.values.detector.bloom
    # Auswahl nach WELTZEIT, nicht nach Zeilenzahl (docs/annahmen.md A14).
    seit = message.world_time - bloom_config.window_world_hours * 3600.0
    window = state.store.producer_series_since(state.run_id, seit)
    # Die soeben eingefuegte Stichprobe gehoert nicht in ihre eigene
    # Vergleichsbasis.
    window = window[:-1] if window else window

    seit_ereignis = None
    if state.last_event_world_time is not None:
        seit_ereignis = (message.world_time - state.last_event_world_time) / 3600.0

    result = evaluate_bloom(window, message.mass.producer, seit_ereignis, bloom_config)
    if not result.triggered:
        logger.debug("Detektor: %s", result.reason)
        return None

    logger.info("Detektor: Bluete bei Tick %d - %s", message.tick, result.reason)

    metrics = {
        "producer_biomass": round(result.value, 4),
        "rolling_median": round(result.median, 4),
        "mad": round(result.mad, 4),
        "threshold": round(result.threshold, 4),
        "nutrient": round(message.mass.nutrient, 4),
        "total_mass": round(message.mass.total, 4),
        "occupancy": round(message.occupancy, 4),
    }
    weather: dict[str, float] = {}
    if state.last_env is not None:
        weather = {
            "light": round(state.last_env.light, 4),
            "nutrient_input": round(state.last_env.nutrient_input, 4),
            "rate": round(state.last_env.rate, 4),
        }

    return DetectedEvent(event_type="bloom", tick=message.tick,
                         metrics=metrics, weather=weather)


def chronicle_allowed_now(state: AppState) -> bool:
    """Mindestabstand zwischen zwei Eintraegen - zweite Bremse neben der
    Sperrzeit des Detektors."""
    minimum = state.config.values.chronicle.min_interval_minutes
    if minimum <= 0.0:
        return True
    last = state.store.last_chronicle_time(state.run_id)
    if last is None:
        return True
    return (datetime.now(UTC) - last).total_seconds() >= minimum * 60.0


async def write_chronicle_entry(state: AppState, event: DetectedEvent) -> None:
    """Laesst einen Eintrag formulieren und legt ihn ab.

    Laeuft als Hintergrundaufgabe: Ein Modellaufruf dauert gemessen 19-25 s und
    darf den Empfang der Metriken nicht anhalten.
    """
    try:
        entry = await state.chronicle.write(event)
    except Exception:
        logger.exception("Chronik: Backend %r ist gescheitert", state.chronicle.name)
        return

    if entry is None:
        logger.warning("Chronik: kein belegbarer Eintrag fuer %s bei Tick %d",
                       event.event_type, event.tick)
        return

    entry_id = state.store.insert_chronicle_entry(
        state.run_id, entry.tick, entry.event_type, entry.text,
        entry.metrics_ref, entry.backend)
    logger.info("Chronik: Eintrag %d ueber %s (%s)", entry_id, entry.backend,
                entry.event_type)


async def handle_metrics(state: AppState, message: MetricsMessage) -> None:
    """Nimmt eine Metriknachricht an: speichern, bilanzieren, pruefen."""
    state.store.insert_metrics(state.run_id, message)
    state.last_metrics = message
    # Bestimmt, welches Wetter gilt. Muss vor allem anderen gesetzt werden,
    # damit Detektor und Chronik dieselbe Weltzeit sehen wie der Klimakanal.
    state.world_time = message.world_time


    # Massenbilanz: Residualsaldo, nicht Konstanz.
    initial_total = state.store.first_total(state.run_id)
    if initial_total and initial_total > 0.0:
        mass_config = state.config.values.mass
        balance = check_balance(
            initial_total=initial_total, current_total=message.mass.total,
            inflow_total=message.mass.inflow_total,
            outflow_total=message.mass.outflow_total,
            drift_tolerance_pct=mass_config.drift_tolerance_pct,
            corridor_min=mass_config.corridor_min, corridor_max=mass_config.corridor_max)
        state.last_health.update({
            "tick": message.tick,
            "mass_total": round(message.mass.total, 4),
            "mass_residual_pct": round(balance.residual_pct, 4),
            "mass_within_tolerance": balance.within_tolerance,
            "mass_within_corridor": balance.within_corridor,
        })
        if not balance.within_tolerance:
            logger.warning("Massenbilanz: %.3f %% unerklaerte Masse bei Tick %d "
                           "(Toleranz %.1f %%)", balance.residual_pct, message.tick,
                           mass_config.drift_tolerance_pct)

    event = evaluate_and_build_event(state, message)
    if event is None:
        return

    state.last_event_world_time = message.world_time

    if not chronicle_allowed_now(state):
        logger.info("Chronik: Mindestabstand noch nicht erreicht, Ereignis bei "
                    "Tick %d bleibt ohne Eintrag", event.tick)
        return
    if state.chronicle_task is not None and not state.chronicle_task.done():
        logger.info("Chronik: vorheriger Eintrag laeuft noch, Ereignis bei "
                    "Tick %d wird uebersprungen", event.tick)
        return

    state.chronicle_task = asyncio.create_task(write_chronicle_entry(state, event))


# --- Anwendung --------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=os.environ.get("FRAME_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    config = load_config()
    values = config.values

    store = MetricsStore(values.metrics.db_path)
    run_id = store.start_run(values.run.name, values.run.seed, config.config_hash)
    logger.info("Lauf %d gestartet: %s, Seed %d, Config %s",
                run_id, values.run.name, values.run.seed, config.config_hash[:12])

    state = AppState(
        config=config,
        store=store,
        run_id=run_id,
        environment=EnvironmentService(config, WeatherRawLog(values.metrics.weather_log_path)),
        pulses=StubPulseSource(values.coupling, values.audio.min_pulse_interval_s),
        health=HealthLog(values.health.path),
        chronicle=build_chronicle_backend(config),
    )
    app.state.frame = state

    state.tasks = [
        asyncio.create_task(environment_poll_loop(state)),
        asyncio.create_task(environment_push_loop(state)),
        asyncio.create_task(pulse_forward_loop(state)),
        asyncio.create_task(health_loop(state)),
    ]

    try:
        yield
    finally:
        for task in state.tasks:
            task.cancel()
        for task in state.tasks:
            with suppress(asyncio.CancelledError):
                await task
        store.close()
        logger.info("Lauf %d beendet", run_id)


app = FastAPI(title="Oekosystem im Bilderrahmen - core", lifespan=lifespan)

# `sim` laeuft als eigener Prozess auf einem anderen Port und ist damit
# cross-origin. Die erlaubten Herkuenfte stehen als konkrete Liste in
# params.yaml, nicht als Platzhalter: Auf dem fertigen Objekt steht das Geraet
# im Wohnraum eines Studienhaushalts.
app.add_middleware(
    CORSMiddleware,
    allow_origins=load_config().values.server.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Der Vertrag. `sim` verbindet sich hier als Client."""
    state = _state(websocket.app)
    await websocket.accept()
    state.connections.add(websocket)
    logger.info("sim verbunden (%d Verbindungen)", len(state.connections))

    # Sofort den aktuellen Klimastand schicken, damit eine frisch verbundene
    # Simulation nicht bis zum naechsten Nachfuehrtakt mit Vorgabewerten rechnet.
    env = state.environment.current_env(state.world_time)
    if env is not None:
        state.last_env = env
        await websocket.send_json({"env": env.model_dump(mode="json")})

    try:
        while True:
            payload = await websocket.receive_json()
            message = parse_incoming(payload)
            if isinstance(message, MetricsMessage):
                await handle_metrics(state, message)
            elif message is not None:
                # Betriebstelemetrie. Fliesst ausdruecklich nicht in
                # Metrikzeitreihe, Detektor oder Chronik (docs/annahmen.md A3).
                state.last_health.update({
                    "frame_ms": message.health.frame_ms,
                    "sim_hz": message.health.sim_hz,
                    "heap_mb": message.health.heap_mb,
                    "gl_context_lost": message.health.gl_context_lost,
                    "speed": message.health.speed,
                })
    except WebSocketDisconnect:
        logger.info("sim getrennt")
    finally:
        state.connections.discard(websocket)


@app.get("/config")
async def get_config() -> dict:
    """Die Konfiguration, die `sim` beim Start abholt.

    `core` ist die Quelle der Wahrheit - dadurch existiert params.yaml wirklich
    nur einmal, und kein Zahlenwert im Shader stammt aus einer zweiten Quelle.
    """
    return _state(app).config.public_dict()


@app.get("/chronicle")
async def get_chronicle(limit: int = 20, since: str | None = None) -> dict:
    """Chronikeintraege, neueste zuerst.

    `metrics_ref` enthaelt genau die Zahlen, die dem Modell uebergeben wurden -
    damit ist jede Zahl im Text gegen die Metrikdatenbank pruefbar.
    """
    entries = _state(app).store.recent_chronicle_entries(limit=limit, since=since)
    return {"entries": [entry.as_dict() for entry in entries]}


@app.get("/health")
async def get_health() -> dict:
    state = _state(app)
    return {
        "run": state.config.values.run.name,
        "run_id": state.run_id,
        "config_hash": state.config.config_hash,
        "connections": len(state.connections),
        "metrics_rows": state.store.metrics_count(state.run_id),
        "restarts": state.health.restart_count,
        "environment": state.environment.status_dict(state.world_time),
        "chronicle_backend": state.chronicle.name,
        **state.last_health,
    }


class PulseRequest(BaseModel):
    """Synthetischer Puls fuer den Audio-Stub."""

    band: str = Field(pattern="^(low|high)$")
    level: float = Field(ge=0.0, le=1.0)


@app.post("/debug/pulse")
async def post_debug_pulse(request: PulseRequest) -> dict:
    """Entwicklungswerkzeug: erzeugt einen Ereignispuls von Hand.

    Ersetzt in Prototyp 0 die echte Audioerfassung. Das Interface dahinter ist
    bereits das endgueltige.
    """
    state = _state(app)
    accepted = state.pulses.emit(request.band, request.level)  # type: ignore[arg-type]
    return {"accepted": accepted,
            "reason": None if accepted else "unter Schwelle oder im Mindestabstand"}
