import asyncio

import asyncpg

DB = "postgresql://neondb_owner:npg_O3Tad0cjSqbH@ep-tiny-dew-ax4j7o4r-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"


async def main():
    conn = await asyncpg.connect(DB)
    products = await conn.fetch(
        "SELECT id, name, status FROM products ORDER BY created_at DESC LIMIT 3"
    )
    for p in products:
        print(f"\nProduct: {p['name']} | Status: {p['status']} | ID: {p['id']}")
        fields = await conn.fetch(
            "SELECT field_name, value, confidence, verification_status FROM product_fields WHERE product_id=$1",
            p["id"],
        )
        for f in fields:
            print(
                f"  {f['field_name']}: {f['value']} (conf={float(f['confidence']):.2f}, {f['verification_status']})"
            )
    await conn.close()


asyncio.run(main())
