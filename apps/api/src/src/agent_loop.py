"""agent_loop.py — Backward-compatible re-export shim for the decomposed agent loop.

The production implementation has moved to the ``src.agent`` sub-package:

  - src.agent.loop       — ``stream_agent_loop`` orchestrator
  - src.agent.classifier — intent classification and request analysis
  - src.agent.context    — context-window utilities and final metrics
  - src.agent.runaway    — runaway-loop detection
  - src.agent.verifier   — tool-block resolution and completion verification
  - src.agent.prompt     — system-prompt assembly

This module keeps the large prompt constants (``TOOL_SECTIONS``,
``_AGENT_PREAMBLE``, ``_AGENT_RULES``, etc.) and the prompt builders
(``_build_base_prompt``, ``_assemble_prompt``) so that ``src.agent.prompt``
can import them without a circular dependency.  Moving those constants into
``src.agent.prompt`` is scheduled for P2.2.

All other original names remain importable from ``src.agent_loop`` for
backward compatibility.
"""

import logging

from src.settings import get_setting
from src.tool_policy import WEB_TOOL_NAMES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base prompt text (active versions)
# ---------------------------------------------------------------------------

_AGENT_PREAMBLE = """\
You are an AI assistant with tool access. Only the tools listed below are available for this turn.
To use a tool, write a fenced code block with the tool name as the language tag. The block executes automatically and you see the output."""

_AGENT_RULES = """\
## Base rules
- Only use tools when needed. For casual messages like "test", "yo", "thanks", answer normally.
- If a needed tool/domain is missing from this turn, say what is missing briefly instead of pretending.
- After a tool succeeds, do not second-guess it; reply with one short confirmation unless more work remains.
- After a tool fails, retry with a concrete fix or state what is blocking you.
- Finish only when the user's concrete request is actually done, or clearly state that you are blocked.
- User identity facts/preferences ("my name is X", "call me X", "I live in X") use `manage_memory`, not contacts.
"""

_API_AGENT_RULES = """\
## Base rules
- Prefer native tool/function calling when tools are needed.
- Only call tools when they materially help answer the request. For casual messages like "test", "yo", "thanks", answer normally.
- You MUST use tools to take action; do not claim you did something without a tool result.
- If a needed tool/domain is missing from this turn, say what is missing briefly instead of pretending.
- Keep answers concise unless the user asks for depth.
- After a tool succeeds, do not second-guess it; reply with one short confirmation unless more work remains.
- After a tool fails, retry with a concrete fix or state what is blocking you.
- Finish only when the user's concrete request is actually done, or clearly state that you are blocked.
- User identity facts/preferences ("my name is X", "call me X", "I live in X") use `manage_memory`, not contacts.
"""

_LINK_RULES = """\
## Link conventions
When referencing app entities by id, use clickable markdown anchors:
- Sessions: `[Name](#session-<id>)`
- Documents: `[Title](#document-<id>)`
- Notes: `[Title](#note-<id>)`
- Emails: `[Subject](#email-<uid>)`
- Calendar events: `[Summary](#event-<uid>)`
- Tasks: `[Task name](#task-<id>)`
- Skills: `[skill-name](#skill-<name>)`
- Research jobs: `[Topic](#research-<session_id>)`
"""

_DOMAIN_RULES = {
    "web": """\
## Web rules
- For web lookup/search/latest/current requests, use `web_search` or `web_fetch`.
- Do not use shell, Python, curl, requests, or scraping code for web lookup unless web tools are unavailable or already failed.
- "Research X" means `trigger_research`, not a one-off `web_search`, unless the user explicitly asks for a quick lookup.""",
    "documents": """\
## Document rules
- For long code/content (>15 lines), use `create_document` instead of pasting into chat.
- If an active document is open, "fix this", "add X", "change Y", etc. usually refers to that document.
- Use `edit_document` for targeted changes. Use `update_document` only for genuine full rewrites.
- For feedback/review/suggestions on an open document, use `suggest_document`.""",
    "email": """\
## Email rules
- Email UIDs are the values after `UID:` in tool output, never list row numbers.
- For latest/newest email, list with `max_results: 1`, `unread_only: false`, then read the returned UID if needed.
- For named mailboxes/accounts, call `list_email_accounts` if needed and pass the exact `account` value.
- Bulk email actions use `bulk_email` once with explicit UIDs; do not loop one message at a time.
- "Write/draft a reply saying X" means open a pre-filled draft via `ui_control open_email_reply ... <body>` / structured `body`; only `reply_to_email` when the user clearly wants to send now.""",
    "cookbook": """\
## Cookbook/model-serving rules
- Cookbook is the LLM-serving subsystem.
- "What's running/serving" starts with `list_served_models`. "What's downloading" uses `list_downloads`.
- Launch known models by checking `list_serve_presets` before raw `serve_model`.
- Downloads/serves run on a Cookbook server; pass the named `host` when the user names one.
- Do not launch model servers manually with bash/ssh/tmux. Use `serve_model`/`serve_preset` so the UI can track and stop them.
- After a successful serve, verify with `list_served_models`; if an external server is running but invisible, use `adopt_served_model`.""",
    "notes_calendar_tasks": """\
## Notes/calendar/tasks rules
- Notes/todos/reminders use `manage_notes`, not memory.
- Calendar create/update/delete should call `manage_calendar` with `action=list_calendars` first.
- Recurring/automatic/scheduled requests create a `manage_tasks` task; do not just perform the action once.""",
    "ui": """\
## UI rules
- "Open/show <panel>" uses `ui_control open_panel <name>`.
- Tool toggles like "turn off shell/search/research" use `ui_control toggle <name> <on|off>`, not memory.""",
    "sessions": """\
## Chat/session rules
- Odysseus chats are sessions. Use `list_sessions`/`manage_session`; do not shell out looking for chat files.
- Preserve clickable session links from tool output in your final answer.""",
    "files": """\
## File rules
- Use file tools for real disk files. Use document tools only for editor documents.
- Prefer `grep`, `glob`, and `ls` over shell equivalents when available.
- Use `edit_file`/`write_file` for writes; avoid shell redirection/heredocs for editing files.""",
    "settings": """\
## Settings/API rules
- Use `manage_settings` for preferences and tool enable/disable.
- Use named tools over `app_api` when a named wrapper exists.
- `app_api` is only for safe UI/API actions without a named tool; do not use it for shell, package installs, engine rebuilds, or sensitive auth/admin paths.""",
    "contacts": """\
## Contacts rules
- Use `resolve_contact` to look up a contact's email or phone number by name. Searches the CardDAV address book and sent email history.
- Use `manage_contact` to list, add, update, or delete contacts in the address book.
- Do NOT use `manage_memory` for contact lookups — contact details live in the address book, not memory.""",
    "integrations": """\
## Integration/API rules
- To query or control a configured service integration (Home Assistant, Miniflux, Gitea, Linkding, Jellyfin, or any other registered service), use `api_call` with the integration name, HTTP method, path, and optional JSON body.
- Do not use shell, curl, or `app_api` to reach a user's connected integration when `api_call` is available.""",
}

