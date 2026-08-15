# Workspace Scoped Tabs Design

## Goal

Make Workspace clearly separate the two different workflows: generating a synthesis report and chatting with uploaded documents.

## User experience

- Keep the existing level-one navigation unchanged.
- Workspace contains two level-two tabs: `Chat với tài liệu` (default) and `Synthesis`.
- The left column remains the shared document context and PDF upload area.
- The shared source column shows a checkbox for every available source and displays the selected count as the scope for the whole Workspace.
- Both Synthesis and Chat use only the currently selected sources.
- Selection persists when switching tabs, defaults to all successfully processed sources, and new successfully processed uploads are added to the selection.
- Remove the floating duplicate source registry from Chat.
- Replace the old onboarding copy with concise contextual empty/ready-state copy.

## State and data flow

`WorkspaceTab` owns `selectedPaperIds`, initialized and reconciled against `allSources`. Removing a source also removes its selection. The selected source set is mapped to paper objects and passed to both panels.

`ChatPanel` receives the selected paper list and uses it as its retrieval scope. It must disable the input/send action when no paper is selected.

`SynthesisPanel` accepts the selected paper list and uses it when constructing the existing synthesis request. It must disable execution and show guidance when zero papers are selected or when the selected count exceeds the backend limit.

## Component changes

- `WorkspaceTab.jsx`: replace the collapsible synthesis header plus simultaneous chat layout with explicit sub-tabs, add shared source selection, and render one active content panel.
- `SourceCard`: render the shared checkbox while retaining remove behavior.
- `SynthesisPanel.jsx`: use the selected paper list, update scope copy, and preserve report/citation behavior.
- `ChatPanel.jsx`: use the selected paper list, remove the floating source registry, show scope copy, and disable sending without selected sources.

## Error handling and compatibility

- Preserve direct PDF upload, source removal, citation verification, chat API, and synthesis polling behavior.
- Preserve dark mode and responsive layout.
- If no sources exist, both tabs show an actionable empty state and upload remains available.
- No backend API changes are required.

## Verification

- Run the frontend lint script.
- Run the frontend production build.
- Check existing synthesis utility tests if available.
- Confirm both the synthesis request and Chat are wired only to selected papers, and that selection persists across tab changes.
