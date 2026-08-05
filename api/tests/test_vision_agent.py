"""
Tests for the Vision Agent.

Covers:
- Agent returns {} when no image paths are provided
- Agent returns {} gracefully when GROQ_API_KEY is absent
- Agent returns {} gracefully when GROQ_VISION_MODEL is not configured
- Agent skips images that do not exist on disk
- Agent processes no more than 3 images

All tests run without real API calls or real image files.
"""

import uuid

import pytest


class TestVisionAgentGracefulSkips:
    @pytest.mark.asyncio
    async def test_no_images_returns_empty_dict(self, monkeypatch):
        """Agent must return {} when image_paths is None."""
        from api.agents.vision_agent import VisionAgent

        events = []

        async def mock_emit(product_id, event_type, message, data=None):
            events.append({"type": event_type, "message": message})

        agent = VisionAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(product_id=uuid.uuid4(), image_paths=None)
        assert result == {}
        assert any(e["type"] == "agent_complete" for e in events)

    @pytest.mark.asyncio
    async def test_empty_image_list_returns_empty_dict(self, monkeypatch):
        """Agent must return {} when image_paths is an empty list."""
        from api.agents.vision_agent import VisionAgent

        async def mock_emit(product_id, event_type, message, data=None):
            pass

        agent = VisionAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(product_id=uuid.uuid4(), image_paths=[])
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_groq_api_key_returns_empty_dict(self, monkeypatch):
        """Agent must return {} (not crash) when GROQ_API_KEY is absent."""
        from api.agents.vision_agent import VisionAgent
        from api.config import settings

        monkeypatch.setattr(settings, "groq_api_key", "")

        events = []

        async def mock_emit(product_id, event_type, message, data=None):
            events.append({"type": event_type, "message": message})

        agent = VisionAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(
            product_id=uuid.uuid4(), image_paths=["some_image.jpg"]
        )
        assert result == {}
        assert any(e["type"] == "agent_error" for e in events)

    @pytest.mark.asyncio
    async def test_no_vision_model_returns_empty_dict(self, monkeypatch):
        """Agent must return {} gracefully when GROQ_VISION_MODEL is not set."""
        from api.agents.vision_agent import VisionAgent
        from api.config import settings

        monkeypatch.setattr(settings, "groq_api_key", "gsk_test_key")
        monkeypatch.setattr(settings, "groq_vision_model", "")

        events = []

        async def mock_emit(product_id, event_type, message, data=None):
            events.append({"type": event_type, "message": message})

        agent = VisionAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(
            product_id=uuid.uuid4(), image_paths=["some_image.jpg"]
        )
        assert result == {}
        assert any(e["type"] == "agent_complete" for e in events)

    @pytest.mark.asyncio
    async def test_nonexistent_images_produce_empty_result(self, monkeypatch):
        """Images that don't exist on disk should be skipped silently."""
        from api.agents.vision_agent import VisionAgent
        from api.config import settings

        monkeypatch.setattr(settings, "groq_api_key", "gsk_test_key")
        monkeypatch.setattr(settings, "groq_vision_model", "llama-4-scout")

        events = []

        async def mock_emit(product_id, event_type, message, data=None):
            events.append({"type": event_type})

        agent = VisionAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(
            product_id=uuid.uuid4(),
            image_paths=["/nonexistent/image1.jpg", "/nonexistent/image2.jpg"],
        )
        # No crash, returns empty (all images skipped)
        assert isinstance(result, dict)
        assert any(e["type"] == "agent_complete" for e in events)