_DOMAIN_TOOL_MAP = {
    "web": set(WEB_TOOL_NAMES),
    "documents": {"create_document", "edit_document", "update_document", "suggest_document", "manage_documents"},
    "email": {"list_email_accounts", "list_emails", "read_email", "send_email", "reply_to_email", "bulk_email", "archive_email", "delete_email", "mark_email_read", "resolve_contact", "manage_contact"},
    "cookbook": {"download_model", "serve_model", "serve_preset", "list_serve_presets", "list_served_models", "stop_served_model", "tail_serve_output", "list_downloads", "cancel_download", "search_hf_models", "list_cached_models", "list_cookbook_servers", "adopt_served_model"},
    "notes_calendar_tasks": {"manage_notes", "manage_calendar", "manage_tasks"},
    "ui": {"ui_control"},
    "sessions": {"create_session", "list_sessions", "manage_session", "send_to_session", "search_chats"},
    "files": {"bash", "python", "read_file", "write_file", "edit_file", "grep", "glob", "ls", "get_workspace", "manage_bg_jobs"},
    "settings": {"manage_settings", "manage_endpoints", "manage_mcp", "manage_webhooks", "manage_tokens", "app_api"},
    "contacts": {"resolve_contact", "manage_contact"},
    "integrations": {"api_call"},
}


def _domain_rules_for_tools(tool_names: set) -> list[str]:
    names = set(tool_names or set())
    rules = []
    for domain, domain_tools in _DOMAIN_TOOL_MAP.items():
        if names & domain_tools:
            rules.append(_DOMAIN_RULES[domain])
    if names & {"create_session", "list_sessions", "manage_session", "manage_documents", "manage_notes", "manage_calendar", "manage_tasks", "manage_skills", "manage_research"}:
        rules.append(_LINK_RULES)
    return rules


# ---------------------------------------------------------------------------
# Tool sections
# ---------------------------------------------------------------------------

