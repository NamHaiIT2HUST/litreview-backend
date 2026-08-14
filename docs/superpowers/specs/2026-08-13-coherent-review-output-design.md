# Coherent Literature Review Output Design

## Goal

Generate a coherent literature review focused on the saved research question, without duplicated summaries or unrelated fallback sections, while preserving sentence-level provenance.

## Rules

- Synthesis cannot start until the project has a non-empty research question.
- Outline generation selects only claims directly relevant to that question.
- Claims omitted by the outline remain omitted; they are never forced into an `Additional findings` section.
- The outline prompt requests an introduction, thematic synthesis, research limitations/gaps, and conclusion when verified claims support those sections.
- The UI renders one article surface with continuous paragraphs and no duplicated per-section TLDR.
- Coverage labels show grounded evidence/source counts rather than implying scientific completeness.
- Sentence clicks retain existing evidence and AI-discourse popovers.

## Failure Handling

If relevance filtering leaves no usable sections, the session fails with an explicit message telling the user that the uploaded corpus does not support the research question. It must not generate unrelated filler.

## Verification

- Blank research questions are rejected before a session is created.
- Unselected claims do not become fallback sections.
- Frontend tests assert that article sections do not render duplicated TLDR blocks.
- Existing provenance and synthesis tests continue to pass.
