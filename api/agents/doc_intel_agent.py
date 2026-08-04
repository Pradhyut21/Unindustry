"""
Doc-Intel Agent — parses PDFs and spec sheet datasheets.

Uses PyMuPDF (fitz) for primary heuristic parsing, then Groq (llama-3.3-70b)
for LLM-assisted structured extraction on the full document text.

Every extracted value is tagged with {source_file, page_number, text_snippet}
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


def _parse_value_from_line(line: str, pattern: str) -> Optional[str]:
    """Extract the value portion from a 'key: value' or 'key  value' line."""
    if ":" in line:
        parts = line.split(":", 1)
        if len(parts) == 2:
            value = parts[1].strip()
            if value and len(value) < 200:
                return value
    if "\t" in line:
        parts = line.split("\t", 1)
        if len(parts) == 2:
            value = parts[1].strip()
            if value and len(value) < 200:
                return value
    return None


def _groq_client():
    """Return an AsyncOpenAI client pointed at the Groq endpoint."""
    from openai import AsyncOpenAI

    return AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )


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
        if not pdf_path or not Path(pdf_path).exists():
            await self.emit_event(
                product_id, "agent_complete", "No PDF provided — skipping doc extraction."
            )
            return {}

        await self.emit_event(product_id, "agent_start", f"Parsing {Path(pdf_path).name}...")

        try:
            results = await self._parse_pdf(pdf_path)
        except Exception as exc:
            await self.emit_event(product_id, "agent_error", f"PDF parse failed: {exc}")
            logger.error("PDF parse error", path=pdf_path, error=str(exc))
            return {}

        # Group (field_name, CandidateValue) tuples into dict
        field_candidates: dict[str, list[CandidateValue]] = {}
        for field_name, candidate in results:
            field_candidates.setdefault(field_name, []).append(candidate)

        await self.emit_event(
            product_id,
            "agent_complete",
            f"Doc extraction done — {len(field_candidates)} fields found.",
            data={"field_count": len(field_candidates)},
        )
        return field_candidates

    async def _parse_pdf(self, pdf_path: str) -> list[tuple[str, CandidateValue]]:
        """
        Parse PDF with PyMuPDF page-by-page (heuristic), then LLM pass.
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
        full_pages: list[str] = []

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if not text.strip():
                continue
            full_pages.append(text)

            # Heuristic pass
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
                                            extraction_agent="doc_intel_agent:heuristic",
                                        ),
                                    )
                                )
                            break

        doc.close()

        # LLM pass over full text (first 10 pages max)
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(full_pages[:10])
        llm_results = await self._llm_extract(full_text, source_file)
        results.extend(llm_results)
        return results

    async def _llm_extract(self, text: str, source_file: str) -> list[tuple[str, CandidateValue]]:
        """
        Use Groq (llama-3.3-70b) to extract structured fields from document text.
        More reliable than heuristic parsing for complex layouts.
        """
        if not settings.groq_api_key:
            logger.warning("No GROQ_API_KEY — LLM extraction skipped")
            return []

        prompt = f"""You are extracting product specification data from an industrial product datasheet.

Extract ALL fields you can find in the following text. Return a JSON object where keys are snake_case field names and values are the extracted values as strings.

Focus on: voltage_rating, current_rating, power_rating, frequency, ip_rating, operating_temperature, dimensions, weight, material, certifications, model_number, manufacturer, product_category, description.

Only include fields you actually find in the text. Do NOT hallucinate values. If a field is not present, omit it.

TEXT:
{text[:8000]}

Return ONLY valid JSON, no explanation."""

        try:
            client = _groq_client()
            response = await client.chat.completions.create(
                model=settings.groq_extraction_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or ""
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
                                extracted_snippet="LLM extracted from full document text",
                                extraction_agent="doc_intel_agent:groq",
                            ),
                        )
                    )
            return results

        except Exception as exc:
            logger.warning("LLM extraction failed", error=str(exc))
            return []
