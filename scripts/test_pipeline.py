"""
End-to-end test of doc_intel_agent against the sample PDF.
Run: python scripts/test_pipeline.py
No DB needed — just tests the extraction + Groq LLM call.
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Must come before api imports — adds repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from api.agents.doc_intel_agent import DocIntelAgent  # noqa: E402


async def main() -> None:
    pdf_path = str(
        Path(__file__).parent.parent / "api" / "fixtures" / "sample_siemens_3rt2015_datasheet.pdf"
    )
    print(f"Testing doc extraction on: {pdf_path}\n")

    agent = DocIntelAgent()
    product_id = uuid.uuid4()

    # Monkey-patch emit_event to print instead of push to SSE
    async def print_event(pid, event_type, message, data=None):  # type: ignore[misc]
        print(f"  [{event_type}] {message}")

    agent.emit_event = print_event  # type: ignore[method-assign]

    results = await agent.run(product_id, pdf_path=pdf_path)

    print(f"\nExtracted {len(results)} fields:\n")
    for field, candidates in sorted(results.items()):
        for c in candidates:
            print(f"  {field:25} = {c.value!r:30} [{c.extraction_agent}]")

    if not results:
        print("  No fields extracted — check Groq key and PDF path.")
        sys.exit(1)
    else:
        print("\nDoc-intel pipeline: OK")


asyncio.run(main())
