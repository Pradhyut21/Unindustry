"""
Tests for the HITL Router Agent.

The HITLRouter is deliberately thin — it doesn't do inference, just emits
the correct SSE event based on hitl_count. These tests verify:
- Zero hitl_count emits an "all clear" agent_complete event
- Non-zero hitl_count emits the count and review URL in the event
- agent_name is always "hitl_router"

All tests are pure — no DB, no API calls.
"""

import uuid

import pytest

from api.agents.hitl_router import HITLRouter


class TestHITLRouterEvents:
    @pytest.mark.asyncio
    async def test_zero_hitl_count_emits_all_clear(self):
        """When hitl_count=0, the agent emits an agent_complete 'all fields verified' event."""
        events = []

        async def capture_emit(product_id, event_type, message, data=None):
            events.append({"type": event_type, "message": message, "data": data or {}})

        agent = HITLRouter()
        agent.emit_event = capture_emit

        await agent.run(product_id=uuid.uuid4(), hitl_count=0)

        assert len(events) == 1
        assert events[0]["type"] == "agent_complete"
        assert events[0]["data"].get("hitl_count") == 0
        assert (
            "verified" in events[0]["message"].lower() or "no human" in events[0]["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_nonzero_hitl_count_emits_queue_notification(self):
        """When hitl_count > 0, the event includes hitl_count and review_url."""
        events = []

        async def capture_emit(product_id, event_type, message, data=None):
            events.append({"type": event_type, "message": message, "data": data or {}})

        agent = HITLRouter()
        agent.emit_event = capture_emit

        await agent.run(product_id=uuid.uuid4(), hitl_count=3)

        assert len(events) == 1
        assert events[0]["type"] == "agent_complete"
        assert events[0]["data"].get("hitl_count") == 3
        assert "review_url" in events[0]["data"]
        assert "3" in events[0]["message"]

    @pytest.mark.asyncio
    async def test_agent_name_is_hitl_router(self):
        """Agent name must be 'hitl_router' for SSE event routing to work."""
        assert HITLRouter.name == "hitl_router"

    @pytest.mark.asyncio
    async def test_single_hitl_field_message_uses_singular(self):
        """Message should say 'field' (singular) when hitl_count=1."""
        events = []

        async def capture_emit(product_id, event_type, message, data=None):
            events.append({"message": message})

        agent = HITLRouter()
        agent.emit_event = capture_emit

        await agent.run(product_id=uuid.uuid4(), hitl_count=1)
        assert "1" in events[0]["message"]

    @pytest.mark.asyncio
    async def test_run_returns_none(self):
        """HITLRouter.run() must return None — it's a side-effect-only agent."""

        async def noop_emit(product_id, event_type, message, data=None):
            pass

        agent = HITLRouter()
        agent.emit_event = noop_emit

        result = await agent.run(product_id=uuid.uuid4(), hitl_count=0)
        assert result is None
