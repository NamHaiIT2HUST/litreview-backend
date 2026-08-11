from src.services.paper_persistence_utils import normalize_authors_for_db


def test_normalize_authors_for_db_splits_api_author_string():
    assert normalize_authors_for_db("Alice, Bob, Carol") == ["Alice", "Bob", "Carol"]


def test_normalize_authors_for_db_preserves_existing_list_and_empty_values():
    assert normalize_authors_for_db(["Alice", "Bob"]) == ["Alice", "Bob"]
    assert normalize_authors_for_db(None) == []
