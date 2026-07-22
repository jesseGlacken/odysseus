Now I have a thorough understanding of the entire v1 frontend and the ticket coverage. Let me compile the gap analysis.

---

## Gap Analysis Report: v1 → v2 Ticket Coverage

### Summary

**8 tickets** (ODY-25 through ODY-31, plus ODY-36) claim to cover the migration of ~130K lines of vanilla JS across ~100 modules. I have identified **12 categories of gaps**, many of which are blocking dependencies for the existing tickets.

---

### GAP-1: Foundation Infrastructure (Blocks ALL domain tickets)

| # | Missing Item | v1 Source | Description | Blocks / Blocked By | Effort |
|---|---|---|---|---|---|
| 1.1 | **i18n Layer** | (none — ADR-0005 mandate) | ADR-0005 requires "No hard-coded user-facing strings — use the i18n layer." No ticket provisions an i18n framework (react-i18next, formatjs, or similar). Must be in place before any domain ticket writes user-facing strings. | Blocked by ODY-25; Blocks ODY-28,29,30,31,36 | **M** |
| 1.2 | **Theme System** | `theme.js` (2,115 lines) | 16 built-in presets (dark, light, cyberpunk, retrowave, forest, ocean, terminal, etc.), custom theme editor, font family selection (4 choices + dyslexia font), background patterns, density (comfortable/compact), live switching, localStorage persistence. Theme tokens must feed into Tailwind design tokens. | Blocked by ODY-25; Blocks ALL UI tickets | **L** |
| 1.3 | **Markdown Rendering** | `markdown.js` (1,084 lines) | Markdown→HTML with thinking/reasoning block parsing (`<thinking>` tags), code-block normalization, code-fence extraction. Critical for chat messages, document viewer, research results, tool outputs. Not explicitly in any ticket — ODY-36 mentions "messages" but not the rendering infrastructure. | Blocked by ODY-25; Blocks ODY-31, ODY-36 | **L** |
| 1.4 | **Toast/Notification System** | `ui.js` (`showToast`, `showError`) | Every module uses toast notifications for success/error feedback. Not in ODY-26's component list. Needs a Sonner or Radix Toast primitive. | Blocked by ODY-26; Blocks ALL domain tickets | **S** |
| 1.5 | **Keyboard Shortcuts** | `keyboard-shortcuts.js` (292 lines) | Global keyboard shortcut dispatch (Ctrl+K search, Ctrl+N new chat, Escape handling, etc.). | Blocked by ODY-25; Blocks ODY-36 | **S** |
| 1.6 | **LocalStorage Helpers** | `storage.js` (125 lines) | Per-module state persistence in localStorage. Shared across all modules. | Blocked by ODY-25; Blocks ALL domain tickets | **S** |

---

### GAP-2: Missing Component Library Primitives (Blocks UI work)

ODY-26 covers 7 primitives: Button, Input, Dialog, Select, Combobox, DropdownMenu, Tabs. Below are the additional primitives needed to replicate v1 features, each of which needs to live in `packages/ui`:

| # | Missing Component | Used By | Effort |
|---|---|---|---|
| 2.1 | **Toast** | Every module for feedback | **S** |
| 2.2 | **Tooltip** | Icon rail, toolbar buttons, inline explanations | **S** |
| 2.3 | **Popover** | Model picker, color picker, presets selector, date picker | **M** |
| 2.4 | **Sheet/Drawer** | Settings panel, document library, sidebar panels | **S** |
| 2.5 | **Command Palette** (cmdk) | Slash commands, global search (Ctrl+K) | **M** |
| 2.6 | **Context Menu** | Right-click on sessions, documents, chat messages | **S** |
| 2.7 | **Slider** | Settings (temperature, top-p), image editor (brush size, opacity) | **S** |
| 2.8 | **Toggle / ToggleGroup** | Theme mode, settings toggles, toolbar formatting | **S** |
| 2.9 | **Badge** | Unread indicators, streaming status, model labels | **S** |
| 2.10 | **Toolbar** | Image editor topbar, document formatting | **M** |
| 2.11 | **Table / DataGrid** | Email inbox, document library, memory list, tasks list, skills list, admin tables. React Aria `useGridList`/`useTable` for proper row navigation and screen reader support. | **L** |
| 2.12 | **Card** | Cookbook job cards, memory cards, session cards | **S** |
| 2.13 | **Avatar** | User profile, assistant persona icons | **S** |
| 2.14 | **Progress** | Model download/serve progress, research progress | **S** |
| 2.15 | **Skeleton** | Loading states for chat history, document list, session list | **S** |
| 2.16 | **ScrollArea** | Chat message history (needs proper scroll-anchoring and auto-scroll behavior) | **S** |
| 2.17 | **Accordion / Collapsible** | Settings sections, sidebar category sections | **S** |
| 2.18 | **Switch / Checkbox / RadioGroup** | Settings toggles, multi-select, option lists | **S** |
| 2.19 | **Textarea** | Chat composer, document editor, email composer | **S** |

