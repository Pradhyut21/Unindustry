"""
SSE streaming router — clients subscribe here to get live pipeline events.

Pattern:
  1. Client opens GET /api/v1/stream/{product_id}  (SSE connection)
  2. Client POSTs to /api/v1/products/{product_id}/run
  3. Agent events are published to the in-memory event bus
  4. SSE endpoint reads from the bus and streams to the client

This keeps the pipeline fully async and the HTTP layer thin.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory event bus
# Keyed by product_id (str). Each value is an asyncio.Queue of event dicts.
# Sufficient for a single-server demo; replace with Redis pub/sub for scale.
# ---------------------------------------------------------------------------

_event_queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)


def get_queue(product_id: str) -> asyncio.Queue:
    return _event_queues[product_id]


async def publish_event(product_id: str, event: dict) -> None:
    """Called by agents to push an event to the SSE stream for this product."""
    await _event_queues[product_id].put(event)


async def _event_generator(
    product_id: str,
) -> AsyncGenerator[dict, None]:
    queue = get_queue(product_id)
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield {"data": json.dumps(event)}
            if event.get("event_type") in ("pipeline_complete", "pipeline_error"):
                break
        except asyncio.TimeoutError:
            # Keepalive ping so the connection doesn't drop
            yield {"data": json.dumps({"event_type": "ping"})}


@router.get("/{product_id}")
async def stream_pipeline(product_id: uuid.UUID) -> EventSourceResponse:
    """
    SSE endpoint — subscribe before triggering the pipeline run.
    Events: agent_start | agent_complete | agent_error | pipeline_complete | ping
    """
    return EventSourceResponse(_event_generator(str(product_id)))
