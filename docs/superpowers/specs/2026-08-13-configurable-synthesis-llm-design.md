# Configurable Synthesis LLM Design

## Goal

Allow evidence-first synthesis to use Gemini by default and switch to Groq using environment variables only, without changing application code. Prioritize successful end-user generation over maximum parallelism.

## Configuration

```env
SYNTHESIS_LLM_PROVIDER=gemini
SYNTHESIS_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=
```

To switch to Groq:

```env
SYNTHESIS_LLM_PROVIDER=groq
SYNTHESIS_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=
```

The backend must be restarted after configuration changes.

## Architecture

`SynthesisLLMService` remains the single adapter used by planning, evidence extraction, claim synthesis, claim verification, outline generation, and prose drafting. A small provider factory reads the synthesis-specific settings and creates either `ChatGroq` or `ChatGoogleGenerativeAI`. Grounding, evidence coverage, citation resolution, and sentence-level provenance remain provider-independent.

LLM calls share a small concurrency gate and transient provider failures are retried with backoff. There is no automatic cross-provider fallback inside a running session because silently mixing providers makes results difficult to reproduce. Configuration errors are rejected before a synthesis job is accepted.

## Error Handling

- Missing provider key reports the exact required environment variable.
- Unsupported provider reports the accepted values: `groq` and `gemini`.
- Provider errors propagate to the existing synthesis session failure state.
- Existing structured Pydantic outputs remain mandatory for both providers.

## Tests

- Groq configuration creates `ChatGroq` with the configured model and temperature.
- Gemini configuration creates `ChatGoogleGenerativeAI` with the configured model and temperature.
- Missing keys and unsupported providers fail with actionable messages.
- Existing synthesis coverage, response provenance, frontend sentence interaction, and production build checks continue to pass.

## Scope

Only the synthesis pipeline becomes provider-selectable. Existing general chat and embedding configuration are unchanged.
