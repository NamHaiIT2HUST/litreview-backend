import json
from uuid import uuid4

from src.services.synthesis_session_utils import json_paper_ids, uuid_paper_ids


def test_json_paper_ids_are_safe_for_sqlite_json_columns():
    paper_id = uuid4()

    result = json_paper_ids([paper_id])

    assert result == [str(paper_id)]
    assert json.loads(json.dumps(result)) == result


def test_uuid_paper_ids_restore_database_query_values():
    paper_id = uuid4()

    assert uuid_paper_ids([str(paper_id)]) == [paper_id]
