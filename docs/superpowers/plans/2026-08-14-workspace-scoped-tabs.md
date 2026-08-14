# Workspace Scoped Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign Workspace into explicit Chat and Synthesis tabs with one persistent checkbox-based source scope shared by both workflows.

**Architecture:** `WorkspaceTab` owns `selectedPaperIds` and derives `selectedPapers` from the merged source list. It renders only the active panel, passing the filtered list to both `ChatPanel` and `SynthesisPanel`. Existing upload, polling, citation, and backend contracts remain intact.

**Tech Stack:** React 19, Vite, Tailwind utility classes, lucide-react, existing frontend lint/build scripts.

## Global Constraints

- Keep level-one navigation and all non-Workspace screens unchanged.
- Both Chat and Synthesis use only selected papers.
- Selection persists across tab changes; valid newly uploaded papers are selected by default.
- Remove the duplicate floating source registry from Chat.
- Preserve PDF upload, removal, ingestion, citations, polling, dark mode, and responsive behavior.
- No backend API changes.

---

### Task 1: Add shared source-selection model in WorkspaceTab

**Files:**
- Modify: `frontend/src/components/workspace/WorkspaceTab.jsx`

**Interfaces:**
- Produces `selectedPaperIds` state and `selectedPapers` derived from `allSources`.
- `SourceCard` receives `isChecked` and `onToggle` for the shared scope.

- [ ] **Step 1: Add `selectedPaperIds` state initialized from current sources.**

Initialize to `allSources.map((paper) => paper.id)` after source derivation, while avoiding a selection reset on every render.

- [ ] **Step 2: Reconcile selection when sources change.**

Retain existing IDs still present in `allSources` and add newly present ready/processed IDs; do not clear valid user choices during tab changes.

- [ ] **Step 3: Update upload and remove handlers.**

After a successful upload, add `data.paper_id` to `selectedPaperIds`. When removing a source, remove its ID from the shared selection.

- [ ] **Step 4: Derive `selectedPapers` and pass it to both panels.**

Keep `workspacePapers` as the full source registry, but pass `selectedPapers` to Chat and Synthesis.

- [ ] **Step 5: Run the frontend lint check.**

Run: `npm run lint --prefix frontend`

Expected: no new lint errors.

### Task 2: Make the source column express the shared scope

**Files:**
- Modify: `frontend/src/components/workspace/WorkspaceTab.jsx`

**Interfaces:**
- `SourceCard` renders the shared checkbox and still supports source removal.

- [ ] **Step 1: Replace selected-source preview behavior with checkbox behavior.**

Use a real checkbox/button control, stop propagation for remove, and make the entire row accessible for toggling.

- [ ] **Step 2: Update source-column header and copy.**

Show `N tài liệu · M đang được sử dụng`, keep upload controls, and preserve empty/upload queue states.

- [ ] **Step 3: Add the current scope line to the active content area.**

Render `Dựa trên M/N tài liệu` above the active panel, with subdued styling.

- [ ] **Step 4: Run lint again.**

Run: `npm run lint --prefix frontend`

Expected: PASS.

### Task 3: Replace the collapsible layout with explicit Workspace tabs

**Files:**
- Modify: `frontend/src/components/workspace/WorkspaceTab.jsx`

**Interfaces:**
- Maintains local `activeWorkspaceTab` with default `chat`.
- Renders exactly one of `ChatPanel` or `SynthesisPanel` at a time.

- [ ] **Step 1: Add the two-tab header.**

Use buttons labeled `Chat với tài liệu` and `Synthesis`; style active/inactive states for light and dark modes.

- [ ] **Step 2: Render only the active panel.**

Remove the expandable synthesis card and simultaneous chat grid. Pass `selectedPapers` to the active panel and retain `VerificationPanel` outside the panel content.

- [ ] **Step 3: Add contextual ready/empty copy.**

Use the selected count and total count; show an upload-oriented empty state when no sources exist and concise tab-specific guidance when sources exist.

- [ ] **Step 4: Run the production build.**

Run: `npm run build --prefix frontend`

Expected: Vite build succeeds.

### Task 4: Scope Synthesis and Chat behavior

**Files:**
- Modify: `frontend/src/components/workspace/SynthesisPanel.jsx`
- Modify: `frontend/src/components/workspace/ChatPanel.jsx`

**Interfaces:**
- Both components receive `workspacePapers` as the already-filtered selected list.

- [ ] **Step 1: Update Synthesis copy and guards.**

Use selected count in the header/scope line; keep the existing 1–15 backend guard and disable creation when the filtered list is empty or over the limit.

- [ ] **Step 2: Remove Chat’s floating source registry.**

Delete the duplicate absolute-positioned source list and retain citations/context references in AI messages.

- [ ] **Step 3: Disable Chat sending with no selected sources.**

Guard `handleSendMessage`, disable the input/button, and show `Chọn ít nhất 1 tài liệu ở cột trái để bắt đầu chat.` when the filtered list is empty.

- [ ] **Step 4: Keep the existing Chat API contract.**

Do not change endpoint behavior unless the current backend request schema already supports source IDs; preserve message history and citation rendering.

- [ ] **Step 5: Run existing frontend tests and lint.**

Run: `npm run lint --prefix frontend`

Run: `npm run build --prefix frontend`

Expected: both commands succeed.

### Task 5: Verify scope persistence and request wiring

**Files:**
- Test: existing `frontend/src/utils/synthesis.test.mjs` where utility-level coverage applies.
- Modify: `frontend/src/components/workspace/WorkspaceTab.jsx` only if verification finds a state bug.

- [ ] **Step 1: Confirm utility request construction uses filtered paper IDs.**

Run: `npm test --prefix frontend` if the project exposes a test script; otherwise run the existing Node test command used by the repository for `frontend/src/utils/*.test.mjs`.

- [ ] **Step 2: Verify production build output.**

Run: `npm run build --prefix frontend`.

- [ ] **Step 3: Inspect the final diff for scope invariants.**

Confirm tab changes do not reset `selectedPaperIds`, new successful uploads are selected, removed sources are deselected, and both panels receive only `selectedPapers`.

- [ ] **Step 4: Record verification results.**

Report exact commands and outcomes; do not claim completion without successful command output.
