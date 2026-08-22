"""Social Agent parent — receives buzz packets from child agents."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


class SocialAgent:
    def __init__(self, on_forward: Callable[[dict[str, Any]], None] | None = None):
        self.name = "social_agent"
        self.status = "online"
        self.current_action = "Listening for social buzz."
        self.inbox: list[dict[str, Any]] = []
        self.on_forward = on_forward

    def receive_from_sub_agent(self, item: dict[str, Any]) -> dict[str, Any]:
        packet = {
            **item,
            "routed_by": self.name,
            "routed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.inbox.append(packet)
        if len(self.inbox) > 300:
            self.inbox = self.inbox[-300:]
        self.current_action = f"Got {item.get('subreddit') or item.get('sector') or 'buzz'} from {item.get('agent_name')}."
        if self.on_forward:
            self.on_forward(packet)
        return packet
