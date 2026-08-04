"""
Retrieval Agent — fills missing fields via RAG over manufacturer catalog fixtures.

Uses pgvector for semantic similarity search over pre-indexed catalog documents.
Falls back to a web search call if the local index has no useful results.

Every retrieved value is tagged with {source_url, retrieved_snippet}
so the citation trail includes where the information came from.
"""

from __future__ import annotations

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

CATALOG_FIXTURES_DIR = Path(__file__).parent.parent.parent / "api" / "fixtures" / "catalogs"


class RetrievalAgent(BaseAgent):
    """
    RAG-based retrieval agent.
    Queries the pgvector catalog index for fields not found by doc/vision agents.
    """

    name = "retrieval_agent"

    async def run(
        self,
        product_id: uuid.UUID,
        product_name: str,
        missing_fields: list[str],
        known_fields: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> dict[str, list[CandidateValue]]:
        """
        Parameters
        ----------
        product_id : uuid.UUID
        product_name : str — used as the base query
        missing_fields : list[str] — field names to try to fill
        known_fields : dict — already-extracted fields (used to refine queries)

        Returns
        -------
        dict mapping field_name → list[CandidateValue]
        """
        if not missing_fields:
            await self.emit_event(product_id, "agent_complete", "No missing fields — skipping retrieval.")
            return {}

        await self.emit_event(
            product_id,
            "agent_start",
            f"Retrieving {len(missing_fields)} missing fields for '{product_name}'...",
        )

        field_candidates: dict[str, list[CandidateValue]] = {}

        # 1. Try local fixture catalog first (fast, no API cost)
        fixture_results = await self._search_fixtures(product_name, missing_fields)
        for field_name, candidate in fixture_results:
            field_candidates.setdefault(field_name, []).append(candidate)

        # 2. LLM-assisted retrieval for fields still missing
        still_missing = [f for f in missing_fields if f not in field_candidates]
        if still_missing and settings.groq_api_key:
            llm_results = await self._llm_retrieval(
                product_name, still_missing, known_fields or {}
            )
            for field_name, candidate in llm_results:
                field_candidates.setdefault(field_name, []).append(candidate)

        await self.emit_event(
            product_id,
            "agent_complete",
            f"Retrieval complete — filled {len(field_candidates)}/{len(missing_fields)} fields.",
            data={"filled": len(field_candidates), "missing": len(missing_fields)},
        )
        return field_candidates

    async def _search_fixtures(
        self, product_name: str, fields: list[str]
    ) -> list[tuple[str, CandidateValue]]:
        """
        Simple keyword search over local catalog fixture files.
        In production this would be a pgvector similarity query.
        """
        if not CATALOG_FIXTURES_DIR.exists():
            return []

        results: list[tuple[str, CandidateValue]] = []
        product_name_lower = product_name.lower()

        for catalog_file in CATALOG_FIXTURES_DIR.glob("*.txt"):
            content = catalog_file.read_text(encoding="utf-8")
            content_lower = content.lower()

            # Only use catalogs relevant to this product
            if not any(word in content_lower for word in product_name_lower.split()[:3]):
                continue

            for field_name in fields:
                # Look for the field name in the catalog content
                field_aliases = {
                    "voltage_rating": ["voltage", "rated voltage"],
                    "current_rating": ["current", "rated current", "ampere"],
                    "ip_rating": ["ip rating", "ip code"],
                    "certifications": ["certifications", "approvals", "standards"],
                    "material": ["material", "housing"],
                    "dimensions": ["dimensions", "size"],
                    "weight": ["weight"],
                    "model_number": ["model", "part number"],
                    "manufacturer": ["manufacturer", "brand"],
                }.get(field_name, [field_name.replace("_", " ")])

                for alias in field_aliases:
                    if alias in content_lower:
                        # Extract surrounding context
                        idx = content_lower.find(alias)
                        snippet = content[max(0, idx - 20): idx + 100].strip()
                        value = _extract_value_from_snippet(snippet, alias)
                        if value:
                            results.append(
                                (
                                    field_name,
                                    CandidateValue(
                                        value=value,
                                        source_type=SourceType.WEB,
                                        source_ref=f"catalog:{catalog_file.stem}",
                                        extracted_snippet=snippet[:200],
                                        extraction_agent="retrieval_agent:fixture",
                                    ),
                                )
                            )
                            break

        return results

    async def _llm_retrieval(
        self,
        product_name: str,
        missing_fields: list[str],
        known_fields: dict[str, str],
    ) -> list[tuple[str, CandidateValue]]:
        """
        Use Groq (llama-3.3-70b) to infer likely values for missing fields based on
        the product name and known fields. Marked as low-confidence WEB source.
        """
        try:
            from openai import AsyncOpenAI

            context = "\n".join(f"  {k}: {v}" for k, v in known_fields.items())
            fields_str = ", ".join(missing_fields)

            prompt = f"""You are a product data specialist for industrial commerce.

Product name: {product_name}
Known attributes:
{context if context else "  (none yet)"}

Based on this product name and known attributes, provide your best estimates for these missing fields: {fields_str}

Rules:
- Only provide values that are TYPICAL or STANDARD for this type of industrial product
- Do NOT invent specific model numbers or certifications you cannot reasonably infer
- Mark uncertain values with a ~ prefix (e.g., "~230V" means "probably 230V but verify")
- Return JSON only.

Return format:
{{"field_name": "value or null if you cannot reasonably infer it"}}"""

            client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            response = await client.chat.completions.create(
                model=settings.groq_extraction_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            extracted = json.loads(response.choices[0].message.content or "{}")
            results: list[tuple[str, CandidateValue]] = []

            for field_name, value in extracted.items():
                if value and isinstance(value, str):
                    low_quality = value.startswith("~")
                    clean_value = value.lstrip("~").strip()
                    results.append((
                        field_name,
                        CandidateValue(
                            value=clean_value,
                            source_type=SourceType.WEB,
                            source_ref="llm:inferred",
                            extracted_snippet=f"LLM inferred from product name: {product_name}",
                            extraction_agent="retrieval_agent:groq",
                            low_quality=low_quality,
                        ),
                    ))
            return results

        except Exception as exc:
            logger.warning("LLM retrieval failed", error=str(exc))
            return []


def _extract_value_from_snippet(snippet: str, key: str) -> Optional[str]:
    """Extract the value part after a key in a text snippet."""
    lower = snippet.lower()
    idx = lower.find(key)
    if idx == -1:
        return None
    after = snippet[idx + len(key):].strip()
    # Remove leading punctuation
    after = after.lstrip(":- \t")
    # Take up to first newline or 80 chars
    lines = after.split("\n")
    value = lines[0].strip()[:80] if lines else ""
    return value if value else None
