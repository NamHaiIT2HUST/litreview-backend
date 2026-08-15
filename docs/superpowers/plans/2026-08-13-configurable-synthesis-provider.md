# Configurable Synthesis Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make end-user synthesis reliably use Gemini by default while retaining an environment-only Groq option.

**Architecture:** Add synthesis provider settings and a tested provider factory inside `SynthesisLLMService`. Serialize provider calls through a configurable semaphore, retry transient failures, and reject missing provider credentials before creating a session.

**Tech Stack:** FastAPI, Pydantic Settings, LangChain Google GenAI, LangChain Groq, pytest.

## Global Constraints

- Gemini is the default synthesis provider.
- Grounding and citation behavior remain unchanged.
- No automatic provider mixing within one synthesis session.
- Work remains local; do not commit or push.

---

### Task 1: Provider configuration and factory

**Files:**
- Modify: `src/config.py`
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `.env.example`
- Modify: `requirements.txt`
- Test: `tests/test_services/test_synthesis_provider.py`

- [ ] Write failing tests for Gemini/Groq selection and missing-key errors.
- [ ] Implement the minimal provider factory and settings.
- [ ] Run the provider tests.

### Task 2: Reliable invocation and early validation

**Files:**
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `src/api/routes.py`
- Test: `tests/test_services/test_synthesis_provider.py`

- [ ] Write failing tests for concurrency and transient retry behavior.
- [ ] Add a shared semaphore and bounded retry with backoff.
- [ ] Validate synthesis credentials before accepting a session.
- [ ] Run backend regression tests.

### Task 3: Dependency and runtime verification

**Files:**
- Modify: `requirements.txt`

- [ ] Install declared dependencies.
- [ ] Run backend tests and frontend build.
- [ ] Restart backend and verify health endpoints.
