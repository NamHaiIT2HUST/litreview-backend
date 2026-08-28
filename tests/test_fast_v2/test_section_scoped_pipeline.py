import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.planning.research_lead import LongformOutlinePlan, SectionPlan
from src.synthesis.fast_v2.section_pipeline import (
    SectionScopedSynthesisPipeline,
    WriterIncompleteError,
    format_section_contexts_prompt,
)


class MockStreamingChunk:
    def __init__(self, content: str, finish_reason: str = "stop", output_tokens: int = 100):
        self.content = content
        self.response_metadata = {"finish_reason": finish_reason} if finish_reason else {}
        self.usage_metadata = {"output_tokens": output_tokens} if output_tokens else None


class MockStreamingLLM:
    def __init__(self, chunks: list[MockStreamingChunk]):
        self.chunks = chunks
        self.bind_calls: list[dict] = []

    def bind(self, **kwargs):
        self.bind_calls.append(kwargs)
        return self

    async def astream(self, messages):
        for chunk in self.chunks:
            yield chunk


def test_format_section_contexts_prompt():
    outline = LongformOutlinePlan(
        research_question="What are CQ algorithms?",
        sections=(
            SectionPlan(
                id="sec_1",
                title="1. Introduction",
                purpose="Define split feasibility problem",
                target_words=500,
                papers_to_compare=("Byrne2002", "Xu2010"),
                retrieval_queries=("split feasibility problem",),
            ),
        ),
    )
    unit = EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(),
        title="Byrne (2002)",
        page=0,
        text="The CQ algorithm was introduced by Byrne.",
        source_chunk_id=uuid.uuid4(),
    )
    contexts = {"sec_1": [unit]}
    prompt = format_section_contexts_prompt(outline, contexts)

    assert "RESEARCH TOPIC: What are CQ algorithms?" in prompt
    assert "### Section 1: 1. Introduction" in prompt
    assert "- Section ID: sec_1" in prompt
    assert "Byrne (2002)" in prompt
    assert "The CQ algorithm was introduced by Byrne." in prompt


@pytest.mark.asyncio
async def test_section_scoped_pipeline_run():
    mock_retriever = MagicMock()
    unit = EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(),
        title="Byrne (2002)",
        page=1,
        text="Convergence of CQ method is proved for any non-empty solution set.",
        source_chunk_id=uuid.uuid4(),
    )
    mock_retriever.retrieve = AsyncMock(return_value=[unit])

    mock_reranker = MagicMock(spec=["rerank"])
    mock_reranker.rerank = MagicMock(return_value=[(0, 0.95)])

    writer_chunks = [
        MockStreamingChunk("# Literature Review on CQ Algorithms\n\n## 1. Introduction\n\n"),
        MockStreamingChunk("The CQ algorithm is a prominent projection method for split feasibility problems.\n\n"),
        MockStreamingChunk("Convergence of CQ method is proved for any non-empty solution set.", finish_reason="stop", output_tokens=350),
    ]
    mock_writer_llm = MockStreamingLLM(writer_chunks)

    mock_citation_llm = MagicMock()
    mock_citation_response = MagicMock()
    mock_citation_response.content = (
        '<paragraph id="0">The CQ algorithm is a prominent projection method for split feasibility problems.</paragraph>\n'
        '<paragraph id="1">Convergence of CQ method is proved for any non-empty solution set. [E001]</paragraph>'
    )
    mock_citation_llm.ainvoke = AsyncMock(return_value=mock_citation_response)

    pipeline = SectionScopedSynthesisPipeline(
        retriever=mock_retriever,
        reranker=mock_reranker,
        writer_llm=mock_writer_llm,
        citation_llm=mock_citation_llm,
    )

    outline = LongformOutlinePlan(
        research_question="CQ Method",
        sections=(
            SectionPlan(
                id="sec_1",
                title="1. Introduction",
                purpose="Foundations",
                target_words=500,
                papers_to_compare=(),
                retrieval_queries=("CQ method convergence",),
            ),
        ),
    )

    result = await pipeline.run(
        approved_outline=outline,
        paper_ids=[unit.paper_id],
    )

    assert result.synthesis_mode == "fast_v2_section_scoped"
    assert result.semantic_grounded is True
    assert len(result.citations) >= 1
    assert result.citations[0].citation_marker == "[E001]"
    assert result.citations[0].paper_title == "Byrne (2002)"
    assert mock_retriever.retrieve.call_count >= 1
    assert len(mock_writer_llm.bind_calls) >= 1
    assert mock_citation_llm.ainvoke.call_count >= 1


