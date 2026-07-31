"""Tests der Chronikpipeline: beide Backends, HTTP-Aufruf gemockt.

Kein echtes Modell noetig - `httpx.AsyncClient.post` wird durch ein
Testdouble ersetzt, das feste Antworten liefert. Geprueft wird die
Sicherheitseigenschaft aus base.py und two_step.py: Kommt kein belegbarer,
inhaltlich tragfaehiger Eintrag zustande, liefert `write()` **kein** Ergebnis
statt eines fragwuerdigen. "Kein Eintrag" ist hier immer der richtige
Vergleichspunkt fuer "kein Ereignis, ueber das man schreiben koennte" - ein
fehlender Eintrag ist ein Datenausfall, ein erfundener waere ein Befund, der
nie stattgefunden hat (Expose 6.4).
"""

from __future__ import annotations

import asyncio

import pytest

from frame_core.chronicle.base import DetectedEvent
from frame_core.chronicle.single import SingleChronicle
from frame_core.chronicle.two_step import TwoStepChronicle


class FakeResponse:
    """Steht fuer `httpx.Response`, ohne echtes HTTP."""

    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


class FakeClient:
    """Steht fuer `httpx.AsyncClient`: liefert die naechste Antwort aus einer
    Warteschlange, eine je `post`-Aufruf - so wie chronicler und verifier
    nacheinander aufgerufen werden."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls = 0

    async def post(self, url, json=None, headers=None):  # noqa: ARG002
        self.calls += 1
        if not self._replies:
            raise AssertionError("FakeClient: mehr Aufrufe als vorbereitete Antworten")
        return FakeResponse(self._replies.pop(0))


def event() -> DetectedEvent:
    return DetectedEvent(
        event_type="bloom",
        tick=92160,
        metrics={"producer_biomass": 0.3812, "rolling_median": 0.1904},
        weather={"precipitation": 2.4},
    )


def run(coro):
    return asyncio.run(coro)


# --- SingleChronicle ---------------------------------------------------------

def test_single_chronicle_liefert_beleg_eintrag_bei_gedeckten_zahlen(app_config):
    client = FakeClient(["Die Produzentenbiomasse liegt bei 0,38."])
    chronicle = SingleChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is not None
    assert entry.backend == "single"
    assert entry.metrics_ref == event().all_numbers()
    assert client.calls == 1


def test_single_chronicle_ohne_belegbaren_text_liefert_keinen_eintrag(app_config):
    """Kein Ereignis ohne Beleg: Jede Antwort nennt eine erfundene Zahl, das
    Guardrail verwirft sie bei jedem Versuch - am Ende steht kein Eintrag."""
    retries = app_config.values.chronicle.guardrail_max_retries
    client = FakeClient(["Die Biomasse stieg um 17 Prozent."] * (retries + 1))
    chronicle = SingleChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is None
    assert client.calls == retries + 1


def test_single_chronicle_leere_antworten_liefern_keinen_eintrag(app_config):
    """Der leere String tritt auf, wenn max_tokens das Denkbudget eines
    Reasoning-Modells nicht ueberlebt (docs/annahmen.md A8). Auch dann: kein
    Eintrag statt eines fehlenden."""
    retries = app_config.values.chronicle.guardrail_max_retries
    client = FakeClient([""] * (retries + 1))
    chronicle = SingleChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is None


# --- TwoStepChronicle ---------------------------------------------------------

def test_two_step_chronicle_liefert_eintrag_wenn_verifier_bestaetigt(app_config):
    client = FakeClient([
        "Die Produzentenbiomasse liegt bei 0,38.",   # chronicler
        "Die Produzentenbiomasse liegt bei 0,38.",   # verifier: unveraendert
    ])
    chronicle = TwoStepChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is not None
    assert entry.backend == "verified"
    assert entry.text == "Die Produzentenbiomasse liegt bei 0,38."
    assert client.calls == 2


def test_two_step_chronicle_uebernimmt_die_korrektur_des_verifiers(app_config):
    client = FakeClient([
        "Die Produzentenbiomasse stieg wegen des Regens auf 0,38.",  # chronicler
        "Die Produzentenbiomasse liegt bei 0,38.",                   # verifier: korrigiert
    ])
    chronicle = TwoStepChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is not None
    assert entry.text == "Die Produzentenbiomasse liegt bei 0,38."


def test_two_step_chronicle_ohne_chronicler_beleg_liefert_keinen_eintrag(app_config):
    """Scheitert schon der chronicler-Schritt am numerischen Guardrail, gibt
    es fuer den verifier nichts zu pruefen - er wird gar nicht erst
    aufgerufen."""
    retries = app_config.values.chronicle.guardrail_max_retries
    client = FakeClient(["Die Biomasse stieg um 17 Prozent."] * (retries + 1))
    chronicle = TwoStepChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is None
    assert client.calls == retries + 1


def test_two_step_chronicle_verifier_verwirft_liefert_keinen_eintrag(app_config):
    """Der Fall, fuer den es den Verifier gibt: keine falsche Zahl, aber eine
    Kausalitaet, die aus den Zahlen nicht hervorgeht. Der Verifier verwirft -
    kein Eintrag."""
    client = FakeClient([
        "Die Produzentenbiomasse stieg wegen des Regens auf 0,38.",  # chronicler
        "VERWORFEN",                                                 # verifier
    ])
    chronicle = TwoStepChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is None


def test_two_step_chronicle_verifier_mit_erfundener_zahl_liefert_keinen_eintrag(app_config):
    """Auch eine 'Korrektur' des Verifiers durchlaeuft das Guardrail erneut:
    Fuehrt sie eine nicht belegte Zahl ein, entsteht kein Eintrag - der
    Verifier wird nicht blind uebernommen."""
    client = FakeClient([
        "Die Produzentenbiomasse liegt bei 0,38.",           # chronicler
        "Die Biomasse liegt bei 0,38, nach 24 Stunden.",     # verifier erfindet "24"
    ])
    chronicle = TwoStepChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is None


def test_two_step_chronicle_verifier_fehlschlag_liefert_keinen_eintrag(app_config):
    """Ein leerer Verifier-Aufruf ist kein Freibrief fuer den unverifizierten
    Entwurf - auch dann kein Eintrag."""
    client = FakeClient([
        "Die Produzentenbiomasse liegt bei 0,38.",  # chronicler
        "",                                          # verifier: leer
    ])
    chronicle = TwoStepChronicle(app_config.values.chronicle, client)

    entry = run(chronicle.write(event()))

    assert entry is None


# --- Umschaltbarkeit ----------------------------------------------------------

def test_backend_name_entspricht_der_config(app_config):
    """`chronicle.name` landet als `backend` in jedem Eintrag und in
    GET /health - darueber ist im laufenden Betrieb sichtbar, welcher Weg
    aktiv ist, ohne Codeaenderung."""
    single = SingleChronicle(app_config.values.chronicle)
    verified = TwoStepChronicle(app_config.values.chronicle)
    assert single.name == "single"
    assert verified.name == "verified"
    assert app_config.values.chronicle.backend in {"single", "verified"}
