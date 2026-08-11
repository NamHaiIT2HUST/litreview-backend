import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://postgres:password@localhost:5434/litreview')
    count = await conn.fetchval('SELECT COUNT(*) FROM scopus_sources')
    sample = await conn.fetch('SELECT title, issn, eissn, active_status FROM scopus_sources LIMIT 5')
    print(f'Total sources: {count}')
    print('Samples:')
    for r in sample:
        print(dict(r))
    await conn.close()

asyncio.run(run())