TOOL_SECTIONS = {
    "bash": """\
```bash
<shell command>
```
Run any shell command. Output is returned to you. Use for: installing packages, checking files, git, system info, process management, etc.
Do NOT use bash/curl for web lookup/search/latest/current requests when `web_search` or `web_fetch` is available.
NEVER use bash to create or change files — no `>`/`>>` redirects, no heredocs (`cat > f << 'EOF'`), no `tee`, `sed -i`, `awk -i`, no `python -c` that writes. To CREATE or fully rewrite a file use `write_file`; to change part of an existing file use `edit_file`. Those show a diff and are the ONLY allowed way to write files. (bash is for read-only inspection: `ls`, `cat` to READ, `grep`, `git status`/`git diff`, builds, installs.)
For LONG-running commands (package installs, pip/npm, ffmpeg, model downloads, training, builds — anything that may take more than ~20s), make the FIRST line `#!bg` to run it in the BACKGROUND. You get a job id back immediately and you are automatically re-invoked with the full output when it finishes — so you never block the chat waiting. Example:
```bash
#!bg
pip install openai-whisper
```
SANDBOX LIMITS: stdin/stdout are pipes, so there is NO interactive terminal — `input()`, `curses`, `termios`, `pygame`, and `tkinter` will all fail. Don't try to RUN interactive terminal games or GUI apps here — verify syntax (`python -c "import py_compile; py_compile.compile('x.py')"`) and tell the user to run it themselves in their own terminal. For anything the USER should play/use interactively (games, UIs, demos), prefer a single self-contained HTML file with `<canvas>` + inline JS — save it via `create_document` with language="html" and tell the user to hit the Run / Preview button (▶) in the document editor toolbar; it renders inline in a sandboxed iframe so the game is playable right there. Works from any machine that can reach the Odysseus UI — no need to copy files out.
NEVER pipe multi-line Python through `python -c "..."` — shell quoting eats real newlines and `\\n` arrives as literal backslash-n, which Python parses as a line-continuation error on line 1. To run multi-line code, either use the dedicated `python` tool block above, or save to a file first with a quoted HEREDOC (`cat > /tmp/x.py << 'EOF' ... EOF`) and then `python /tmp/x.py`.""",

    "python": """\
```python
<python code>
```
Execute Python code. Use for computation, data processing, scripting. NOT for writing code for the user (use create_document for that). Same sandbox limits as bash — no TTY, no GUI, no `input()`; for anything the user should interact with, generate a single HTML file with inline JS instead.
Prefer a dedicated tool whenever one fits the job (reading, searching, or writing files); use python only for computation/processing no dedicated tool covers - not for reading or writing files.
Do NOT use Python/requests for web lookup/search/latest/current requests when `web_search` or `web_fetch` is available.""",

    "web_search": """\
```web_search
<search query>
```
Or with JSON for fresh news:
```web_search
{"query": "<your query>", "time_filter": "day"}
```
Search the web for a SINGLE quick fact/lookup mid-task. For news / "today" / "latest" queries, pass `time_filter` ("day", "week", "month", or "year"). NOT for "research X" / "do research on X" / "look into X" requests — those mean a multi-source DEEP RESEARCH job: use `trigger_research` instead (it runs in the Deep Research sidebar and produces a full report). web_search = one quick query; trigger_research = a researched report.
If this `web_search` tool section is visible, search is available. Do NOT tell the user web/search tools are unavailable.
Use this instead of `bash`, `curl`, `python`, `requests`, or scraping code for web lookup/search/latest/current requests.""",

    "web_fetch": """\
```web_fetch
<url or domain>
```
Fetch and read the text content of a SPECIFIC URL the user names (e.g. "check example.com", "what does this page say <url>"). A bare domain like `example.com` works (defaults to https). Use this when you already have a concrete URL. For open-ended lookups use `web_search`, and for "research X" jobs use `trigger_research`.""",

    "read_file": """\
```read_file
<file path>
```
Read a file and return its contents.""",

    "write_file": """\
```write_file
<file path>
<file contents>
```
Write content to a file. First line is the path, rest is the content.""",

    "edit_file": """\
```edit_file
{"path": "<file path>", "old_string": "<exact text to replace>", "new_string": "<replacement>", "replace_all": false}
```
Edit an EXISTING file by exact string replacement. PREFER this over bash (sed/echo/redirects) for changing files — it shows a before/after diff. `old_string` must match the file exactly and be unique unless `replace_all` is true. Use write_file to create a file.""",

    "get_workspace": """\
```get_workspace
```
Return the absolute path of the active workspace folder. File tools are CONFINED to it (paths can be RELATIVE to it); the shell starts there (cwd) but is NOT sandboxed. Call this first when the user says "the project"/"the code"/"this folder" without a path, instead of asking them. No arguments.""",

    "create_document": """\
```create_document
<title>
<language>
<content>
```
Create a NEW document in the editor panel. Only use when the user explicitly asks for a new file/document. If a document is already open in the editor, the user's request "fix this", "add X", "change Y", etc. refers to THAT document — use edit_document, never create_document.""",

    "edit_document": """\
```edit_document
<<<FIND>>>
old text to find
<<<REPLACE>>>
new replacement text
<<<END>>>
```
Edit a document OPEN IN THE EDITOR PANEL — NOT a file on disk. For files on disk (home folder, project files, any real path like ~/sweden.txt) use `edit_file` instead. Find exact text and replace. Multiple FIND/REPLACE blocks per call OK. Use for any edit smaller than a full rewrite. **If a document is open in the editor, treat it as the user's current context: don't ask which file they mean, and don't create a new one — just edit_document the active one.** Do NOT re-send the whole file with update_document for small changes.""",

    "update_document": """\
```update_document
<entire new content>
```
Replace the ENTIRE active document. ONLY use when you're genuinely rewriting more than half of it from scratch. For any smaller change, use edit_document — echoing back the whole file for a two-line edit wastes tokens and is hard to review.""",

    "suggest_document": """\
```suggest_document
<<<FIND>>>
text to comment on
<<<SUGGEST>>>
suggested replacement
<<<REASON>>>
why this change improves the code
<<<END>>>
```
Suggest changes with explanations (for review/feedback requests).""",

    "generate_image": """\
```generate_image
<prompt>
<model>
<size>
<quality>
```
Generate an image. Line 1 = description, line 2 = model name, line 3 = WxH (e.g. 1024x1024), line 4 = quality.""",

    "chat_with_model": "- ```chat_with_model``` — Ask a DIFFERENT AI model and relay its answer. Line 1 = model name (or 'model@endpoint'), rest = your message. Use when the user says 'ask <model>', 'what does <model> think', or wants to compare/their answer from another model.",
    "ask_teacher": "- ```ask_teacher``` — Escalate a hard question to a more capable model. Line 1 = model name or 'auto', rest = the question. Use when stuck or need expert knowledge.",
    "list_models": "- ```list_models``` — Show all available AI models across all endpoints. Use when user asks what models are available.",
    "manage_session": "- ```manage_session``` — Rename, archive, delete, fork, switch, or `list` chats (the UI calls them 'chats'; 'session' is internal). Line 1 = action (list/switch/rename/archive/unarchive/delete/important/unimportant/truncate/fork), Line 2 = exact chat id from `list_sessions` (or `current` where supported). For delete/archive/truncate, always list first and reuse the exact id; never invent placeholder ids. `switch`/`open` returns a clickable anchor link the user can tap to open the chat — use for \"open my X chat\".",
    "manage_memory": "- ```manage_memory``` — Manage the user's persistent memory (facts about the USER themselves, their preferences, context that persists across chats). Line 1 = action (list/add/edit/delete/search), rest = content. Use when user says 'remember this' about themselves, states identity facts like 'my name is <name>' / 'call me <name>' / 'I live in <place>', or asks about stored memories. DO NOT use for info about another person (their address, phone, email, birthday) — that goes in `manage_contact`. If the user pastes an address/phone with a name and says 'save this for <person>', use `manage_contact add` with the address arg, NOT manage_memory.",
    "manage_skills": "- ```manage_skills``` — Skill registry (SKILL.md format). Args (JSON): {\"action\": \"list|view|view_ref|search|add|edit|patch|publish|delete\", ...}. `list` returns the index of available skills (published + teacher-escalation drafts); `view name=foo` fetches the full SKILL.md; `view_ref name=foo path=...` loads a reference file under the skill directory. For `add`, provide an explicit kebab-case `name` and only report the exact returned name, because storage may normalize or dedupe it. Use this BEFORE doing domain work — there may already be a procedure (published or draft) that prescribes the correct steps. Drafts written by the teacher loop are authoritative guidance even though they're not yet published.",
    "manage_tasks": "- ```manage_tasks``` — Create and manage scheduled background tasks (recurring AI jobs). Args (JSON): {\"action\": \"list|create|edit|delete|pause|resume|run\", ...}",
    "manage_endpoints": "- ```manage_endpoints``` — Add, remove, or configure AI model API endpoints. Args (JSON): {\"action\": \"list|add|delete|enable|disable\", ...}. Use when user wants to add a new AI provider.",
    "manage_mcp": "- ```manage_mcp``` — Manage MCP (Model Context Protocol) tool servers — external tools that extend your capabilities. Args (JSON): {\"action\": \"list|add|delete|reconnect|list_tools\", ...}",
    "manage_webhooks": "- ```manage_webhooks``` — Configure outgoing webhooks (HTTP notifications on events like chat completion). Args (JSON): {\"action\": \"list|add|delete|enable|disable\", ...}",
    "manage_tokens": "- ```manage_tokens``` — Generate or revoke API access tokens for external integrations. Args (JSON): {\"action\": \"list|create|delete\", ...}",
    "manage_documents": "- ```manage_documents``` — List, read/open, delete, or tidy documents in the editor panel. Args (JSON): {\"action\": \"list|read|delete|tidy\", ...}. `list` returns rows like `[Title](#document-<id>) — lang, size, updated 5m ago` sorted MOST-RECENT FIRST; the user clicks the anchor to open. `read` (aliases: view/open/get) takes `document_id` and returns the content.",
    "manage_research": "- ```manage_research``` — List, read/open, or delete saved DEEP RESEARCH results from the Library. Args (JSON): {\"action\": \"list|read|delete\", \"id\": \"<id>\", \"search\": \"...\"}. `list` returns rows like `[query](#research-<id>) — N sources` MOST-RECENT FIRST; the user clicks to open. Use when the user says \"open/read/find/delete my research\" or \"that report\". This IS how you read a finished report: when the user refers to a just-completed deep-research job (\"check it out\", \"read that report\", \"summarize the research\") WITHOUT giving an id, call `manage_research` with `action:list` to get the most-recent id, then `action:read` with that id, and answer from the returned text. Do NOT `web_fetch`/`app_api` the `/api/research/report/{id}` URL — that endpoint renders HTML for the browser, not clean text — and do NOT start a fresh `web_search`/`trigger_research` just to read an existing report. To START new research, use trigger_research instead.",
    "manage_settings": "- ```manage_settings``` — View/change the REAL app settings (same ones the Settings panel writes) AND turn tools on/off. Change a setting: `{\"action\":\"set\",\"key\":\"...\",\"value\":\"...\"}` — keys accept friendly aliases, e.g. voice→tts_voice, \"search engine\"→search_provider, \"default model\"→default_model, \"teacher model\"→teacher_model, \"task/background model\"→task_model, \"image quality\"→image_quality, \"reminder channel\"→reminder_channel (browser|email|ntfy), \"agent timeout\"/\"max tool calls\"/\"token budget\". Read: `{\"action\":\"get\",\"key\":\"...\"}`; see all: `{\"action\":\"list\"}`; reset one: `{\"action\":\"reset\",\"key\":\"...\"}`. Use this when the user asks to change ANY preference instead of making them open Settings. Secrets/API keys are read-only (tell them to set those in the panel). Tool toggles: `{\"action\":\"disable_tool|enable_tool\",\"tool\":\"shell\"}` (aliases: shell/search/browser/documents/memory/skills/images/tasks/notes/calendar/email), list disabled: `{\"action\":\"list_tools\"}`.",
    "manage_notes": """\
```manage_notes
{"action": "add", "title": "<short todo>", "due_date": "<natural language or ISO datetime>"}
```
Notes, checklists, AND user reminders. Use this for "create/add/write a note", todos, checklists, and "remind me to X at <time>" — never use memory for note content. For reminders, pair a short `title` (what to do) with a `due_date` (when). `due_date` accepts natural language ("tomorrow at 1pm", "in 2 hours", "next monday 9am") or ISO ("2026-05-12T13:00:00"). Actions: `list`, `add` (title, content OR items:[{text,done}], note_type, color, label, due_date), `update`, `delete`, `toggle_item`.""",
    "list_email_accounts": "- ```list_email_accounts``` — List configured email accounts. Use this before reading/sending when the user says Gmail, work mail, custom domain mail, or any non-default mailbox; pass the returned account name/email/id as `account` to email tools.",
    "send_email": """\
```send_email
{"to": "recipient@example.com", "subject": "Re: Your question", "body": "Hi, ...", "account": "gmail"}
```
Send a new email via SMTP. Use `resolve_contact` first if you only have a name. If multiple email accounts exist, call `list_email_accounts` first and pass the chosen `account`.

CRITICAL — signatures: DO NOT invent a sign-off name. End the body with just `Thanks,` or similar — never type a person's name unless the user explicitly told you what to sign as. When `agent_email_confirm` is on (default), the tool returns `{pending: true, pending_id: ...}` and stages the email for the user to approve in the chat UI instead of SMTPing immediately.""",
    "bulk_email": """\
```bulk_email
{"action": "delete", "uids": ["10997", "10998"], "folder": "INBOX", "account": "Gmail"}
```
Bulk delete/archive/mark emails. Use this for "delete all those" after listing emails. Pass the exact UIDs and the same account from the list result, then report only the tool result.""",
    "delete_email": "- ```delete_email``` — Delete one email by UID. Args (JSON): {\"uid\":\"...\", \"folder\":\"INBOX\", \"account\":\"Gmail\"}. For multiple messages use bulk_email.",
    "archive_email": "- ```archive_email``` — Archive one email by UID. Args (JSON): {\"uid\":\"...\", \"folder\":\"INBOX\", \"account\":\"Gmail\"}. For multiple messages use bulk_email.",
    "mark_email_read": "- ```mark_email_read``` — Mark one email read/unread. Args (JSON): {\"uid\":\"...\", \"read\":true, \"folder\":\"INBOX\", \"account\":\"Gmail\"}. For multiple messages use bulk_email.",
    "resolve_contact": "- ```resolve_contact``` — Look up a contact's email by name. Searches CardDAV address book + sent email history. Args (JSON): {\"name\": \"...\"}. Use BEFORE send_email when the user gives only a name.",
    "manage_contact": "- ```manage_contact``` — Create/update/delete/list CardDAV contacts. Args (JSON): {\"action\": \"list|add|update|delete\", \"name\": \"...\", \"email\": \"...\", \"phones\": [...], \"address\": \"...\", \"uid\": \"...\"}. Use for info about another person: email, phone, postal address. For 'save this for <person>' / address paste / phone next to a name, use this — NOT manage_memory. Do NOT use for user identity facts ('my name is X'); those are manage_memory. For update/delete, call action=list first for the uid.",
    "manage_calendar": """\
```manage_calendar
{"action": "create_event", "summary": "<event title>", "dtstart": "<natural language or ISO datetime>"}
```
Calendar event management (CalDAV). Actions: `list_events`, `create_event`, `update_event`, `delete_event`, `list_calendars`. \
For `list_events`: {action: "list_events", start: "YYYY-MM-DDT00:00:00", end: "YYYY-MM-DDT00:00:00", calendar?}; resolve month/week phrases yourself from the Current date and time context and do not pass a loose `query` field. Prefer `start`/`end`; start_time/end_time, start_date/end_date, and from/to aliases are accepted. \
For `create_event`: {summary, dtstart, dtend?, duration?, calendar?, location?, description?, reminder_minutes?, rrule?}. \
For `update_event`: {uid, summary?, dtstart?, dtend?, all_day?, location?, description?, event_type?, importance?, rrule?}. Pass `rrule: ""` to remove recurrence and make a repeating event a single event. \
`dtstart` accepts natural language ("tomorrow at 1pm", "in 2 hours", "next monday 9am") or ISO ("2026-05-12T13:00:00"). \
If `dtend` omitted, defaults to dtstart+1h (or +1d when `all_day: true`). \
For a RECURRING event pass `rrule` as an iCalendar RRULE string, e.g. `"FREQ=WEEKLY;BYDAY=MO"` (every Monday), `"FREQ=DAILY;COUNT=10"`, or `"FREQ=MONTHLY;BYMONTHDAY=1"` — create ONE event with the rrule, do not loop creating many events. Do not pass `rrule` for "next Wednesday only", "just this once", or any single occurrence. \
If the user asks for a reminder/alarm before the event, pass `reminder_minutes` as an integer; do not write reminder text into the event description and do NOT also call `manage_notes` for the same reminder because calendar reminders are routed through Notes automatically. \
`calendar` accepts a name ("Main") or short-id prefix.""",
    "create_session": "- ```create_session``` — Create a new chat. Line 1 = chat name, Line 2 = model name. Use for background/parallel work.",
    "list_sessions": "- ```list_sessions``` — List chats sorted MOST-RECENT FIRST (the UI calls them 'chats') with clickable chat-title links. Output includes a relative \"last active\" timestamp per row, so the first row is the user's most recent chat. Content = optional filter keyword (matches chat name). When answering, preserve the `[title](#session-id)` links exactly; do not convert them into plain text.",
    "send_to_session": "- ```send_to_session``` — Send a message to another session. Line 1 = session_id, rest = message. Use for orchestrating work across sessions.",
    "search_chats": "- ```search_chats``` — Search past session transcripts for direct conversation evidence. Use when user asks 'did we discuss X?', 'find the conversation about Y', or when prior chat context is more appropriate than persistent memory.",
    "pipeline": "- ```pipeline``` — Run a multi-step AI pipeline. Args (JSON) with ordered steps, each specifying a model and prompt. Use for complex workflows.",
    "ui_control": "- ```ui_control``` — Control the UI: toggle tools on/off, OPEN PANELS, open email reply drafts, switch models, change themes. Commands: `toggle <name> on/off` (names: bash/shell, web/search, research, incognito, document_editor/documents), `open_panel <name>` (panels: documents, gallery, email, sessions, notes, memories/brain, skills, settings, cookbook), `open_email_reply <uid> <folder> <reply|reply-all|ai-reply> <body text>` (opens an email compose document pre-filled with body, DOES NOT send; use this for normal “write/draft a reply saying X” requests), `set_mode agent/chat`, `switch_model <name>`, `set_theme <preset>`, `create_theme <name> <bg> <fg> <panel> <border> <accent>` (optional key=val for advanced colors AND background effects: bgPattern=<none|dots|synapse|rain|constellations|perlin-flow|petals|sparkles|embers>, bgEffectColor=#RRGGBB, bgEffectIntensity=<num>, bgEffectSize=<num>, frosted=true|false). \"open documents\" / \"open library\" / \"show gallery\" / \"open inbox\" / \"open notes\" / \"open cookbook\" all map to `open_panel <name>`. Built-in theme presets: dark, light, midnight, paper, cyberpunk, retrowave, forest, ocean, ume, copper, terminal, organs, lavender, gpt, claude, cute. For any other vibe/name, use create_theme.",
    "ask_user": "- ```ask_user``` — Ask the user a multiple-choice question when the task is genuinely ambiguous and the answer changes what you do next (pick an approach, confirm an assumption, choose a target). Args (JSON): {\"question\": \"...\", \"options\": [{\"label\": \"...\", \"description\": \"...\"?}, ...], \"multi\": false?}. 2-6 options. The user gets clickable buttons; calling this ENDS your turn and their choice comes back as your next message. Prefer sensible defaults — only ask when you truly can't proceed well without their input.",
    "update_plan": "- ```update_plan``` — While executing an approved plan, write the plan back: tick steps done or revise them. Args (JSON): {\"plan\": \"- [x] done step\\n- [ ] next step\"}. Always pass the COMPLETE checklist, not a diff. Call it after finishing each step (mark it `- [x]`) and whenever the user asks to change the plan. The user's docked plan window updates live. Does nothing if there's no active plan.",
    "list_served_models": "- ```list_served_models``` — Show what the Cookbook (LLM-serving subsystem) is currently running. NO args. Use this for ANY 'what's running' / 'what's serving' / 'show my cookbook' / 'is anything up' query. DO NOT shell out (`ps aux`, `docker ps`, etc.) — this tool is the source of truth. Failed serve tasks include recent logs plus diagnosis/retry suggestions; use those suggestions to call `serve_model` again with an adjusted command when appropriate.",
    "stop_served_model": "- ```stop_served_model``` — Stop a running model server. Args (JSON): {\"session_id\": \"<from list_served_models>\"}. Use for 'kill my cookbook' / 'stop the model' / 'shut down vLLM'.",
    "tail_serve_output": "- ```tail_serve_output``` — Read the actual tmux stderr/traceback of a CURRENTLY failing cookbook task. Args (JSON): {\"session_id\": \"<from list_served_models>\", \"tail\": 150?}. **Use ONLY after** you just launched something via `serve_model` AND `list_served_models` reports YOUR new task as `crashed`/`error`. DO NOT use it on old stopped/completed download tasks (they're historical noise — won't predict whether a new launch succeeds). DO NOT call it before launching a fresh attempt. When you do call it, bump `tail` to 400+ only if the visible error references 'see root cause above'.",
    "download_model": "- ```download_model``` — Download a HuggingFace model. Args (JSON): {\"repo_id\": \"Qwen/Qwen3-8B\", \"host\": \"user@gpu-box\"?, \"include\": \"*Q4_K_M*\"?}.",
    "serve_model": "- ```serve_model``` — Start serving a model with vLLM / SGLang / llama.cpp / Ollama / Diffusers. Args (JSON): {\"repo_id\": \"...\", \"cmd\": \"vllm serve ... --port 8000\" or \"python3 -m sglang.launch_server ... --port 30000\" or \"python3 scripts/diffusion_server.py --model diffusers/stable-diffusion-xl-1.0-inpainting-0.1 --port 8100\", \"host\": \"user@gpu-box\"?}. For image/inpaint/diffusion models, use the `scripts/diffusion_server.py` command exactly. After launch, call `list_served_models`; if it returns a diagnosis with an adjusted command, retry with that command.",
    "list_downloads": "- ```list_downloads``` — Show in-progress HuggingFace model downloads (filters Cookbook tasks/status to downloads only). NO args. Use for 'what's downloading' / 'show my downloads' / 'check download progress'.",
    "cancel_download": "- ```cancel_download``` — Cancel an in-progress download. Args (JSON): {\"session_id\": \"<from list_downloads>\"}. Use for 'cancel the download' / 'kill the download'.",
    "search_hf_models": "- ```search_hf_models``` — Search HuggingFace for models. Args (JSON): {\"query\": \"qwen 8b\", \"limit\": 10?}. Use for 'find a model for X' / 'search huggingface' / 'what models are there for Y'.",
    "list_cached_models": "- ```list_cached_models``` — List models already on disk. Args (JSON, all optional): {\"host\": \"ajax or user@gpu-box\"?, \"model_dir\": \"/data/models,/extra\"?}. Friendly Cookbook server names work. Use for 'what models do I have' / 'show cached models' / 'is X downloaded'.",
    "app_api": """\
```app_api
{"action": "call", "method": "GET", "path": "/api/cookbook/gpus"}
```
GENERIC LOOPBACK to allowed Odysseus internal endpoints. Use this whenever the user wants something the UI can do but there's NO named tool for it. Many UI buttons hit /api/* endpoints — you can hit allowed ones. Auth is handled automatically.

**Discovery first.** If you're not sure of the path, call `{"action":"endpoints","filter":"<keyword>"}` (e.g. filter='calendar' or 'gallery' or 'theme') to list available endpoints with their methods + summaries. Then call with action='call'.

**Common surfaces (use `endpoints` with filter to discover the full set per domain):**
- Calendar: `/api/calendar/events`, `/api/calendar/calendars`, `/api/calendar/events/{uid}`
- Cookbook: `/api/cookbook/gpus`, `/api/cookbook/state`, `/api/cookbook/setup`, `/api/cookbook/packages`, `/api/cookbook/hf-latest`, `/api/model/cached`. Do NOT use `app_api` for package installs, engine rebuilds, or PID signalling.
- Gallery: `/api/gallery/list`, `/api/gallery/delete`, `/api/gallery/{id}`, `/api/gallery/albums`
- Library / Documents: list all via `/api/documents/library`; docs in a session via `/api/documents/{session_id}`; a single doc via `/api/document/{id}` (singular) and its history via `/api/document/{id}/versions` (singular). Note the plural `/api/documents/...` vs singular `/api/document/{id}` split.
- Memory: `/api/memory`, `/api/memory/{id}`, `/api/memory/search`
- Notes: `/api/notes`, `/api/notes/{id}`
- Tasks: `/api/tasks`, `/api/tasks/{id}/run`, `/api/tasks/notifications`
- Sessions: `/api/sessions`, `/api/session/{id}`, `/api/session/{id}/truncate`
- Themes: `/api/prefs/themes`, `/api/prefs/custom-themes`
- Settings: `/api/settings`, `/api/prefs/{key}`
- Research: `/api/research/start`, `/api/research/tasks` (note: `/api/research/report/{id}` renders HTML — to READ a report's text use the `manage_research` tool with `action:read`, not this endpoint)
- Compare: `/api/compare/sessions`, `/api/compare/start`
- Email: use named email tools (`list_email_accounts`, `list_emails`, `read_email`, `send_email`, `reply_to_email`). Do NOT use `/api/email/accounts`; it is owner-filtered in tool context and may falsely return empty.
- Endpoints (model providers): `/api/endpoints`, `/api/endpoints/{id}`
- Shell: do NOT use `app_api` for `/api/shell/*`; use named command tooling instead.

Body for POST/PUT/PATCH goes in `body` (object). Query params in `query` (object). Returns the parsed JSON of the response.

**When to prefer named tools over app_api:** if a named wrapper exists (list_email_accounts, list_emails, read_email, manage_calendar, manage_notes, list_served_models, etc.) USE IT — it has nicer output formatting and clearer schema. Reach for `app_api` only when there's no wrapper for what you need.

Blocked paths/routes (refused for safety): /api/auth/, /api/users/, /api/tokens/, /api/admin/, /api/shell/, /api/backup/restore, POST /api/cookbook/packages/install, POST /api/cookbook/rebuild-engine, POST /api/cookbook/kill-pid.""",
}


