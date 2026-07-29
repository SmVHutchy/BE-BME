"""frame_core — der Nicht-Simulationsteil des Systems.

Haelt Umweltdienst, Audiodienst, Metrikspeicher, Regeldetektor und
Chronikpipeline und liefert die Chronik aus. Rechnet nichts am Oekosystem:
Der Simulationszustand lebt ausschliesslich in `sim/` auf der GPU.

Der Vertrag zur Simulation ist in docs/contract.md spezifiziert. `core` kann
`sim` ausschliesslich ueber die Nachrichten `env` und `pulse` beeinflussen -
das sind die sechs Kopplungen aus docs/mapping.md und sonst nichts.

Ab Phase 1 entstehen hier:
    config    Laden und Typisieren von config/params.yaml
    contract  Pydantic-Modelle der vier Vertragsnachrichten
    api       FastAPI-Anwendung, WebSocket-Server, HTTP-Endpunkte
"""
