"""SingleChronicle - ein Modellaufruf, ohne Framework.

Die Pflicht-Rueckfallebene. Bewusst **ohne CrewAI-Import**: Wenn dieser Weg das
Framework braeuchte, waere er keine Rueckfallebene. Es genuegt `httpx` gegen den
OpenAI-kompatiblen Endpunkt.

Der Endpunkt /v1/chat/completions unterstuetzt laut LM Studio keine MCPs. Das
ist hier erwuenscht: Der Chronist bekommt keine Werkzeuge, sondern
ausschliesslich die uebergebenen Zahlen. Koennte er die Metrikdatenbank selbst
abfragen, hielte `metrics_ref` nicht mehr fest, was er gesehen hat.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from frame_core.chronicle.base import ChronicleEntry, DetectedEvent
from frame_core.chronicle.guard import find_unsupported_numbers
from frame_core.config import ChronicleConfig

logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str, language: str) -> str:
    return (PROMPT_DIR / f"{name}_{language}.txt").read_text(encoding="utf-8")


def format_numbers(values: dict) -> str:
    """Kennzahlen als schlichte Liste.

    Deutsches Dezimalkomma, weil der Eintrag deutsch ist und das Modell die
    Schreibweise sonst uneinheitlich mischt.
    """
    if not values:
        return "(keine)"
    lines = []
    for key, value in values.items():
        if isinstance(value, float):
            lines.append(f"- {key}: {value:.4f}".replace(".", ","))
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


async def call_model(config: ChronicleConfig, messages: list[dict[str, str]],
                      client: httpx.AsyncClient | None) -> str:
    """Ein einzelner Aufruf gegen den lokalen OpenAI-kompatiblen Endpunkt.

    Modulweite Funktion statt Methode, damit `TwoStepChronicle` denselben
    Aufrufmechanismus fuer den `verifier`-Schritt nutzt, ohne ihn zu
    duplizieren oder auf ein privates Attribut von `SingleChronicle`
    zuzugreifen. Beide Rollen sprechen mit demselben Modell am selben
    Endpunkt, nur mit unterschiedlichen Prompts.
    """
    payload: dict = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        # Deckt Denkbudget UND Eintrag ab. Ein Reasoning-Modell verbraucht
        # den groessten Teil davon, bevor ein Zeichen Text entsteht; ein zu
        # kleiner Wert liefert stillschweigend einen leeren String.
        "max_tokens": config.max_tokens,
    }
    if config.reasoning_effort:
        payload["reasoning_effort"] = config.reasoning_effort
    if config.disable_thinking:
        # Daempft das Reasoning-Budget wirksam (gemessen 2018 statt bis zu
        # 4000 Tokens). Modelle ohne Reasoning ignorieren den Schluessel.
        payload["chat_template_kwargs"] = {"enable_thinking": False}

    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=config.timeout_s)
    try:
        response = await active_client.post(
            f"{config.base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {config.api_key}"},
        )
        response.raise_for_status()
        data = response.json()
    finally:
        if owns_client:
            await active_client.aclose()

    return (data["choices"][0]["message"].get("content") or "").strip()


class SingleChronicle:
    """Ein Aufruf, strikter Prompt, numerisches Guardrail mit Wiederholung."""

    name = "single"

    def __init__(self, config: ChronicleConfig,
                 client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._client = client

    def build_messages(self, event: DetectedEvent) -> list[dict[str, str]]:
        system = load_prompt("chronicler_system", self._config.language)
        template = load_prompt("event_user", self._config.language)
        user = template.format(
            event_type=event.event_type,
            tick=event.tick,
            metrics=format_numbers(event.metrics),
            weather=format_numbers(event.weather),
        )
        return [{"role": "system", "content": system},
                {"role": "user", "content": user}]

    async def _complete(self, messages: list[dict[str, str]]) -> str:
        return await call_model(self._config, messages, self._client)

    async def write(self, event: DetectedEvent) -> ChronicleEntry | None:
        """Formuliert einen Eintrag und prueft jede Zahl darin.

        Bei einer nicht belegten Zahl wird der Entwurf verworfen und ein neuer
        angefordert, hoechstens `guardrail_max_retries` mal. Bleibt es dabei,
        entsteht **kein** Eintrag: Ein fehlender Eintrag ist ein Datenausfall,
        ein erfundener waere ein Befund, der nie stattgefunden hat - und genau
        das schliesst Expose 6.4 aus.
        """
        allowed = event.all_numbers()
        messages = self.build_messages(event)

        for attempt in range(self._config.guardrail_max_retries + 1):
            try:
                text = await self._complete(messages)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                logger.warning("Chronik: Modellaufruf fehlgeschlagen (%s)", exc)
                return None

            if not text:
                # Passiert, wenn max_tokens das Denkbudget nicht ueberlebt.
                logger.warning("Chronik: leere Antwort (Versuch %d). Reicht "
                               "chronicle.max_tokens = %d fuer das Reasoning-Budget?",
                               attempt + 1, self._config.max_tokens)
                continue

            unsupported = find_unsupported_numbers(text, allowed)
            if not unsupported:
                return ChronicleEntry(text=text, metrics_ref=allowed,
                                      backend=self.name, event_type=event.event_type,
                                      tick=event.tick)

            logger.warning("Chronik: nicht belegte Zahlen %s (Versuch %d)",
                           unsupported, attempt + 1)
            messages = [*messages, {"role": "assistant", "content": text},
                        {"role": "user", "content":
                         "Diese Zahlen kommen in den Kennzahlen nicht vor: "
                         f"{', '.join(unsupported)}. Schreibe den Eintrag neu und "
                         "verwende ausschliesslich die uebergebenen Werte."}]

        logger.error("Chronik: kein belegbarer Eintrag nach %d Versuchen - "
                     "Ereignis %s bei Tick %d bleibt ohne Text",
                     self._config.guardrail_max_retries + 1, event.event_type, event.tick)
        return None
