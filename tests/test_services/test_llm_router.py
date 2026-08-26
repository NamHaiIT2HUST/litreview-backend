"""Guards for provider selection and failure handling.

The behaviour being pinned is mostly about what does *not* happen: how many
paid calls a misconfiguration is allowed to cost, and which fallbacks are
forbidden. Both are easy to relax by accident, and both were relaxed before.
"""
import pytest

from src.services.llm import (
    FailureKind,
    LLMBudgetExceededError,
    ModelProfile,
    NoCapableProviderError,
    UnknownModelError,
    UnknownTaskError,
    classify,
    get_capability,
    get_profile,
    reset_store,
    select,
)
from src.services.llm.capability import LLMCapability
from src.services.llm.invoker import CallBudget, ainvoke_with_failover


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Start from no credentials and no priority, so tests state their own."""
    for var in [
        "LLM_PROVIDER_PRIORITY",
        "OPENAI_API_KEY", "OPENAI_API_KEYS", "OPENAI_MODEL",
        "GEMINI_API_KEY", "GEMINI_API_KEYS", "GOOGLE_API_KEY", "GEMINI_MODEL",
        "GROQ_API_KEY", "GROQ_API_KEYS", "GROQ_MODEL",
        "DEEPSEEK_API_KEY", "DEEPSEEK_API_KEYS",
        "OPENROUTER_API_KEY", "XKIRO_API_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)
    reset_store()
    yield
    reset_store()


class _FakeRunner:
    """Counts invocations, so a test can assert on calls actually made."""

    def __init__(self, error=None, result="ok"):
        self.error = error
        self.result = result
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


def _status_error(code, message="failed"):
    exc = RuntimeError(message)
    exc.status_code = code
    return exc


class TestErrorClassification:
    """Everything was transient before, which is what made failures expensive."""

    @pytest.mark.parametrize("code,expected", [
        (400, FailureKind.BAD_REQUEST),
        (401, FailureKind.AUTH),
        (403, FailureKind.PERMISSION),
        (404, FailureKind.NOT_FOUND),
        (422, FailureKind.BAD_REQUEST),
        (429, FailureKind.QUOTA),
        (500, FailureKind.TRANSIENT),
        (503, FailureKind.TRANSIENT),
    ])
    def test_status_codes(self, code, expected):
        assert classify(_status_error(code)) is expected

    def test_quota_wording_wins_over_a_4xx_status(self):
        # Providers report exhaustion with assorted 4xx codes whose body says
        # "rate limit"; treating those as permanent would strand a live key.
        assert classify(_status_error(400, "rate limit exceeded")) is FailureKind.QUOTA

    def test_unrecognised_failures_are_treated_as_permanent(self):
        # The deliberate inversion of the old default: an unknown error retried
        # across every key and provider is how one misconfiguration became a bill.
        assert classify(RuntimeError("something nobody has seen")).is_permanent

    def test_model_not_found_is_permanent(self):
        assert classify(_status_error(404)).is_permanent
        assert classify(_status_error(400)).is_permanent


class TestSelection:
    def test_picks_the_first_provider_with_a_usable_key(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "openai,gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake")
        reset_store()

        selection = select("extract_evidence")
        assert selection.profile.provider == "gemini"
        assert "openai" in selection.skipped

    def test_priority_is_per_operator(self, monkeypatch):
        # Each person orders providers in their own .env, so preferring the keys
        # you have never means editing a shared file.
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake")

        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "openai,gemini")
        reset_store()
        assert select("extract_evidence").profile.provider == "openai"

        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "gemini,openai")
        reset_store()
        assert select("extract_evidence").profile.provider == "gemini"

    def test_a_provider_that_cannot_do_the_work_is_skipped(self, monkeypatch):
        # Having a credential is not the same as being able to do the job. The
        # gate is what stops an unrestricted fallback from answering with
        # something that cannot honour the request -- a failure that does not
        # raise and is not correct.
        from src.services.llm import registry

        too_small = ModelProfile(
            provider="deepseek",
            model="deepseek-chat",
            context_window=4_000,
            supports_json_schema=False,
            supports_json_mode=False,
            supports_function_calling=False,
            supports_tool_calling=False,
            cost_tier=1,
        )
        monkeypatch.setitem(registry.MODEL_REGISTRY, too_small.key, too_small)

        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "deepseek,gemini")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake-deepseek")
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake")
        reset_store()

        selection = select("extract_evidence")
        assert selection.profile.provider == "gemini"
        assert "structured-output" in selection.skipped["deepseek"]

    def test_no_capable_provider_lists_every_reason(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "openai,gemini")
        reset_store()

        with pytest.raises(NoCapableProviderError) as exc_info:
            select("extract_evidence")
        message = str(exc_info.value)
        assert "openai" in message and "gemini" in message

    def test_an_undeclared_task_is_refused(self):
        with pytest.raises(UnknownTaskError):
            get_capability("some_task_nobody_declared")

    def test_an_unregistered_model_is_refused(self):
        with pytest.raises(UnknownModelError):
            get_profile("openai", "gpt-9-imaginary")


class TestCredentialRotation:
    def test_several_keys_rotate_in_a_fixed_order(self, monkeypatch):
        # Deterministic, unlike the random.choice this replaces: the same input
        # picks the same key, so a failure can be reproduced and a cost attributed.
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "gemini")
        monkeypatch.setenv("GEMINI_API_KEYS", "lien:AIza1,huyen:AIza2,team:AIza3")
        reset_store()

        aliases = [select("extract_evidence").credential.alias for _ in range(4)]
        assert aliases == ["lien", "huyen", "team", "lien"]

    def test_a_key_out_of_quota_is_set_aside(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "gemini")
        monkeypatch.setenv("GEMINI_API_KEYS", "spent:AIza1,fresh:AIza2")
        reset_store()

        first = select("extract_evidence")
        first.credential.cool_down()

        for _ in range(3):
            assert select("extract_evidence").credential.alias != first.credential.alias


class TestFailoverCost:
    """The point of the whole exercise, expressed in calls made."""

    @pytest.mark.asyncio
    async def test_a_permanent_failure_costs_exactly_one_call(self, monkeypatch):
        # This is the case that used to cost up to twenty-four.
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "gemini,openai")
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
        reset_store()

        runner = _FakeRunner(error=_status_error(404, "model not found"))
        with pytest.raises(RuntimeError):
            await ainvoke_with_failover("extract_evidence", lambda _client: runner, [])
        assert runner.calls == 1

    @pytest.mark.asyncio
    async def test_no_configured_provider_costs_zero_calls(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "openai,gemini")
        reset_store()

        runner = _FakeRunner()
        with pytest.raises(NoCapableProviderError):
            await ainvoke_with_failover("extract_evidence", lambda _client: runner, [])
        assert runner.calls == 0

    @pytest.mark.asyncio
    async def test_a_rejected_key_is_not_retried(self, monkeypatch):
        # One attempt per key, then the next key. Not four attempts per key.
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "gemini")
        monkeypatch.setenv("GEMINI_API_KEYS", "a:AIza1,b:AIza2")
        reset_store()

        runner = _FakeRunner(error=_status_error(401, "invalid api key"))
        with pytest.raises(RuntimeError):
            await ainvoke_with_failover("extract_evidence", lambda _client: runner, [])
        assert runner.calls == 1

    @pytest.mark.asyncio
    async def test_the_budget_stops_a_runaway(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake")
        reset_store()

        runner = _FakeRunner(error=_status_error(503, "unavailable"))
        budget = CallBudget(max_calls=2, label="test")
        with pytest.raises(LLMBudgetExceededError):
            await ainvoke_with_failover(
                "extract_evidence", lambda _client: runner, [], budget=budget
            )
        assert runner.calls <= 2

    @pytest.mark.asyncio
    async def test_a_successful_call_reports_who_served_it(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "gemini")
        monkeypatch.setenv("GEMINI_API_KEYS", "team:AIzaFake")
        reset_store()

        runner = _FakeRunner(result="answer")
        result, outcome = await ainvoke_with_failover(
            "extract_evidence", lambda _client: runner, []
        )
        assert result == "answer"
        assert outcome.attempts == 1
        assert outcome.selection.credential.alias == "team"
        assert outcome.selection.profile.provider == "gemini"


class TestCapabilityGate:
    def test_a_schema_task_needs_structured_output(self):
        capability = LLMCapability(json_schema=True, min_context=8_000)
        no_structured_output = ModelProfile(
            provider="test", model="plain-text-only", context_window=128_000,
            supports_json_schema=False, supports_json_mode=False,
            supports_function_calling=False, supports_tool_calling=False, cost_tier=1,
        )
        ok, reason = capability.satisfied_by(no_structured_output)
        assert not ok and "structured-output" in reason

    def test_json_mode_alone_is_accepted_for_schema_tasks(self):
        # Native schema support is not required. json_mode plus Pydantic
        # validation on our side reaches the same guarantee, and refusing it
        # would rule out most gateway-hosted models for no benefit.
        capability = LLMCapability(json_schema=True, min_context=8_000)
        json_mode_only = ModelProfile(
            provider="test", model="json-mode-only", context_window=128_000,
            supports_json_schema=False, supports_json_mode=True,
            supports_function_calling=False, supports_tool_calling=False, cost_tier=1,
        )
        ok, _ = capability.satisfied_by(json_mode_only)
        assert ok

    def test_context_window_is_enforced(self):
        capability = LLMCapability(json_schema=False, min_context=500_000)
        ok, reason = capability.satisfied_by(get_profile("openai", "gpt-4o-mini"))
        assert not ok and "context window" in reason

    def test_every_declared_task_can_be_served_by_some_registered_model(self):
        # A task whose requirements no model meets is a configuration trap that
        # only shows up when that task first runs.
        from src.services.llm.capability import TASK_REGISTRY
        from src.services.llm.registry import MODEL_REGISTRY

        for task, capability in TASK_REGISTRY.items():
            assert any(
                capability.satisfied_by(profile)[0] for profile in MODEL_REGISTRY.values()
            ), f"No registered model can serve task {task!r}"
