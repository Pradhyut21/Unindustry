"""
HITL Router — surfaces low-confidence fields to the human review queue.

This agent doesn't do inference — it just emits the SSE event that tells
the frontend how many fields need human attention and where to find them.
The actual queue population happens in the orchestrator.
"""

from __future__ import annotations

import uuid

from api.agents.base import BaseAgent


class HITLRouter(BaseAgent):
    """Emits the HITL routing event after low-confidence fields are queued."""

    name = "hitl_router"

    async def run(  # type: ignore[override]
        self,
        product_id: uuid.UUID,
        hitl_count: int = 0,
        **kwargs,
    ) -> None:
        if hitl_count == 0:
            await self.emit_event(
                product_id,
                "agent_complete",
                "All fields verified — no human review needed.",
                data={"hitl_count": 0},
            )
        else:
            await self.emit_event(
                product_id,
                "agent_complete",
                f"{hitl_count} field(s) routed to human review queue.",
                data={"hitl_count": hitl_count, "review_url": f"/review"},
            )