def get_builtin_overrides() -> dict:
    """User overrides for built-in tool descriptions (TOOL_SECTIONS).

    Stored globally in settings.json so the user can preview + edit how
    the assistant is told to use a native tool, with a revert path.
    """
    try:
        ov = get_setting("builtin_tool_overrides", {})
        return ov if isinstance(ov, dict) else {}
    except Exception as e:
        logger.warning("Failed to load builtin tool overrides, using defaults", exc_info=e)
        return {}


def _section_text(name: str, default: str) -> str:
    """Effective TOOL_SECTIONS text for a tool — user override if set, else default."""
    ov = get_builtin_overrides()
    val = ov.get(name)
    return val if isinstance(val, str) and val.strip() else default


def _compact_tool_line(name: str, section: str) -> str:
    """One-line fenced-tool usage hint for compact/local prompts."""
    text = (section or "").strip()
    if not text:
        return f"- `{name}`"
    if text.startswith("- "):
        return text
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    usage = []
    in_fence = False
    for ln in lines:
        if ln.startswith("```"):
            usage.append(ln)
            in_fence = not in_fence
            if len(usage) >= 3:
                break
            continue
        if in_fence and len(usage) < 3:
            usage.append(ln)
    if usage:
        return f"- `{name}` — " + " ".join(usage)
    return f"- `{name}` — " + lines[0][:160]


