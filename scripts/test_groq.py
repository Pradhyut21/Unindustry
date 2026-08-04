"""Quick Groq connectivity test — run: python scripts/test_groq.py"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY not set. Add it to .env or export it.")
    sys.exit(1)


async def main():
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

    print("Testing text model (llama-3.3-70b-versatile)...")
    try:
        r = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": 'Return valid JSON: {"status": "ok"}'}],
            max_tokens=50,
            temperature=0,
            response_format={"type": "json_object"},
        )
        print("  TEXT OK:", r.choices[0].message.content)
    except Exception as e:
        print("  TEXT FAIL:", e)
        sys.exit(1)

    print("\nTesting vision model (llama-4-scout)...")
    try:
        r2 = await client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": 'What colour is the sky? Return JSON: {"answer": "..."}',
                        }
                    ],
                }
            ],
            max_tokens=50,
            temperature=0,
        )
        print("  VISION OK:", r2.choices[0].message.content)
    except Exception as e:
        print("  VISION FAIL (may need different model name):", e)

    print("\nAll checks done.")


asyncio.run(main())
