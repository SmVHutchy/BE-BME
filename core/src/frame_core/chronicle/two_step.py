"""TwoStepChronicle - zwei Rollen, zwei schlichte httpx-Aufrufe, kein Framework.

Ersetzt die urspruenglich vorgesehene CrewAI-Anbindung. Grund der Streichung:
Das Expose nennt Agenten nur zweimal, beide Male als Abgrenzung (Expose 3.4
und 5, "kein Multi-Agenten-Dialogsystem") - CrewAI selbst kommt im Expose
nirgends vor. Die Zwei-Rollen-Idee (`chronicler` formuliert, `verifier`
prueft) bleibt, das Framework faellt weg.

Ablauf:

    1. chronicler  - exakt `SingleChronicle`. Gleiche Prompts, gleiche
                     Guardrail-Wiederholung. Hier wird nichts neu erfunden;
                     dieser Schritt wird intern an `SingleChronicle`
                     delegiert.
    2. verifier    - bekommt den Entwurf UND dieselben Kennzahlen und prueft
                     *Aussagen*, nicht Zahlen: Behauptet der Text eine
                     Kausalitaet oder Bewertung, die aus den Zahlen nicht
                     hervorgeht? Er bestaetigt, korrigiert oder verwirft.

Arbeitsteilung zwischen Guardrail und Verifier (CLAUDE.md, guard.py):

    guard.py   prueft Zahlen mechanisch, deterministisch, ohne Modellaufruf.
               Das bleibt und laeuft ZUERST - hier zweimal: einmal innerhalb
               des chronicler-Schritts (mit Wiederholung, siehe single.py),
               ein zweites Mal NACH dem verifier-Schritt. Der zweite Lauf ist
               kein Misstrauen gegen den ersten, sondern eine Eigenschaft des
               Ablaufs: Der Verifier darf Text streichen oder umformulieren,
               und genau dabei koennte er unbemerkt eine neue Zahl einfuehren
               (etwa eine vermeintlich gerundete). Was Python mechanisch
               pruefen kann, wird nicht dem Modell ueberlassen - auch nicht
               dem zweiten Modellaufruf.
    verifier   prueft Aussagen - inhaltlich, nicht numerisch. Das kann nur ein
               Modell beurteilen.

Zwei Modellaufrufe pro Eintrag sind langsamer als einer (siehe base.py); die
Chronik ist im Expose Pflichtumfang, dieser Weg ist es nicht - `single` bleibt
die Rueckfallebene.
"""

from __future__ import annotations

import logging

import httpx

from frame_core.chronicle.base import ChronicleEntry, DetectedEvent
from frame_core.chronicle.guard import find_unsupported_numbers
from frame_core.chronicle.single import (
    SingleChronicle,
    call_model,
    format_numbers,
    load_prompt,
)
from frame_core.config import ChronicleConfig

logger = logging.getLogger(__name__)

# Antwortmarker des Verifiers, wenn der Entwurf nicht reparierbar ist. Kein
# Konfigurationswert (Regel 7 betrifft Zahlen, nicht Protokollworte), aber
# fest an den Wortlaut von prompts/verifier_system_de.txt gebunden - wird der
# Prompt geaendert, muss dieser Marker mitgehen.
DISCARD_MARKER = "VERWORFEN"


class TwoStepChronicle:
    """Chronicler formuliert, Verifier prueft die Aussagen - zwei Aufrufe."""

    name = "verified"

    def __init__(self, config: ChronicleConfig,
                 client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._client = client
        # Der chronicler-Schritt IST SingleChronicle, nicht nur aehnlich dazu -
        # exakt dieselben Prompts, exakt dasselbe Guardrail mit Wiederholung.
        self._chronicler = SingleChronicle(config, client)

    def build_verifier_messages(self, event: DetectedEvent,
                                 draft: str) -> list[dict[str, str]]:
        system = load_prompt("verifier_system", self._config.language)
        template = load_prompt("verifier_user", self._config.language)
        user = template.format(
            draft=draft,
            event_type=event.event_type,
            tick=event.tick,
            metrics=format_numbers(event.metrics),
            weather=format_numbers(event.weather),
        )
        return [{"role": "system", "content": system},
                {"role": "user", "content": user}]

    async def _run_verifier(self, event: DetectedEvent, draft: str) -> str | None:
        messages = self.build_verifier_messages(event, draft)
        try:
            text = await call_model(self._config, messages, self._client)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("Chronik: Verifier-Aufruf fehlgeschlagen (%s) - "
                           "Entwurf verworfen statt unverifiziert uebernommen", exc)
            return None

        if not text:
            logger.warning("Chronik: Verifier lieferte eine leere Antwort - "
                           "Entwurf verworfen")
            return None

        if text.strip().upper().startswith(DISCARD_MARKER):
            logger.info("Chronik: Verifier hat den Entwurf verworfen "
                        "(Ereignis %s, Tick %d)", event.event_type, event.tick)
            return None

        return text.strip()

    async def write(self, event: DetectedEvent) -> ChronicleEntry | None:
        """Formuliert einen Entwurf und laesst ihn inhaltlich pruefen.

        Scheitert bereits der chronicler-Schritt (kein belegbarer Entwurf nach
        allen Wiederholungen), gibt es nichts zu verifizieren - `None` wie bei
        `SingleChronicle`. Verwirft der Verifier den Entwurf, oder fuehrt er
        beim Korrigieren eine nicht belegte Zahl ein, entsteht ebenfalls
        **kein** Eintrag statt eines fragwuerdigen.
        """
        draft_entry = await self._chronicler.write(event)
        if draft_entry is None:
            return None

        verified_text = await self._run_verifier(event, draft_entry.text)
        if verified_text is None:
            return None

        # Zweiter, abschliessender Guardrail-Lauf - siehe Moduldocstring.
        unsupported = find_unsupported_numbers(verified_text, draft_entry.metrics_ref)
        if unsupported:
            logger.warning("Chronik: Verifier hat nicht belegte Zahlen eingefuehrt "
                           "%s - Ereignis %s bei Tick %d bleibt ohne Text",
                           unsupported, event.event_type, event.tick)
            return None

        return ChronicleEntry(text=verified_text, metrics_ref=draft_entry.metrics_ref,
                              backend=self.name, event_type=event.event_type,
                              tick=event.tick)