def _assemble_prompt(tool_names: set, disabled_tools: set = None, compact: bool = False) -> str:
    """Build the system prompt with only the specified tools included."""
    disabled = disabled_tools or set()
    included = tool_names - disabled

    if compact:
        tool_lines = []
        for name, _default_section in TOOL_SECTIONS.items():
            if name in included:
                tool_lines.append(f"- `{name}`")
        parts = [
            "You are an AI assistant with native tool/function calling. "
            "Only the tool schemas provided by the API are available for this turn. "
            "Use native tool calls when action is needed; do not write tool syntax or tool instructions in chat.",
            "## Available tools\n" + ("\n".join(tool_lines) if tool_lines else "none"),
            _API_AGENT_RULES,
        ]
        parts.extend(_domain_rules_for_tools(included))
        return "\n\n".join(parts)

    parts = [_AGENT_PREAMBLE]

    full_blocks = []
    one_liners = []

    for name, _default_section in TOOL_SECTIONS.items():
        if name not in included:
            continue
        section = _section_text(name, _default_section)
        if section.startswith("```") or section.startswith("-"):
            if section.startswith("- "):
                one_liners.append(section)
            else:
                full_blocks.append(section)

    if full_blocks:
        parts.append("\n\n".join(full_blocks))

    if one_liners:
        parts.append("## Additional tools\n" + "\n".join(one_liners))

    parts.append(_AGENT_RULES)
    parts.extend(_domain_rules_for_tools(included))
    return "\n\n".join(parts)


