"""
Schema Mapper Agent — maps verified fields to ETIM-style commerce schema.

ETIM (Electro Technical Information Model) is the standard taxonomy used
in industrial electrical and mechanical product catalogs. We implement an
ETIM-inspired schema (configurable via schemas/etim_schema.json) so output
can integrate with real PIM systems.

The mapper:
1. Reads the target schema from schemas/etim_schema.json
2. Maps each verified field to its ETIM equivalent (using field aliases)
3. Applies any unit normalisation defined in the schema
4. Returns a commerce-ready product record as a dict
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Optional

from api.agents.base import BaseAgent
from api.agents.verifier_agent import VerificationResult

SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "etim_schema.json"


def load_schema() -> dict:
    """Load the ETIM-style schema definition."""
    if SCHEMA_PATH.exists():
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return {}


def map_to_schema(
    verified_fields: dict[str, VerificationResult],
    schema: dict,
) -> dict[str, Any]:
    """
    Pure function — maps verified field results to the target schema.

    Parameters
    ----------
    verified_fields : dict[str, VerificationResult]
    schema : dict — loaded ETIM schema definition

    Returns
    -------
    dict — commerce-ready product record
    """
    fields_def = schema.get("fields", {})
    output: dict[str, Any] = {
        "_schema": schema.get("schema_id", "etim_custom_v1"),
        "_schema_version": schema.get("version", "1.0"),
    }

    for etim_field_id, field_def in fields_def.items():
        aliases = field_def.get("aliases", [field_def.get("name", "")])
        unit = field_def.get("unit", "")
        field_name_in_schema = field_def.get("name", etim_field_id)

        # Find a matching verified field
        matched_value: Optional[str] = None
        matched_confidence: float = 0.0

        for alias in aliases:
            alias_snake = alias.lower().replace(" ", "_")
            if alias_snake in verified_fields:
                result = verified_fields[alias_snake]
                if result.final_value is not None:
                    matched_value = result.final_value
                    matched_confidence = result.confidence
                    break

        # Apply unit normalisation if needed
        if matched_value and unit:
            matched_value = _normalise_unit(matched_value, unit)

        output[field_name_in_schema] = {
            "value": matched_value,
            "unit": unit if unit else None,
            "etim_field_id": etim_field_id,
            "confidence": matched_confidence,
        }

    return output


def _normalise_unit(value: str, target_unit: str) -> str:
    """
    Basic unit normalisation (expand as needed).
    E.g. "230 volts" → "230 V", "5.2 kilograms" → "5.2 kg"
    """
    normalizations = {
        "kW": ["kilowatt", "kilowatts"],
        "W": ["watt", "watts"],
        "V": ["volts", "volt", "voltage"],
        "A": ["amperes", "ampere", "amps", "amp"],
        "kg": ["kilograms", "kilogram", "kilo"],
        "mm": ["millimeter", "millimetre"],
        "°C": ["celsius", "degrees c", "deg c"],
        "Hz": ["hertz", "hz"],
    }
    value_lower = value.lower()
    for unit_symbol, synonyms in normalizations.items():
        for syn in synonyms:
            if syn in value_lower:
                # Replace synonym with symbol
                return value_lower.replace(syn, unit_symbol).strip()
    return value


class SchemaMappingAgent(BaseAgent):
    """Maps verified product fields to the target ETIM-style commerce schema."""

    name = "schema_mapper"

    async def run(
        self,
        product_id: uuid.UUID,
        verified_fields: dict[str, VerificationResult],
        **kwargs,
    ) -> dict[str, Any]:
        """
        Parameters
        ----------
        product_id : uuid.UUID
        verified_fields : dict[str, VerificationResult]

        Returns
        -------
        dict — commerce-ready product record in target schema
        """
        await self.emit_event(product_id, "agent_start", "Mapping fields to ETIM schema...")

        schema = load_schema()
        if not schema:
            await self.emit_event(
                product_id, "agent_error", "Schema file not found — raw output only."
            )
            return {k: v.final_value for k, v in verified_fields.items()}

        result = map_to_schema(verified_fields, schema)

        await self.emit_event(
            product_id,
            "agent_complete",
            f"Schema mapping complete — {len(result)} fields mapped.",
            data={"schema_id": schema.get("schema_id"), "field_count": len(result)},
        )
        return result
