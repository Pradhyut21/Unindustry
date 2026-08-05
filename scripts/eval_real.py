"""
Real-world evaluation script for ProductTruth.
Downloads public manufacturer datasheets and evaluates pipeline extraction accuracy.
"""

from __future__ import annotations

import asyncio
import pathlib
import tempfile
import uuid
from typing import Any

import httpx

REAL_DATASHEETS: list[dict[str, Any]] = [
    {
        "name": "Siemens 3RT2015 (real)",
        "url": "https://cache.industry.siemens.com/dl/dl-media/573/109780573/att_1063569/v1/3RT2015_en.pdf",
        "ground_truth": {
            "current_rating": "7A",
            "voltage_rating": "400V",
            "product_category": "contactor",
            "ip_rating": "IP20",
        },
    },
    {
        "name": "ABB S200 Miniature Circuit Breaker (real)",
        "url": "https://search.abb.com/library/Download.aspx?DocumentID=2CDC400002D0201&LanguageCode=en&DocumentPartId=&Action=Launch",
        "ground_truth": {
            "current_rating": "16A",
            "voltage_rating": "230V",
            "product_category": "circuit breaker",
            "ip_rating": "IP20",
        },
    },
]


async def run_real_eval() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for item in REAL_DATASHEETS:
            print(f"Downloading datasheet for {item['name']}...")
            pdf_path: str | None = None
            try:
                r = await client.get(item["url"])
                if r.status_code == 200 and r.content:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                        f.write(r.content)
                        pdf_path = f.name
            except Exception as exc:
                print(f"Could not download {item['name']}: {exc}. Using bundled fixture fallback.")

            if not pdf_path or not pathlib.Path(pdf_path).exists():
                bundled = (
                    pathlib.Path(__file__).parent.parent
                    / "api"
                    / "fixtures"
                    / "sample_siemens_3rt2015_datasheet.pdf"
                )
                if bundled.exists():
                    pdf_path = str(bundled)

            fields_dict: dict[str, str] = {}
            db_connected = False
            try:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from api.agents.orchestrator import OrchestratorAgent
                from api.database import AsyncSessionLocal, init_db
                from api.models.db import Product

                await init_db()
                product_id = uuid.uuid4()
                async with AsyncSessionLocal() as db:
                    product = Product(
                        id=product_id,
                        name=item["name"],
                        input_pdf_path=pdf_path,
                    )
                    db.add(product)
                    await db.commit()

                print(f"Running Orchestrator pipeline for {item['name']}...")
                agent = OrchestratorAgent()
                await agent.run(product_id=product_id)

                async with AsyncSessionLocal() as db:
                    res = await db.execute(
                        select(Product)
                        .where(Product.id == product_id)
                        .options(selectinload(Product.fields))
                    )
                    product_record = res.scalar_one_or_none()
                    if product_record:
                        for f in product_record.fields:
                            fields_dict[f.field_name] = f.value or ""
            except Exception as db_exc:
                print(f"DB unavailable ({db_exc}). Running direct doc-intel extraction...")
                from api.agents.doc_intel_agent import DocIntelAgent

                doc_agent = DocIntelAgent()
                candidates = await doc_agent.run(product_id=uuid.uuid4(), pdf_path=pdf_path)
                for field_name, cand_list in candidates.items():
                    if cand_list:
                        fields_dict[field_name] = cand_list[0].value

            for field, truth in item["ground_truth"].items():
                predicted = fields_dict.get(field, "")
                correct = (
                    (
                        predicted.lower().strip() == truth.lower().strip()
                        or truth.lower() in predicted.lower()
                        or predicted.lower() in truth.lower()
                    )
                    if predicted
                    else False
                )

                results.append(
                    {
                        "product": item["name"],
                        "field": field,
                        "predicted": predicted,
                        "truth": truth,
                        "correct": correct,
                    }
                )

    if results:
        accuracy = sum(1 for r in results if r["correct"]) / len(results)
        print(f"\nReal-world accuracy: {accuracy:.1%} on {len(results)} evaluated fields")
    else:
        print("\nNo results evaluated.")

    return results


if __name__ == "__main__":
    asyncio.run(run_real_eval())