# Legacy: full prompt with all tools (fallback when RAG unavailable)
AGENT_SYSTEM_PROMPT = _assemble_prompt(set(TOOL_SECTIONS.keys()))

_cached_base_prompt: str | None = None
_cached_base_prompt_key: tuple | None = None


# ---------------------------------------------------------------------------
# Runtime constants referenced by src.agent.loop
# ---------------------------------------------------------------------------

_API_HOSTS: frozenset[str] = frozenset([
    "api.openai.com", "api.anthropic.com",
    "openrouter.ai", "api.groq.com",
    "api.mistral.ai", "api.cohere.com",
    "api.deepseek.com", "deepseek.com",
    "api.together.xyz", "api.fireworks.ai",
    "api.perplexity.ai", "api.x.ai",
    "ollama.com", "api.venice.ai", "api.kimi.com",
    "api.githubcopilot.com",
])

_MCP_KEYWORDS: frozenset[str] = frozenset([
    "mcp", "browse", "browser", "website", "calendar", "event", "email",
    "gmail", "screenshot", "navigate", "click", "miniflux", "rss", "feed",
])

_ADMIN_SCHEMA_NAMES: frozenset[str] = frozenset([
    "manage_session", "manage_skills", "manage_tasks",
    "manage_endpoints", "manage_mcp", "manage_webhooks", "manage_tokens",
    "create_session", "list_sessions", "send_to_session", "pipeline",
    "ask_teacher", "list_models", "search_chats",
])

