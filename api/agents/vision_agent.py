"""
Vision Agent — extracts product attributes from images using Groq's vision capability.

Uses meta-llama/llama-4-scout-17b-16e-instruct (multimodal) on Groq for fast,
cheap image analysis. Every extracted value is tagged with {source_image, region}
so the citation trail includes the image source.
"""

from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path
from typing import Optional

import structlog

from api.agents.base import BaseAgent
from api.agents.verifier_agent import CandidateValue
from api.config import settings
from api.models.db import SourceType

logger = structlog.get_logger(__name__)

VISION_EXTRACTION_PROMPT = """You are analyzing a product image for an industrial commerce catalog.

Extract ALL product attributes visible in this image. Look for:
- Nameplates, labels, spec plates
- Dimensions marked on the product
- Model numbers, serial numbers, part numbers
- Certification marks (CE, UL, CSA, RoHS, ATEX, IP ratings)
- Voltage/current/power ratings
- Material clues from the product appearance
- Product category based on visual appearance
- Manufacturer branding/logo

Return a JSON object with these fields (include ONLY fields you can actually see):
{
  "model_number": "...",
  "manufacturer": "...",
  "voltage_rating": "...",
  "current_rating": "...",
  "power_rating": "...",
  "ip_rating": "...",
  "certifications": "...",
  "dimensions": "...",
  "weight": "...",
  "material": "...",
  "product_category": "...",
  "description": "brief visual description of the product",
  "region_notes": "which part of the image each value came from"
}

Be conservative — only include values you can actually see. Do NOT guess or hallucinate.
Return ONLY valid JSON."""


def _groq_client():
    from openai import AsyncOpenAI

    return AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )


class VisionAgent(BaseAgent):
    """
    Uses Groq's llama-4-scout vision model to extract product attributes from images.
    Handles up to 3 images per product run.
    """

    name = "vision_agent"

    async def run(
        self,
        product_id: uuid.UUID,
        image_paths: Optional[list[str]] = None,
        **kwargs,
    ) -> dict[str, list[CandidateValue]]:
        if not image_paths:
            await self.emit_event(
                product_id, "agent_complete", "No images provided — skipping vision extraction."
            )
            return {}

        if not settings.groq_api_key:
            await self.emit_event(
                product_id, "agent_error", "No GROQ_API_KEY — vision extraction skipped."
            )
            return {}

        if not settings.groq_vision_model:
            # Vision model not available on this Groq tier — skip gracefully.
            # Doc-intel and retrieval agents will cover what we miss here.
            await self.emit_event(
                product_id,
                "agent_complete",
                f"Vision model not configured (GROQ_VISION_MODEL is blank) — "
                f"{len(image_paths)} image(s) skipped. "
                f"Set GROQ_VISION_MODEL to enable. Doc-intel covers extraction.",
            )
            return {}

        await self.emit_event(
            product_id,
            "agent_start",
            f"Analyzing {len(image_paths)} image(s) with {settings.groq_vision_model}...",
        )

        field_candidates: dict[str, list[CandidateValue]] = {}
        for img_path in image_paths[:3]:
            if not Path(img_path).exists():
                continue
            candidates = await self._extract_from_image(img_path)
            for field_name, candidate in candidates:
                field_candidates.setdefault(field_name, []).append(candidate)

        await self.emit_event(
            product_id,
            "agent_complete",
            f"Vision extraction complete — {len(field_candidates)} fields found.",
            data={"field_count": len(field_candidates)},
        )
        return field_candidates

    async def _extract_from_image(self, img_path: str) -> list[tuple[str, CandidateValue]]:
        """Call Groq vision model on one image (base64-encoded)."""
        try:
            with open(img_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            suffix = Path(img_path).suffix.lower()
            media_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }.get(suffix, "image/jpeg")

            client = _groq_client()
            response = await client.chat.completions.create(
                model=settings.groq_vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}",
                                },
                            },
                            {"type": "text", "text": VISION_EXTRACTION_PROMPT},
                        ],
                    }
                ],
                max_tokens=1024,
                temperature=0.0,
            )

            raw = response.choices[0].message.content or ""
            # Strip markdown code fences if model wraps output
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            extracted = json.loads(raw)
            source_image = Path(img_path).name
            region_notes = extracted.pop("region_notes", "")

            results: list[tuple[str, CandidateValue]] = []
            for field_name, value in extracted.items():
                if value and isinstance(value, (str, int, float)):
                    region_desc = f"image:{source_image}"
                    if region_notes:
                        region_desc += f" ({region_notes})"
                    results.append(
                        (
                            field_name,
                            CandidateValue(
                                value=str(value),
                                source_type=SourceType.IMAGE,
                                source_ref=source_image,
                                extracted_snippet=region_desc,
                                extraction_agent=f"vision_agent:groq:{settings.groq_vision_model}",
                                low_quality=False,
                            ),
                        )
                    )
            return results

        except Exception as exc:
            logger.error("Vision extraction failed", img_path=img_path, error=str(exc))
            return []
