import os

# Declare the embedding backend the suite runs on, before anything imports
# src.config and caches Settings.
#
# The default provider is "openai", which now raises when no key is configured
# rather than silently degrading to random vectors. Tests must therefore say
# which backend they want. "hash-debug" is the explicit, deterministic,
# network-free opt-in that exists for exactly this: it is never selected
# implicitly, so a test run can never be mistaken for a production
# configuration.
os.environ.setdefault("EMBEDDING_PROVIDER", "hash-debug")
# Signing key for routes that mint or verify tokens. Not a secret: the suite
# only needs a well-formed key, and validate_security_settings enforces a real
# one outside tests.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-any-real-deployment-0123456789")

from unittest.mock import AsyncMock  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from src.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
