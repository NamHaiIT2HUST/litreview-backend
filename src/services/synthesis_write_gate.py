"""Serialize long synthesis write transactions only when SQLite is in use."""

import asyncio
from contextlib import asynccontextmanager


class SynthesisWriteGate:
    def __init__(self, database_url: str):
        self._serialize = database_url.startswith("sqlite")
        self._lock = None
        self._loop = None

    def _get_lock(self):
        loop = asyncio.get_running_loop()
        if self._lock is None or self._loop is not loop:
            self._lock = asyncio.Lock()
            self._loop = loop
        return self._lock

    @asynccontextmanager
    async def hold(self):
        if not self._serialize:
            yield
            return
        async with self._get_lock():
            yield
