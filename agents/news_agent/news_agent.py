"""Parent News Agent / CORE-01.

Receives packets from satellite agents, analyzes the combined stream,
and forwards both raw items and the briefing to the central orb.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from core_analyzer import analyze_inbox

ROOT = Path(__file__).resolve().parent


class NewsAgent:
    def __init__(self, on_forward: Callable[[dict[str, Any]], None] | None = None):
        self.name = "news_agent"
        self.connected_to = "central_orb"
        self.status = "online"
        self.current_action = "Listening for satellite packets."
        self.inbox: list[dict[str, Any]] = []
        self.analysis: dict[str, Any] | None = None
        self.on_forward = on_forward

    def receive_from_sub_agent(self, item: dict[str, Any]) -> dict[str, Any]:
        packet = {
            **item,
            "routed_by": self.name,
            "routed_to": self.connected_to,
            "routed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.inbox.append(packet)
        if len(self.inbox) > 900:
            self.inbox = self.inbox[-900:]
        self.current_action = (
            f"Received {item.get('sector', 'item')} packet from {item.get('agent_name', 'agent')}."
        )
        if self.on_forward:
            self.on_forward(packet)
        return packet

    def analyze(self) -> dict[str, Any]:
        self.status = "analyzing"
        self.current_action = f"Scoring {len(self.inbox)} satellite packets..."
        self.analysis = analyze_inbox(self.inbox)
        up_n = len(self.analysis.get("companies_up") or [])
        self.status = "online"
        self.current_action = f"Briefing ready. {up_n} companies leaning up on news-flow."
        return self.analysis
