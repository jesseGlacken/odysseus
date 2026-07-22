# Task for frontend-dev

You are analyzing whether the existing Linear tickets (ODY-25 through ODY-31) are sufficient to replicate the existing Odysseus v1 vanilla-JS frontend into the v2 React SPA. Below is the full inventory of the v1 frontend. Compare it against the tickets and report gaps.

## Existing Frontend Structure (v1)

### Application Shell & Layout
- SPA entry: `static/index.html` (2,492 lines) — DOM skeleton with chat history, composer, sidebar, icon rail, modals, loading overlay
- Login: `static/login.html` — standalone login/register/setup page
- CSS: `static/style.css` (40,453 lines) — monolithic, all styles
- Orchestrator: `static/app.js` — imports all feature modules, routes deep-links (/notes, /calendar, /email, /memory, /gallery, /cookbook, /library, /tasks), wires global events
- Foundation modules: ui.js, storage.js, markdown.js, spinner.js, keyboard-shortcuts.js, sidebar-layout.js, section-management.js, modalManager.js, tileManager.js, windowDrag.js, modalSnap.js, toolWindowZOrder.js, windowResize.js

### Core Subsystems (by module size, descending)

1. **Chat Pipeline** (13 modules): chat.js (5,457), chatRenderer.js (2,764), chatStream.js, streamingRenderer.js, streamingSegmenter.js, slashCommands.js (6,513), slashAutocomplete.js, composerArrowUpRecall.js, assistant.js, tts-ai.js, voiceRecorder.js, fileHandler.js, codeRunner.js
   - Chat submit → SSE streaming → progressive rendering of text/tools/research/documents
   - Slash commands (/help, /setup, etc.) with autocomplete
   - File attachments (paste, drag-drop, upload button)
   - Voice recording + TTS
   - Code execution affordances
   - Multi-round agent state, background streams, stall detection

2. **Documents** (2 modules): document.js (11,038), documentLibrary.js (3,420)
   - Tabbed document editor with AI edit suggestions
   - Markdown/HTML/CSV editing
   - Document streaming (streamDocOpen/streamDocDelta)
   - Document library modal for browsing/searching

3. **Email** (6 modules): emailLibrary.js (7,784), emailInbox.js (1,374), emailShared.js, replyRecipients.js, signatureFold.js, state.js, utils.js
   - Inbox reader, compose, threading
   - IMAP folder management
   - Signatures, reply recipients
   - Account management

4. **Settings** (1 module): settings.js (5,795) — models, search, appearance, users, MCP, RAG, embedding, tokens

5. **Notes** (1 module): notes.js (5,373) — notes editor, todo panel, reminders, pinboard

6. **Cookbook** (12 modules): cookbook.js (3,506), cookbookRunning.js (4,404), cookbookServe.js (4,000), cookbook-hwfit.js (2,668), cookbook.js, cookbook-diagnosis.js, cookbook-deps-recipes.js, cookbookDownload.js, cookbookPorts.js, cookbookProgressSignal.js, cookbookSchedule.js
   - Model download/serve flow
   - Hardware fitting, diagnosis, dependency recipes
   - Running job cards, scheduling, port detection, progress computation

7. **Calendar** (3 modules): calendar.js (3,722), calendar/reminders.js, calendar/utils.js
   - Calendar views, event forms, reminders, CalDAV sync

8. **Gallery/Editor** (40+ modules): gallery.js (2,958), galleryEditor.js (3,928), editor/ (35+ files)
   - Image library browser
   - Full canvas editor: layers, brush, inpaint (AI), crop, filters, history, AI model runners
   - 35+ editor submodules for canvas, tools, filters, layers, AI operations

9. **Sessions** (1 module): sessions.js (3,483) — session list, CRUD, library modal, streaming/research indicators

10. **Admin** (1 module): admin.js (3,123) — privileged user/endpoint configuration

11. **Research** (3 modules): research/panel.js (1,259), research/jobs.js, researchSynapse.js
    - Research panel, job list, animated progress visualization in chat bubbles

12. **Model/Presets** (7 modules): models.js, modelPicker.js, modelSort.js, model/matchKey.js, providers.js, providerDeviceFlow.js, presets.js
    - Model discovery, selection, provider management, character/presets

13. **Theming** (1 module): theme.js (2,115) — theme presets, custom colors, fonts, backgrounds, live switching

14. **Skills** (1 module): skills.js (1,970) — skill library UI, import, edit, delete, test, audit

15. **Compare** (9 modules): compare/index.js, state.js, stream.js, panes.js, selector.js, scoreboard.js, probe.js, vote.js, icons.js
    - Model comparison: parallel SSE streams, side-by-side panes, scoring, voting

16. **Memory/RAG** (2 modules): memory.js (1,532), rag.js — AI memory CRUD, personal doc RAG

17. **Tasks** (1 module): tasks.js (2,949) — scheduled task / recurring LLM job UI

18. **Additional** (20+ modules): a11y.js, censor.js, colorPicker.js, color/hex.js, dragSort.js, emojiPicker.js, emojiShortcodes.js, escMenuStack.js, group.js, init.js, langIcons.js, markdown/tableRow.js, search.js, search-chat.js, signature.js, storage.js, tourAutoplay.js, tourHints.js, workspace.js, platform.js, util/ordinal.js

### Icon Rail (sidebar navigation buttons in static/index.html lines ~677-701):
Search | New Chat | Delete | Chats | Documents | Calendar | Compare | Cookbook | Research | Email | Gallery | Library | Memory | Notes | Tasks | Theme | Settings

### Existing Linear Tickets:
P3.1 (ODY-25): Scaffold apps/web/ — React 19 + Vite SPA (app shell, routes structure)
P3.2 (ODY-26): Scaffold packages/ui/ — Accessible Component Library (Button, Input, Dialog, Select, Combobox, DropdownMenu, Tabs)
P3.3 (ODY-27): Wire TanStack Query to the SDK (auth, chat, docs, email hooks, SSE streaming hook)
P4.1 (ODY-28): Migrate Auth Domain to React SPA (login/register screens)
P4.2 (ODY-36): Migrate Chat Domain to React SPA (session list, messages, input, SSE, tool calls)
P4.3a (ODY-31): Migrate Documents Domain to React SPA (list, upload, viewer, search)
P4.3b (ODY-30): Migrate Email Domain to React SPA (inbox, compose, folders, accounts)
P4.3c (ODY-29): Migrate Remaining Domains (Cookbook, Notes/Calendar, Gallery, Settings)

### Existing v2 packages that are created by other Phase 3 tickets:
- packages/ui: Button, Input, Dialog, Select, Combobox, DropdownMenu, Tabs
- packages/client-sdk: Generated typed TS client
- packages/config: Shared TS/ESLint/Tailwind/Vitest presets

## Task
Identify what UI structure and behaviors exist in v1 that are NOT covered by the existing tickets. For each gap:
1. Name the missing work item
2. Describe what needs to be built
3. Identify which existing ticket it blocks on or is blocked by
4. Estimate relative effort (S/M/L/XL)

## Acceptance Contract
Acceptance level: reviewed
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope
- criterion-2: Return evidence sufficient for an independent acceptance review

Required evidence: changed-files, tests-added, commands-run, validation-output, residual-risks, no-staged-files

Review gate: required by reviewer.

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
`criteriaSatisfied[].status` must be exactly one of: satisfied, not-satisfied, not-applicable.
`commandsRun[].result` must be exactly one of: passed, failed, not-run.
`manualNotes` and `notes` are optional strings; an empty string means no note and does not satisfy `manual-notes` evidence.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    },
    {
      "id": "criterion-2",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```