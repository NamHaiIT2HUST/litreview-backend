import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from src.models.schemas import SearchHistoryResponse, SearchQueryRecord, SearchResponse


def test_search_query_record_accepts_database_uuid_attributes():
    query_id = uuid.uuid4()
    project_id = uuid.uuid4()
    row = SimpleNamespace(
        id=query_id,
        project_id=project_id,
        query_string="rag hallucination",
        strategy_label=None,
        result_count=3,
        executed_at=datetime.now(UTC),
        is_duplicated_from=None,
    )

    record = SearchQueryRecord.model_validate(row)

    assert record.id == query_id
    assert record.project_id == project_id


def test_search_response_accepts_canonical_uuid_search_query_id():
    query_id = uuid.uuid4()

    response = SearchResponse(papers=[], search_query_id=query_id)

    assert response.search_query_id == query_id


def test_search_history_project_id_is_uuid():
    project_id = uuid.uuid4()
    response = SearchHistoryResponse(project_id=project_id, history=[])
    assert response.project_id == project_id
