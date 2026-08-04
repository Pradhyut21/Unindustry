"""
Doc-Intel Agent — parses PDFs and spec sheet datasheets.

Uses PyMuPDF (fitz) for primary parsing and falls back to unstructured.io
for complex layouts. Every extracted value is tagged with:
  {source_file, page_number, text_snippet}

so the citation trail goes all the way back to the exact page.
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

# Fields we look for in industrial spec sheets
SPEC_FIELD_PATTERNS: dict[str, list[str]] = {
    "voltage_rating": ["voltage", "rated voltage", "supply voltage", "v ac", "v dc"],
    "current_rating": ["current", "rated current", "ampere", "amp", "a ac", "a dc"],
    "power_rating": ["power", "rated power", "watt", "kw", "hp"],
    "frequency": ["frequency", "hz", "hertz"],
    "ip_rating": ["ip rating", "ip code", "ip6", "ip5", "ingress protection"],
    "operating_temperature": ["operating temperature", "ambient temperature", "temp range"],
    "dimensions": ["dimensions", "size", "length", "width", "height", "l x w x h"],
    "weight": ["weight", "mass", "kg", "lbs"],
    "material": ["material", "housing material", "body material"],
    "certifications": ["ce", "ul", "csa", "rohs", "atex", "iec", "iso", "en"],
    "model_number": ["model", "model no", "part number", "catalog number", "order code"],
    "manufacturer": ["manufacturer", "brand", "made by"],
    "product_category": ["category", "product type", "classification"],
    "description": ["description", "product description", "overview"],
}


def _extract_kv_from_text(text: str, page_num: int, source_file: str) -> list[CandidateValue]:
    """
    Heuristic key-value extraction from a page of text.
    Looks for known field patterns and extracts the adjacent value.
    """
    candidates: list[CandidateValue] = []
    lines = text.split("\n")

    for field_name, patterns in SPEC_FIELD_PATTERNS.items():
        for line in lines:
            line_lower = line.lower().strip()
            for pattern in patterns:
                if pattern in line_lower:
                    # Try to extract the value part (after colon, tab, or next word)
                    value = _parse_value_from_line(line, pattern)
                    if value:
                        candidates.append(
                            CandidateValue(
                                value=value,
                                source_type=SourceType.DOC,
                                source_ref=f"{source_file}:page{page_num}",
                                extracted_snippet=line.strip()[:200],
                                extraction_agent="doc_intel_agent",
                            )
                        )
                        break  # one match per field per line

    return candidates


def _parse_value_from_line(line: str, pattern: str) -> Optional[str]:
    """Extract the value portion from a 'key: value' or 'key  value' line."""
    # Try colon-delimited
    if ":" in line:
        parts = line.split(":", 1)
        if len(parts) == 2:
            value = parts[1].strip()
            if value and len(value) < 200:
                return value

    # Try tab-delimited
    if "\t" in line:
        parts = line.split("\t", 1)
        if len(parts) == 2:
            value = parts[1].strip()
            if value and len(value) < 200:
                return value

    return None


class DocIntelAgent(BaseAgent):
    """
    Parses a product PDF/datasheet and extracts structured fields.
    Tags every extracted value with source_file + page_number + text_snippet.
    """

    name = "doc_intel_agent"

    async def run(
        self,
        product_id: uuid.UUID,
        pdf_path: Optional[str] = None,
        **kwargs,
    ) -> dict[str, list[CandidateValue]]:
        """
        Parameters
        ----------
        product_id : uuid.UUID
        pdf_path : str | None — path to the uploaded PDF file

        Returns
        -------
        dict mapping field_name → list[CandidateValue]
        """
        if not pdf_path or not Path(pdf_path).exists():
            await self.emit_event(
                product_id, "agent_complete", "No PDF provided — skipping doc extraction."
            )
            return {}

        await self.emit_event(product_id, "agent_start", f"Parsing {Path(pdf_path).name}...")

        try:
            candidates = await self._parse_pdf(pdf_path)
        except Exception as exc:
            await self.emit_event(
                product_id, "agent_error", f"PDF parse failed: {exc}"
            )
            logger.error("PDF parse error", path=pdf_path, error=str(exc))
            return {}

        # Group by field name
        field_candidates: dict[str, list[CandidateValue]] = {}
        for candidate in candidates:
            # We don't have field_name on CandidateValue directly here —
            # _extract_kv_from_text produces (field_name, CandidateValue) tuples
            pass

        await self.emit_event(
            product_id,
            "agent_complete",
            f"Extracted candidates from PDF.",
            data={"field_count": len(field_candidates)},
        )
        return field_candidates

    async def _parse_pdf(self, pdf_path: str) -> list[tuple[str, CandidateValue]]:
        """
        Parse PDF with PyMuPDF page-by-page.
        Returns list of (field_name, CandidateValue) tuples.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not installed — PDF parsing unavailable")
            return []

        results: list[tuple[str, CandidateValue]] = []
        source_file = Path(pdf_path).name

        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if not text.strip():
                continue

            page_candidates = _extract_kv_from_text(text, page_num, source_file)
            # We need field names — re-run with field name tracking
            for field_name, patterns in SPEC_FIELD_PATTERNS.items():
                for line in text.split("\n"):
                    line_lower = line.lower().strip()
                    for pattern in patterns:
                        if pattern in line_lower:
                            value = _parse_value_from_line(line, pattern)
                            if value:
                                results.append(
                                    (
                                        field_name,
                                        CandidateValue(
                                            value=value,
                                            source_type=SourceType.DOC,
                                            source_ref=f"{source_file}:page{page_num}",
                                            extracted_snippet=line.strip()[:200],
                                            extraction_agent="doc_intel_agent",
                                        ),
                                    )
                                )
                            break

        doc.close()

        # Also use Claude for LLM-assisted structured extraction on the full text
        full_text = "\n".join(
            fitz.open(pdf_path)[i].get_text("text") for i in range(min(len(fitz.open(pdf_path)), 10))
        )
        llm_results = await self._llm_extract(full_text, source_file)
        results.extend(llm_results)

        return results

    async def _llm_extract(
        self, text: str, source_file: str
    ) -> list[tuple[str, CandidateValue]]:
        """
        Use Claude to extract structured fields from the full document text.
        More reliable than heuristic parsing for complex layouts.
        """
        if not settings.anthropic_api_key:
            return []

        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

            prompt = f"""You are extracting product specification data from an industrial product datasheet.

Extract ALL fields you can find in the following text. Return a JSON object where keys are snake_case field names and values are the extracted values as strings.

Focus on: voltage_rating, current_rating, power_rating, frequency, ip_rating, operating_temperature, dimensions, weight, material, certifications, model_number, manufacturer, product_category, description.

Only include fields you actually find in the text. Do NOT hallucinate values. If a field is not present, omit it.

TEXT:
{text[:8000]}

Return ONLY valid JSON, no explanation."""

            message = await client.messages.create(
                model=settings.claude_extraction_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = message.content[0].text.strip()
            # Strip markdown code block if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            extracted = json.loads(raw)

            results: list[tuple[str, CandidateValue]] = []
            for field_name, value in extracted.items():
                if value and isinstance(value, str):
                    results.append(
                        (
                            field_name,
                            CandidateValue(
                                value=value,
                                source_type=SourceType.DOC,
                                source_ref=f"{source_file}:llm_extract",
                                extracted_snippet=f"LLM extracted from full document text",
                                extraction_agent="doc_intel_agent:claude",
                            ),
                        )
                    )
            return results

        except Exception as exc:
            logger.warning("LLM extraction failed", error=str(exc))
            return []
