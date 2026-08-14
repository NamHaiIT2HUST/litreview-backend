import asyncio

import pytest

from src.services.synthesis_write_gate import SynthesisWriteGate


@pytest.mark.asyncio
async def test_sqlite_write_gate_serializes_parallel_extraction_transactions():
    gate = SynthesisWriteGate("sqlite+aiosqlite:///./data/app.db")
    active = 0
    max_active = 0

    async def write():
        nonlocal active, max_active
        async with gate.hold():
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1

    await asyncio.gather(write(), write(), write())

    assert max_active == 1


@pytest.mark.asyncio
async def test_postgres_write_gate_keeps_parallelism():
    gate = SynthesisWriteGate("postgresql+asyncpg://localhost/litreview")
    active = 0
    max_active = 0

    async def write():
        nonlocal active, max_active
        async with gate.hold():
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1

    await asyncio.gather(write(), write())

    assert max_active == 2
