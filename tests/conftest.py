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

from src.database import create_all_tables  # noqa: E402
from src.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_test_tables():
    """Ensure the schema exists before any test hits the database.

    httpx's ASGITransport does not run the app's lifespan (that's what calls
    create_all_tables() in production), so a test is the first thing to touch
    the DB in a given environment. Most tests never notice because they 401
    before a query runs, or because a developer's local data/app.db already
    has the schema from running the real server. On a clean checkout (e.g. a
    fresh CI runner) with no such file, the first test that actually performs
    a real insert -- registering a user -- fails with "no such table: users".
    """
    await create_all_tables()


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
