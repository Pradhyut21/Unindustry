"""
Catalog indexing script for ProductTruth.
Downloads public catalog pages from major industrial manufacturers and updates the RAG catalog index.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

PUBLIC_CATALOG_PAGES: list[tuple[str, str]] = [
    (
        "siemens_contactors",
        "https://www.siemens.com/global/en/products/automation/industrial-controls/contactors.html",
    ),
    (
        "abb_breakers",
        "https://new.abb.com/low-voltage/products/circuit-breakers",
    ),
    (
        "schneider_pushbuttons",
        "https://www.se.com/us/en/product-range/61487-harmony-xb4/",
    ),
]

CATALOG_FIXTURES_DIR = Path(__file__).parent.parent / "api" / "fixtures" / "catalogs"


async def index_catalogs() -> None:
    CATALOG_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    indexed_count = 0

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for source_name, url in PUBLIC_CATALOG_PAGES:
            print(f"Fetching catalog source: {source_name} ({url})...")
            try:
                r = await client.get(url)
                if r.status_code == 200 and len(r.text) > 100:
                    out_file = CATALOG_FIXTURES_DIR / f"{source_name}.txt"
                    # Strip tags simply or store raw catalog text
                    out_file.write_text(f"SOURCE_URL: {url}\n\n" + r.text[:10000], encoding="utf-8")
                    indexed_count += 1
                    print(f"Indexed {source_name} into {out_file.name}")
                    continue
            except Exception as exc:
                print(f"Web fetch for {source_name} failed ({exc}). Retaining fixture.")

            out_file = CATALOG_FIXTURES_DIR / f"{source_name}.txt"
            if out_file.exists():
                indexed_count += 1
                print(f"Retained existing fixture: {out_file.name}")

    print(f"\nIndexed {indexed_count} catalog sources in {CATALOG_FIXTURES_DIR}")


if __name__ == "__main__":
    asyncio.run(index_catalogs())
