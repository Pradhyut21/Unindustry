"""
Vision Agent — extracts product attributes from images using Claude's vision capability.

Every extracted value is tagged with {source_image, region_description}
so the citation trail includes the image source, not just a raw number.
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
- Color, finish, form factor

Return a JSON object with these fields (include ONLY fields you can see):
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


class VisionAgent(BaseAgent):
    """
    Uses Claude's vision capability to extract product attributes from images.
    Handles up to 3 images per product run.
    """

    name = "vision_agent"

    async def run(
        self,
        product_id: uuid.UUID,
        image_paths: Optional[list[str]] = None,
        **kwargs,
    ) -> dict[str, list[CandidateValue]]:
        """
        Parameters
        ----------
        product_id : uuid.UUID
        image_paths : list[str] | None — paths to uploaded product images

        Returns
        -------
        dict mapping field_name → list[CandidateValue]
        """
        if not image_paths:
            await self.emit_event(
                product_id, "agent_complete", "No images provided — skipping vision extraction."
            )
            return {}

        if not settings.anthropic_api_key:
            await self.emit_event(
                product_id, "agent_error", "No Anthropic API key — vision extraction skipped."
            )
            return {}

        await self.emit_event(
            product_id, "agent_start", f"Analyzing {len(image_paths)} image(s) with vision model..."
        )

        field_candidates: dict[str, list[CandidateValue]] = {}

        for img_path in image_paths[:3]:  # max 3 images
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

    async def _extract_from_image(
        self, img_path: str
    ) -> list[tuple[str, CandidateValue]]:
        """Call Claude vision API on one image."""
        try:
            import anthropic

            # Read and encode image
            with open(img_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            suffix = Path(img_path).suffix.lower()
            media_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif",
            }
            media_type = media_type_map.get(suffix, "image/jpeg")

            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            message = await client.messages.create(
                model=settings.claude_extraction_model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": VISION_EXTRACTION_PROMPT},
                        ],
                    }
                ],
            )

            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

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
                                extraction_agent="vision_agent:claude",
                                low_quality=False,
                            ),
                        )
                    )
            return results

        except Exception as exc:
            logger.error("Vision extraction failed", img_path=img_path, error=str(exc))
            return []
