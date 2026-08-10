import asyncio
import asyncpg
import json

async def run():
    try:
        conn = await asyncpg.connect('postgresql://postgres:password@localhost:5434/litreview')
        rows = await conn.fetch("SELECT id, title FROM papers WHERE title LIKE '%novel method for ECG%' LIMIT 1")
        print(f"Found paper: {rows}")
        if rows:
            paper_id = rows[0]['id']
            # call the API via httpx
            import httpx
            async with httpx.AsyncClient() as c:
                res = await c.post(f'http://127.0.0.1:8000/api/v1/papers/{paper_id}/quality-check')
                print(f"API status: {res.status_code}")
                print(f"API response: {res.text}")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(run())