**Total gap for ODY-26: 19 additional primitives** (currently covers 7).

---

### GAP-3: Chat Pipeline Sub-Features Not in ODY-36

ODY-36 scope: "session list, messages, input, SSE, tool calls." Missing:

| # | Missing Sub-Feature | v1 Source | Description | Effort |
|---|---|---|---|---|
| 3.1 | **Slash Commands System** | `slashCommands.js` (6,513 lines) + `slashAutocomplete.js` (313 lines) | Command registry (`/help`, `/setup`, `/model`, `/preset`, `/theme`, `/censor`, `/compare`, `/notes`, `/memory`, `/tasks`, etc.), auto-detection of API keys, setup wizard flow, provider device-auth flow. This is a major subsystem — almost twice the size of the core chat controller. | **XL** |
| 3.2 | **File Attachments** | `fileHandler.js` (483 lines) | Paste, drag-drop, and upload-button file handling. Attachment strip rendering, pending-file management, image paste from clipboard. | **M** |
| 3.3 | **Voice Recording + TTS** | `voiceRecorder.js` (283 lines) + `tts-ai.js` (521 lines) | Microphone recording from composer, AI text-to-speech with streaming playback, enqueueing. | **M** |
| 3.4 | **Code Execution** | `codeRunner.js` (403 lines) | Client-side code execution affordances for code blocks returned by the model. | **M** |
| 3.5 | **Composer Arrow-Up Recall** | `composerArrowUpRecall.js` (61 lines) | Recall last user message with ↑ on empty composer. | **S** |
| 3.6 | **In-Chat History Search** | `search-chat.js` (201 lines) | Search within current chat history. | **S** |
| 3.7 | **Group Chat** | `group.js` (1,017 lines) | Multi-model orchestration chat where multiple models respond to the same prompt. | **L** |
| 3.8 | **Background Streams** | Within `chat.js` | Session-switching during active SSE streams, completion notifications, state preservation. | **M** |
| 3.9 | **Streaming Tool Call Rendering** | `streamingRenderer.js` + `streamingSegmenter.js` + `chatRenderer.js` (2,764 lines) | Progressive rendering of text/tools/research/documents. Agent-thread visualization with wave animation, tool stdout/stderr live tail, diff rendering, screenshot rendering, findings box, sources box, ask-user cards. The "tool calls" scope in ODY-36 is a single word for a massive rendering subsystem. | **XL** |

---

### GAP-4: Complete Domains Missing from Any Ticket

| # | Missing Domain | v1 Source | Description | Effort |
|---|---|---|---|---|
| 4.1 | **Compare Mode** | `compare/` (9 modules) | Model A/B comparison with up to 8 parallel SSE streams, side-by-side panes, scoring, voting, confetti animations, model selection, prompt library. **Completely absent from all tickets.** | **XL** |
| 4.2 | **Research Panel** | `research/panel.js` + `research/jobs.js` + `researchSynapse.js` | Research job list UI, controls, job polling, animated progress visualization inside chat bubbles. Not in ODY-29's catch-all. | **L** |
| 4.3 | **Memory / Brain** | `memory.js` (1,532 lines) + `rag.js` (177 lines) | AI memory CRUD with categories (fact, identity, preference, contact, project, goal, task), search/filter, sort (newest/oldest/A-Z/most-used), select mode, bulk delete, memory extraction. Personal document RAG: add directories/files, show included paths. **Not in any ticket.** | **L** |
| 4.4 | **Tasks** | `tasks.js` (2,949 lines) | Scheduled recurring LLM job UI with cron editing (minute/hour/day/week/month presets + custom), run history viewer, enable/disable toggles, onboarding wizard, failure detection badge on icon rail. **Not in any ticket.** | **L** |
| 4.5 | **Skills** | `skills.js` (1,970 lines) | Skill library with list/search, SKILL.md viewer/editor, publish/draft toggle, delete, "run as slash" via `/<skill-name>`, audit status display, cascading card entrance animations. **Not in any ticket.** | **M** |
| 4.6 | **Admin Panel** | `admin.js` (3,123 lines) | Privileged user management, endpoint configuration, system-level controls. **Not in any ticket.** | **M** |
| 4.7 | **Model/Provider Management** | `models.js` + `modelPicker.js` + `modelSort.js` + `providers.js` + `providerDeviceFlow.js` + `presets.js` | Model discovery/scanning, port probing for local models, provider management, OAuth device-flow, model picker dropdown in composer, model sorting, character/preset selection and saving. Partially overlaps with chat (composer model picker) and settings (provider config), but is its own subsystem. | **L** |
| 4.8 | **Web Search Config** | `search.js` (52 lines) | Web-search provider selection, API key management. Small but needed. | **S** |

