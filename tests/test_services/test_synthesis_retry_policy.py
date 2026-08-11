from src.tasks.retry_policy import should_retry_synthesis, should_mark_failed


def test_transient_failure_retries_without_marking_terminal_failure():
    exc = TimeoutError("provider timeout")

    assert should_retry_synthesis(exc, retries=0, max_retries=2) is True
    assert should_mark_failed(exc, retries=0, max_retries=2) is False


def test_transient_failure_is_terminal_after_retry_budget_exhausted():
    exc = ConnectionError("redis/provider connection")

    assert should_retry_synthesis(exc, retries=2, max_retries=2) is False
    assert should_mark_failed(exc, retries=2, max_retries=2) is True


def test_non_transient_failure_is_terminal_immediately():
    exc = ValueError("invalid synthesis state")

    assert should_retry_synthesis(exc, retries=0, max_retries=2) is False
    assert should_mark_failed(exc, retries=0, max_retries=2) is True