_TOOL_SELECTION_TIMEOUT_SECONDS: float = 1.5

_ADMIN_KEYWORDS = [
    "session", "sessions", "chat", "chats", "conversation", "conversations",
    "delete", "fork", "truncate",
    "archive", "rename", "endpoint", "endpoints", "api key",
    "webhook", "webhooks", "token", "tokens", "mcp", "server", "skill", "skills",
    "task", "tasks", "schedule", "cron", "setting", "settings", "preference",
    "configure", "config", "setup", "manage", "admin", "pipeline", "second opinion",
    "list models", "switch model", "change model", "theme", "create theme",
    "document", "documents", "doc", "docs", "library", "tidy",
    "note", "notes", "todo", "todos", "reminder", "reminders",
]

_ADMIN_TOOLS: set[str] = {
    "manage_session", "manage_skills", "manage_tasks",
    "manage_endpoints", "manage_mcp", "manage_webhooks", "manage_tokens",
    "manage_documents", "manage_settings", "create_session", "list_sessions",
    "send_to_session", "pipeline", "ask_teacher", "list_models",
}


# ---------------------------------------------------------------------------
# Prompt builders used by src.agent.prompt
# ---------------------------------------------------------------------------

def _build_base_prompt(
    disabled_tools,
    mcp_mgr,
    needs_admin,
    relevant_tools=None,
    mcp_disabled_map=None,
    compact: bool = False,
    owner: str | None = None,
    suppress_local_context: bool = False,
    suppress_skills: bool = False,
):
    """Build the agent prompt with only relevant tools included.

    If relevant_tools is provided (from RAG retrieval), only those tools
    are shown with full descriptions. Otherwise falls back to full prompt.
    """
    from src.tool_index import ALWAYS_AVAILABLE

    disabled = set(disabled_tools or [])
    if not get_setting("image_gen_enabled", False):
        disabled.add("generate_image")

    if relevant_tools is not None:
        tool_names = set(relevant_tools) | {"ask_user", "update_plan"}
        if needs_admin:
            tool_names |= _ADMIN_TOOLS
        agent_prompt = _assemble_prompt(tool_names, disabled, compact=compact)
    else:
        agent_prompt = AGENT_SYSTEM_PROMPT
        if not needs_admin:
            mgmt_tools = set(TOOL_SECTIONS.keys()) - set(ALWAYS_AVAILABLE) - {
                "generate_image", "suggest_document",
                "chat_with_model", "ask_teacher", "list_models",
            }
            agent_prompt = _assemble_prompt(
                set(TOOL_SECTIONS.keys()) - mgmt_tools, disabled, compact=compact
            )
        elif compact:
            agent_prompt = _assemble_prompt(set(TOOL_SECTIONS.keys()), disabled, compact=True)

    skill_index_block = ""
    if not suppress_local_context and not suppress_skills:
        try:
            from services.memory.skills import SkillsManager
            from src.constants import DATA_DIR
            _sm = SkillsManager(DATA_DIR)
            active_tools = list(set(TOOL_SECTIONS.keys()) - set(disabled or []))
            skill_idx = _sm.index_for(owner=owner, active_toolsets=active_tools)
            if skill_idx:
                lines = ["## Available skills",
                         "Procedures the assistant should consult before doing domain work. "
                         "Fetch the full procedure with `manage_skills` action=view name=<name> "
                         "when one looks relevant. Entries tagged `(draft)` were written by the "
                         "teacher-escalation loop after a prior failure — treat them as authoritative "
                         "guidance; if you follow one and it works, that's a good signal the procedure "
                         "is correct."]
                by_cat: dict[str, list] = {}
                for s in skill_idx:
                    by_cat.setdefault(s["category"], []).append(s)
                for cat in sorted(by_cat):
                    lines.append(f"\n**{cat}**")
                    for s in by_cat[cat]:
                        badge = " *(draft)*" if s.get("status") == "draft" else ""
                        lines.append(f"- `{s['name']}` — {s['description']}{badge}")
                skill_index_block = "\n\n" + "\n".join(lines)
        except Exception as _e:
            logger.debug(f"Skill-index injection skipped: {_e}")

    return agent_prompt, skill_index_block