---

### GAP-5: Gallery/Image Editor Severely Underestimated

ODY-29 lists "Gallery" as 1 of 4 items alongside Cookbook, Notes/Calendar, and Settings. The v1 gallery subsystem is:

| Module Group | Files | Lines | Description |
|---|---|---|---|
| Gallery entry | `gallery.js` + `galleryEditor.js` | 6,886 | Image library browser + canvas editor entry |
| Editor BUILD | 6 files (`build/`) | ~600 | Controls, popups, right-panel, toolbar, topbar, transform-popup |
| Editor CANVAS | 4 files | ~530 | Coordinates, events, transforms, checkerboard |
| Editor TOOLS | 9 files | ~1,200 | Clone, crop, flood-fill, lasso, lasso-mask, move, stroke, transform-drag, transform-handles, transform-session, wand |
| Editor AI | 5 files | ~650 | AI inpainting, AI models, background removal, tool runner, misc |
| Editor WIRING | 7 files | ~1,100 | Topbar, menus, overflow, import, inpaint-controls, selection-controls, merge-buttons |
| Editor OTHER | 11 files | ~1,200 | Filters (blur, edge-feather), FX (adj-popup, filter-string, histogram, pixel-pass), harmonize-masks, history-panel, keyboard-shortcuts, layer-helpers, layer-panel, mask-utils, shortcuts-popover, slider-ux, snap, state, stroke-pipeline, stroke-tool-sliders, clipboard-and-drop, composite-helpers |
| **Total** | **50+ files** | **~12,000+ lines** | Full canvas image editor |

This is an **XL** subsystem by itself. Cramming it into ODY-29 alongside 3 other domains makes the ticket unrealistic.

---

### GAP-6: Modal/Window Management System

The v1 has a desktop-like floating window system used by Documents, Email, Calendar, Notes, Tasks, Memory, Skills, Admin, Cookbook, Research, and Gallery:

| Module | Lines | Responsibility |
|---|---|---|
| `modalManager.js` | 1,560 | Unified minimize/restore behavior across all tool modals |
| `modalSnap.js` | 1,079 | Snap-to-edge/corner behavior for floating panels |
| `tileManager.js` | 394 | Window tiling and snap-to-edge |
| `windowDrag.js` | 333 | Drag support for floating panels (with iframe-aware event capture) |
| `windowResize.js` | 233 | Resize handles on floating panels |
| `toolWindowZOrder.js` | 46 | Z-index stack management |
| **Total** | **3,645** | |

No ticket covers this. It's a prerequisite for every tool-modal domain (Documents, Email, Calendar, Notes, Tasks, Memory, Skills, Admin, Cookbook, Research, Gallery).

---

### GAP-7: Sidebar / Icon Rail Navigation System

| Module | Lines | Description |
|---|---|---|
| `sidebar-layout.js` | 565 | Icon rail ↔ wide sidebar layout, responsive breakpoints |
| `section-management.js` | 260 | Collapsible/draggable sidebar sections |
| Icon rail in index.html | ~25 elements | 18 navigation buttons + resize handle |

ODY-25 (app shell) may partially cover this, but the complexity of the responsive sidebar/rail with collapsible sections, drag-to-reorder, session indicators, and mobile hamburger behavior is substantial.

---

### GAP-8: Testing & CI Infrastructure

| # | Missing Item | Description | Blocks |
|---|---|---|---|
| 8.1 | **E2E Test Setup** | playwright-bdd per ADR-0004. `.feature` files in `features/`. No ticket provisions test infrastructure. | Blocks ALL domain tickets (tests must be written per ADR-0004) |
| 8.2 | **A11y CI Gates** | axe-core/playwright integration, Lighthouse CI budgets per ADR-0005. | Blocks ALL domain tickets |
| 8.3 | **vitest Setup** | Unit/component test runner for apps/web. Not in ODY-25. | Blocks ALL domain tickets |
| 8.4 | **i18n Extraction/Linting** | Tooling to enforce "no hard-coded strings." | Blocks ODY-28 onwards |
| 8.5 | **Nx workspace config** | `nx.json`, project configs, task graph. ODY-25 mentions "scaffold" but the Nx monorepo config is its own effort. | Blocks ODY-25 |

---

### GAP-9: Onboarding & Product Tour

| Module | Lines | Description |
|---|---|---|
| `tourHints.js` | 179 | Onboarding hints and tooltips |
| `tourAutoplay.js` | 133 | Auto-playing product tour |

Small but needed for new-user experience. No ticket covers this.

---

### GAP-10: Cross-Cutting Utility Modules

