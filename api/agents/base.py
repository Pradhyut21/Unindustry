"""
Base agent class.

All agents inherit from BaseAgent, which gives them:
  - emit_event(): publishes an SSE event for this pipeline run
  - A structured logger
  - A standard run() interface
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

import structlog


class BaseAgent(ABC):
    """
    Abstract base for all ProductTruth pipeline agents.

    Subclasses must implement run().
    All agents receive a product_id so they can load/persist state,
    and emit events that are streamed to the frontend via SSE.
    """

    name: str = "base_agent"

    def __init__(self) -> None:
        self.logger = structlog.get_logger(self.__class__.__name__)

    async def emit_event(
        self,
        product_id: uuid.UUID,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        Publish an SSE event for this product's pipeline stream.
        Agents call this to report start, progress, completion, or errors.
        """
        from api.routers.stream import publish_event

        payload: dict[str, Any] = {
            "event_type": event_type,
            "agent_name": self.name,
            "message": message,
        }
        if data:
            payload.update(data)

        await publish_event(str(product_id), payload)
        self.logger.info(event_type, agent=self.name, message=message)

    @abstractmethod
    async def run(self, product_id: uuid.UUID, **kwargs: Any) -> Any:
        """Execute this agent's work for the given product."""
        ...
