from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.documents import Document

from src.agents.graph import agent


@pytest.mark.asyncio
async def test_agent_basic_flow():
    # retrieve_node/draft_node hit a real ChromaDB vector store and a real
    # LLM respectively -- neither is seeded/available in the test
    # environment, so both are mocked here (the metadata has no "doi", so
    # guard_node passes the chunk through without calling the live Crossref
    # API either).
    fake_chunk = Document(page_content="Hello is a common greeting.", metadata={})
    with (
        patch(
            "src.agents.nodes.retrieve_node.vector_store_service.search_similar_documents",
            new=AsyncMock(return_value=[fake_chunk]),
        ),
        patch(
            "src.agents.nodes.draft_node.rag_service.generate_answer_with_citations",
            new=AsyncMock(return_value={"answer": "Hi there!", "citations": []}),
        ),
    ):
        result = await agent.ainvoke({"query": "Hello"})
    assert "response" in result


@pytest.mark.asyncio
async def test_agent_state_structure():
    result = await agent.ainvoke({"query": "Test query"})
    assert isinstance(result, dict)
    assert "query" in result