| Module | Lines | Description | Effort |
|---|---|---|---|
| `emojiPicker.js` + `emojiShortcodes.js` | 771 | Emoji picker popup + shortcode autocomplete (`:smile:`) | **S** |
| `colorPicker.js` + `color/hex.js` | 467 | Color picker widget + hex utilities | **S** |
| `dragSort.js` | 265 | Drag-to-reorder shared behavior (sidebar sessions, lists) | **S** |
| `escMenuStack.js` | 102 | Stack-based Escape handling for nested dismissible popups | **S** |
| `langIcons.js` | 187 | Programming language icon mapping for code blocks | **S** |
| `censor.js` | 356 | Content warning overlay for text/images | **S** |
| `platform.js` | 47 | macOS/Windows/Linux detection, keyboard modifier helpers | **S** |
| `signature.js` | 524 | Email signature management (partially in ODY-30 scope?) | **S** |

---

### GAP-11: Deep-Link & Route Architecture

v1 `app.js` handles deep-link route openers: `/notes`, `/calendar`, `/email`, `/memory`, `/gallery`, `/cookbook`, `/library`, `/tasks`. ODY-25 mentions "routes structure" but no ticket defines:
- Which TanStack Router route maps to which domain
- How deep-links trigger tool modal opening
- Protected vs public route guards (auth)
- 404 / error route handling

---

### GAP-12: Cookbook Domain Severely Underestimated

ODY-29 lists "Cookbook" as 1 of 4 items. The v1 cookbook has 12 modules:

| Module | Lines | Description |
|---|---|---|
| `cookbook.js` | 3,506 | Main UI: hardware fitting, presets, action panels |
| `cookbookRunning.js` | 4,404 | Running job cards with progress, logs, stop/cancel |
| `cookbookServe.js` | 4,000 | Model serving configuration, port selection, GPU layers |
| `cookbook-hwfit.js` | 2,668 | Hardware-fit scoring and recommendations |
| `cookbook-diagnosis.js` | 1,074 | Dependency diagnosis and troubleshooting |
| `cookbook-deps-recipes.js` | 107 | Dependency installation recipes |
| `cookbookDownload.js` | 658 | Model download UI with progress |
| `cookbookPorts.js` | 19 | Port detection utilities |
| `cookbookProgressSignal.js` | 29 | Progress signal computation |
| `cookbookSchedule.js` | 386 | Job scheduling configuration |
| **Total** | **~16,851** | |

This is an **XL** subsystem comparable in size to the entire Chat domain.

---

### Consolidated Gap Summary Table

| Gap ID | Category | Effort | Blocks Which Tickets | In Any Ticket? |
|---|---|---|---|---|
| GAP-1 | Foundation Infrastructure | L (aggregate) | ALL | **No** |
| GAP-2 | Missing UI Primitives (19 items) | M (aggregate) | ALL domain tickets | **No** (ODY-26 covers only 7) |
| GAP-3 | Chat Pipeline Sub-Features | XL (aggregate) | ODY-36 | **No** (ODY-36 scope too narrow) |
| GAP-4 | Missing Domains (8 domains) | XL (aggregate) | None (standalone) | **No** |
| GAP-5 | Gallery/Image Editor | XL | ODY-29 | Partially (named but underestimated ~12x) |
| GAP-6 | Modal/Window Management | L | ODY-29,30,31 | **No** |
| GAP-7 | Sidebar/Icon Rail | M | ODY-25 | Partially (named but underestimated) |
| GAP-8 | Testing & CI Infrastructure | L | ALL | **No** |
| GAP-9 | Onboarding & Tour | S | None | **No** |
| GAP-10 | Utility Modules | S | Various | **No** |
| GAP-11 | Deep-Link Routes | S | ODY-25 | Partially |
| GAP-12 | Cookbook Domain | XL | ODY-29 | Partially (named but underestimated ~4x) |

---

### Dependency Graph of Gaps

```
GAP-1 (Foundation: i18n, theme, markdown, toast, shortcuts, storage)
  ├── Blocks: ALL domain tickets (ODY-28,29,30,31,36)
  └── Blocked by: ODY-25 (app shell) + ODY-26 (UI library)

GAP-2 (Missing UI Primitives)
  ├── Blocks: ALL domain tickets (everyone needs Tooltip, Toast, Table, etc.)
  └── Blocked by: ODY-26 (must extend component library)

GAP-6 (Modal/Window Management)
  ├── Blocks: ODY-29,30,31 (all tool-modal domains)
  └── Blocked by: ODY-25 (app shell)

GAP-3 (Chat Sub-Features)
  ├── Blocks: ODY-36 (Chat Domain cannot be "done" without these)
  └── Blocked by: ODY-25, ODY-26, ODY-27, GAP-1

GAP-8 (Testing Infrastructure)
  ├── Blocks: ALL domain tickets (ADR-0004 requires tests)
  └── Blocked by: ODY-25
```

---