def _compact_email_draft_context(
    raw: str, *, max_own_chars: int = 1200, max_history_chars: int = 1200
) -> str:
    """Compact an email compose document for prompt injection."""
    text = raw or ""
    if "\n---\n" not in text:
        return text[:3500] + ("\n...[truncated]" if len(text) > 3500 else "")
    header, body = text.split("\n---\n", 1)
    literal = "---------- Previous message ----------"
    idx = body.find(literal)
    if idx >= 0:
        own = body[:idx].strip()
        history = body[idx:].strip()
    else:
        own = body.strip()
        history = ""
    if len(own) > max_own_chars:
        own = own[:max_own_chars].rstrip() + "\n...[draft body truncated]"
    if len(history) > max_history_chars:
        history = history[:max_history_chars].rstrip() + "\n...[quoted history truncated; full history is preserved by Odysseus]"
    if history:
        body_out = (
            f"{own}\n\n" if own else ""
        ) + (
            "QUOTED HISTORY EXCERPT FOR CONTEXT ONLY -- do not rewrite or include this excerpt in your tool output; "
            "Odysseus preserves the full quoted thread below the reply automatically.\n"
            f"{history}"
        )
    else:
        body_out = own
    return header.rstrip() + "\n---\n" + body_out.strip()


# ---------------------------------------------------------------------------
# Backward-compatible re-exports from the decomposed src.agent package.
#
# Placed at the end so that src.agent.prompt can import the prompt builders
# above while this module is still being initialised.
# ---------------------------------------------------------------------------

from src.agent.classifier import (  # noqa: E402, F401 — backward-compat re-exports
    _EXPLICIT_CONTINUATION_RE,
    _classify_agent_request,
    _detect_admin_intent,
    _extract_last_user_message,
    _insert_before_latest_user,
    _is_casual_low_signal,
    _is_email_document_obj,
    _is_explicit_continuation,
    _looks_like_memory_identity_turn,
    _looks_like_notes_list_request,
    _looks_like_notes_turn,
    _minimal_saved_memory_message,
    _note_list_summary_from_tool_output,
    _recent_context_for_retrieval,
    _turn_targets_active_document,
    _uploaded_files_context_message,
    _user_turn_count,
)

from src.agent.context import (  # noqa: E402, F401 — backward-compat re-exports
    _build_actions_snapshot,
    _compute_final_metrics,
    _empty_response_fallback,
    _strip_think_blocks,
)

from src.agent.runaway import _detect_runaway_call  # noqa: E402, F401 — backward-compat re-export

from src.agent.verifier import (  # noqa: E402, F401 — backward-compat re-exports
    _append_tool_results,
    _resolve_tool_blocks,
)

# Heavy loop / prompt symbols are imported lazily so that consumers that only need the
# lightweight classifier/context/verifier helpers don't pay the cost of loading
# the full streaming orchestrator.
_LAZY_AGENT_LOOP_EXPORTS = {
    "FUNCTION_TOOL_SCHEMAS",
    "PLAN_MODE_DIRECTIVE",
    "_build_system_prompt",
    "_endpoint_lookup_keys",
    "_is_ollama_openai_compat_url",
    "_normalize_stream_document_fences",
    "build_active_plan_note",
    "stream_agent_loop",
}


def __getattr__(name: str):
    if name in _LAZY_AGENT_LOOP_EXPORTS:
        if name == "FUNCTION_TOOL_SCHEMAS":
            from src.tool_schemas import FUNCTION_TOOL_SCHEMAS  # noqa: F811

            return FUNCTION_TOOL_SCHEMAS
        if name == "_build_system_prompt":
            from src.agent.prompt import _build_system_prompt  # noqa: F811

            return _build_system_prompt
        from src.agent import loop as _loop_module

        return getattr(_loop_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [  # noqa: F822 — loop re-exports resolved via __getattr__
    "AGENT_SYSTEM_PROMPT",
    "PLAN_MODE_DIRECTIVE",
    "TOOL_SECTIONS",
    "build_active_plan_note",
    "get_builtin_overrides",
    "stream_agent_loop",
]