@pytest.mark.asyncio
async def test_section_scoped_pipeline_rejects_truncated_finish_reason_length():
    mock_retriever = MagicMock()
    unit = EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(),
        title="Byrne (2002)",
        page=1,
        text="Convergence of CQ method is proved.",
        source_chunk_id=uuid.uuid4(),
    )
    mock_retriever.retrieve = AsyncMock(return_value=[unit])
    mock_reranker = MagicMock(spec=["rerank"])
    mock_reranker.rerank = MagicMock(return_value=[(0, 0.95)])

    # finish_reason="length"
    writer_chunks = [
        MockStreamingChunk("# Title\n\nIncomplete text continuing without ending", finish_reason="length", output_tokens=8192),
    ]
    mock_writer_llm = MockStreamingLLM(writer_chunks)
    mock_citation_llm = MagicMock()
    mock_citation_llm.ainvoke = AsyncMock()

    pipeline = SectionScopedSynthesisPipeline(
        retriever=mock_retriever,
        reranker=mock_reranker,
        writer_llm=mock_writer_llm,
        citation_llm=mock_citation_llm,
    )

    outline = LongformOutlinePlan(
        research_question="CQ Method",
        sections=(
            SectionPlan(
                id="sec_1",
                title="1. Introduction",
                purpose="Foundations",
                target_words=500,
                papers_to_compare=(),
                retrieval_queries=("CQ method",),
            ),
        ),
    )

    with pytest.raises(WriterIncompleteError) as exc_info:
        await pipeline.run(approved_outline=outline, paper_ids=[unit.paper_id])

    assert "finish_reason='length'" in str(exc_info.value)
    assert mock_citation_llm.ainvoke.call_count == 0


@pytest.mark.asyncio
async def test_section_scoped_pipeline_rejects_truncated_incomplete_ending():
    mock_retriever = MagicMock()
    unit = EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(),
        title="Byrne (2002)",
        page=1,
        text="Convergence of CQ method is proved.",
        source_chunk_id=uuid.uuid4(),
    )
    mock_retriever.retrieve = AsyncMock(return_value=[unit])
    mock_reranker = MagicMock(spec=["rerank"])
    mock_reranker.rerank = MagicMock(return_value=[(0, 0.95)])

    # ends_normally=False (stops mid-sentence without punctuation)
    writer_chunks = [
        MockStreamingChunk("# Title\n\nThis algorithm is defined by the following step where gamma is", finish_reason="stop", output_tokens=500),
    ]
    mock_writer_llm = MockStreamingLLM(writer_chunks)
    mock_citation_llm = MagicMock()
    mock_citation_llm.ainvoke = AsyncMock()

    pipeline = SectionScopedSynthesisPipeline(
        retriever=mock_retriever,
        reranker=mock_reranker,
        writer_llm=mock_writer_llm,
        citation_llm=mock_citation_llm,
    )

    outline = LongformOutlinePlan(
        research_question="CQ Method",
        sections=(
            SectionPlan(
                id="sec_1",
                title="1. Introduction",
                purpose="Foundations",
                target_words=500,
                papers_to_compare=(),
                retrieval_queries=("CQ method",),
            ),
        ),
    )

    with pytest.raises(WriterIncompleteError) as exc_info:
        await pipeline.run(approved_outline=outline, paper_ids=[unit.paper_id])

    assert "ends_normally=False" in str(exc_info.value)
    assert mock_citation_llm.ainvoke.call_count == 0
