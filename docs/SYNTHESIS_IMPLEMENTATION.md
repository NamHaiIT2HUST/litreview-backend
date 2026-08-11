# Evidence-first Literature Synthesis

## What was added

The synthesis path is now separated from the legacy chat/RAG path. Search and
retrieval only find candidate source regions; generated review prose is built
from grounded evidence records and verified cross-paper claims.

```text
Selected papers
    ↓
plan comparison dimensions
    ↓
fan-out by paper
    ↓
Chroma retrieves anchor chunks
    ↓
PageText rebuilds continuous raw page windows
    ↓
LLM extracts {value, verbatim quote, anchor chunk id}
    ↓
deterministic grounding + raw page offsets (max 2 attempts)
    ↓
EvidenceRecord
    ↓
cross-paper claim generation
    ↓
claim-level verification against the evidence set
    ↓
outline from verified claims
    ↓
fan-out by section
    ↓
section draft from allowed claims only
    ↓
code-owned citation resolver
    ↓
final review + clickable source evidence
```

## Provenance model

### `PageText`

Stores the exact `PyPDFLoader` page text for one ingestion version. It is the
source-of-truth coordinate system for `page_char_start/page_char_end`.

### `PDFChunk`

Stores the chunk plus canonical DB identifiers and page-relative offsets. Chroma
stores these identifiers in metadata; an LLM never creates canonical chunk IDs.

### `EvidenceExtractionAttempt`

Audit-only table. Failed and successful LLM extraction/grounding attempts remain
here so retries can be evaluated later. A rejected attempt never becomes clean
evidence.

### `EvidenceRecord`

Contains only deterministically grounded evidence. `quote` is verbatim source
text (modulo normalization used only for locating); `value` is the model's
structured interpretation. Raw offsets always point into `PageText.full_text`.

### `SynthesisClaim` + `ClaimEvidenceLink`

A claim is verified against its linked evidence **as a set**. This matters for
meta-claims such as disagreement across studies: two different study findings
may jointly support the meta-claim even though neither entails it alone.

### `SynthesisSection`

Outline sections are created only after verified claims exist. The outline is
therefore evidence-driven rather than generated before reading the selected
papers.

## Grounding rules

1. `RecursiveCharacterTextSplitter(add_start_index=True)` records each chunk's
   page-relative start.
2. Ingestion checks the invariant:
   `PageText.full_text[start:end] == chunk.page_content`.
3. Chroma retrieves anchor chunk IDs only.
4. Grounding rebuilds a continuous raw window from the anchor's previous/current/
   next chunk **using PageText offsets**, not by concatenating overlapped chunks.
5. Normalization may collapse PDF whitespace and line-break hyphenation only for
   locating. A normalization-to-raw index map converts the match back to raw page
   offsets.
6. Fuzzy similarity never makes evidence valid.
7. First-pass grounding failures receive one exact-quote retry. After attempt 2,
   the candidate is rejected.

A sentence split across two PDF pages is currently a safe false-negative: the
system grounds within one persisted page and rejects evidence it cannot locate.

## Async job runtime

```text
FastAPI POST /api/v1/synthesis-sessions
    ↓
Redis queue
    ↓
Celery worker
    ↓
LangGraph workflow
    ├── PostgreSQL (domain data + checkpoints)
    ├── Chroma server (vector retrieval)
    └── LLM API (structured outputs)
```

Transient built-in timeout/connection failures stay `processing` while Celery
retries. The session is marked `failed` only after retry exhaustion or a
terminal logic/data error.

## API

### Start synthesis

```http
POST /api/v1/synthesis-sessions
Content-Type: application/json

{
  "project_id": "<project UUID>",
  "paper_ids": ["<paper UUID>", "<paper UUID>"]
}
```

All selected papers must belong to the project and have a provenance-aware PDF
ingestion (`active_ingestion_id`).

### Poll result

```http
GET /api/v1/synthesis-sessions/<session UUID>
```

The final response contains `review_markdown` and citation objects with:

- canonical paper ID;
- review marker and review-character range;
- source page;
- raw source-character range;
- grounded quote.

## Running with Docker Compose

1. Copy `.env.example` to `.env` and provide an LLM API key/model.
2. Start the stack:

```bash
docker compose up --build
```

Services:

- backend: `localhost:8000`
- PostgreSQL: host port `5434`
- Redis: `6379`
- Chroma server: host port `8001`
- Celery worker: internal service

The backend runs `alembic upgrade head` before Uvicorn starts.

## Re-ingestion requirement

Papers indexed before this change do not contain `page_text_id`, canonical
`chunk_id`, ingestion version, or page offsets in their vector metadata. They
must be uploaded/ingested again before they can be selected for the new
synthesis path. Old persisted evidence remains versioned; the new ingestion is
recorded separately.

## Important current boundary

The stored offsets refer to **extracted page text**, not PDF pixel coordinates.
They are sufficient for grounding and source-text display. A future UI feature
that highlights the exact region on the rendered PDF needs a layout-aware parser
that stores bounding boxes.
