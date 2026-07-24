"""
agent/classifier.py — Intent classification and request analysis for the
streaming agent loop.

Classifies each user turn so the loop can decide:
  - which tool domains to surface
  - whether this is a low-signal / casual turn
  - whether context from earlier turns should be inherited
  - whether the active editor document is relevant
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Admin-intent keyword list
# ---------------------------------------------------------------------------

_ADMIN_KEYWORDS = [
    "session", "sessions", "chat", "chats", "conversation", "conversations",
    "delete", "fork", "truncate",
    "archive", "rename", "endpoint", "endpoints", "api key",
    "webhook", "webhooks", "token", "tokens", "mcp", "server", "skill", "skills",
    "task", "tasks", "schedule", "cron", "setting", "settings", "preference",
    "configure", "config", "setup", "manage", "admin", "pipeline", "second opinion",
    "list models", "switch model", "change model", "theme", "create theme",
    # Documents
    "document", "documents", "doc", "docs", "library", "tidy",
    "note", "notes", "todo", "todos", "reminder", "reminders",
]


# ---------------------------------------------------------------------------
# Continuation / signal-level detection
# ---------------------------------------------------------------------------

_LOW_SIGNAL_RE = re.compile(r"^[\W_]*$", re.UNICODE)

_CASUAL_OPENING_RE = re.compile(
    r"^\s*(?:h+i+|hey+|hello+|yo+|sup+|what'?s up|wass?up|hiya|howdy|"
    r"lol|lmao|haha+|hehe+|thanks?|thank you|ty|idk|dunno|meh|bruh|bro)\b(?P<tail>.*)$",
    re.IGNORECASE,
)
_CASUAL_BLOCKLIST_RE = re.compile(
    r"\b(?:cookbook|serve|serving|launch|start|vllm|sglang|llama\.?cpp|ollama|"
    r"download|model|email|document|doc|note|calendar|task|search|web|research|"
    r"file|folder|repo|git|settings?|endpoint|api|token|mcp)\b",
    re.IGNORECASE,
)
_EXPLICIT_CONTINUATION_RE = re.compile(
    r"^\s*(?:"
    r"yes|y|yeah|yep|ok|okay|sure|do it|go ahead|continue|carry on|"
    r"run it|launch it|start it|use that|that one|same|the same|"
    r"first|second|third|the first one|the second one|the third one|"
    r"[123]|[abc]"
    r")\s*(?:[.!?]+\s*)?$",
    re.IGNORECASE,
)
_RETRY_CONTINUATION_RE = re.compile(
    r"\b(?:try again|retry|again|rerun|re-run|run it again|launch it again|"
    r"start it again|failed|fails?|died|crashed|broke|insta|instantly)\b",
    re.IGNORECASE,
)
_COOKBOOK_CONTEXT_RE = re.compile(
    r"\b(?:cookbook|serve|serving|served|launch|start|preset|vllm|sglang|"
    r"llama\.?cpp|ollama|download|cached models?|model servers?|running models?|"
    r"gpu box|ajax|qwen|gemma|llama|mistral|minimax)\b",
    re.IGNORECASE,
)


def _is_explicit_continuation(text: str) -> bool:
    """Only terse replies that express consent may inherit older user turns."""
    return bool(_EXPLICIT_CONTINUATION_RE.match(str(text or "").strip()))


def _is_casual_low_signal(text: str) -> bool:
    """True for short greetings/slang that should not inherit stale context."""
    s = str(text or "").strip()
    m = _CASUAL_OPENING_RE.match(s)
    if not m:
        return False
    tail = m.group("tail") or ""
    if _CASUAL_BLOCKLIST_RE.search(tail):
        return False
    # Allow a short vocative/address after the opener without hardcoding.
    tail_words = re.findall(r"[A-Za-z0-9_'-]+", tail)
    return len(tail_words) <= 2


def _recent_context_for_retrieval(
    messages: List[Dict],
    max_user: int = 3,
    max_chars: int = 600,
) -> str:
    """Build the tool-retrieval query from the last few USER turns.

    A contextless follow-up ("yes", "and?", "do it in November") carries no
    tool signal on its own.  Concatenating recent user turns lets the follow-up
    inherit the topic so just-used tools stay surfaced.  Newest-first so the
    latest turn survives the length cap.
    """
    collected: list[str] = []
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
        content = (content or "").strip()
        meta = msg.get("metadata") or {}
        if (
            not content
            or meta.get("trusted") is False
            or content.startswith("[Tool execution results]")
        ):
            continue
        collected.append(content)
        if len(collected) >= max_user:
            break
    return "\n".join(collected)[:max_chars]


def _is_contextual_retry_continuation(messages: List[Dict], text: str) -> bool:
    """Treat "try again / it failed" as a continuation only for active tool work.

    Intentionally narrow so ordinary chat does not inherit stale Cookbook
    context.
    """
    latest = str(text or "").strip()
    if not latest or not _RETRY_CONTINUATION_RE.search(latest):
        return False
    recent = _recent_context_for_retrieval(messages, max_user=5, max_chars=1200)
    return bool(_COOKBOOK_CONTEXT_RE.search(recent))


def _assistant_requested_followup(messages: List[Dict]) -> bool:
    """True when the previous assistant turn asked for missing task details."""
    seen_latest_user = False
    for msg in reversed(messages):
        role = msg.get("role")
        if role == "user" and not seen_latest_user:
            seen_latest_user = True
            continue
        if not seen_latest_user:
            continue
        if role != "assistant":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
        text = str(content or "").lower()
        if "?" not in text:
            return False
        return bool(re.search(
            r"\b(what would you like|what should|what do you want|which one|which model|"
            r"what.+(?:todo|to-do|list|document|email|model|server|item)|"
            r"any specific|give me|tell me)\b",
            text,
        ))
    return False


# ---------------------------------------------------------------------------
# Message extraction utilities
# ---------------------------------------------------------------------------

def _extract_last_user_message(messages: List[Dict]) -> str:
    """Return the most recent user message as plain text."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    b.get("text", "") for b in content if isinstance(b, dict)
                )
            return content
    return ""


def _user_turn_count(messages: List[Dict]) -> int:
    """Count real user turns in the message list."""
    return sum(1 for msg in (messages or []) if msg.get("role") == "user")


def _insert_before_latest_user(messages: List[Dict], context_msg: Dict) -> List[Dict]:
    """Insert *context_msg* immediately before the latest user turn.

    Returns a new list; the original is not mutated.
    """
    out = list(messages or [])
    for idx in range(len(out) - 1, -1, -1):
        if out[idx].get("role") == "user":
            out.insert(idx, context_msg)
            return out
    out.append(context_msg)
    return out


def _uploaded_files_context_message(
    uploaded_files: Optional[List[Dict]],
) -> Optional[Dict]:
    """Build a context message describing files attached to the latest turn."""
    from src.prompt_security import untrusted_context_message

    if not uploaded_files:
        return None

    lines = ["Uploaded files attached to the latest user turn:"]
    for item in uploaded_files[:20]:
        name = str(item.get("name") or item.get("id") or "upload")
        bits = [
            f"id={item.get('id', '')}",
            f"name={name}",
        ]
        if item.get("mime"):
            bits.append(f"mime={item.get('mime')}")
        if item.get("size") is not None:
            bits.append(f"size={item.get('size')} bytes")
        if item.get("path"):
            bits.append(f"path={item.get('path')}")
        lines.append("- " + "; ".join(bits))
    if len(uploaded_files) > 20:
        lines.append(f"- ... {len(uploaded_files) - 20} more upload(s) omitted from this manifest")
    lines.extend([
        "",
        "The attachment contents may already be in the latest user message. "
        "If an attachment is marked truncated or omitted, read its listed path "
        "with `read_file` when that tool is available. Do not say uploaded files "
        "are undiscoverable when they are listed here.",
    ])
    return untrusted_context_message("current chat uploaded files", "\n".join(lines))


# ---------------------------------------------------------------------------
# Admin-intent detection
# ---------------------------------------------------------------------------

def _detect_admin_intent(messages: List[Dict]) -> bool:
    """Check if the last user message suggests admin/management tool usage."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    b.get("text", "") for b in content if isinstance(b, dict)
                )
            content_lower = content.lower()
            return any(kw in content_lower for kw in _ADMIN_KEYWORDS)
    return False


# ---------------------------------------------------------------------------
# Notes / memory turn detection
# ---------------------------------------------------------------------------

def _looks_like_notes_list_request(text: str) -> bool:
    """Whether the user is asking to see existing notes, not create one."""
    t = (text or "").lower()
    return bool(
        re.search(r"\b(what|show|list|see|current|existing|all|my)\b.{0,60}\bnotes?\b", t)
        or re.search(r"\bnotes?\b.{0,60}\b(what|show|list|see|current|existing|all|my)\b", t)
    )


def _note_list_summary_from_tool_output(raw: str, max_items: int = 20) -> str:
    """Format manage_notes list/search output for chat without an LLM pass."""
    if not isinstance(raw, str) or not raw.strip():
        return ""
    titles: list[str] = []
    for line in raw.splitlines():
        m = re.match(r"^\s*-\s+\[[^\]]+\]\s+\*\*(.*?)\*\*(.*)$", line)
        if not m:
            continue
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        suffix = re.sub(r"\s+", " ", m.group(2) or "").strip()
        label = f"{title} {suffix}".strip()
        if label:
            titles.append(label)
        if len(titles) >= max_items:
            break
    if not titles:
        if re.search(r"\b(no notes|0 notes|found 0)\b", raw, re.IGNORECASE):
            return "No notes found."
        return ""
    total = len(re.findall(r"^\s*-\s+\[[^\]]+\]\s+\*\*", raw, re.MULTILINE))
    heading_count = total or len(titles)
    result_lines = [f"Here are your notes ({heading_count}):"]
    result_lines.extend(f"- {title}" for title in titles)
    if total and total > len(titles):
        result_lines.append(f"- ...and {total - len(titles)} more")
    return "\n".join(result_lines)


def _looks_like_notes_turn(text: str) -> bool:
    """True when the user's message is about notes/todos/reminders."""
    q = (text or "").lower()
    if re.search(r"\b(notes?|todos?|to-?do|checklists?|reminders?)\b", q):
        return True
    if re.search(
        r"\b(?:take|jot|write down|add|create|make)\b.{0,80}\b(?:note|todo|to-?do|checklist|reminder)\b",
        q,
    ):
        return True
    if re.search(r"\b(?:buy|pick ?up|pickup)\b", q) and not re.search(
        r"\b(?:calendar|event|meeting|appointment|schedule)\b", q
    ):
        return True
    return False


def _looks_like_memory_identity_turn(text: str) -> bool:
    """True when the user is asking about their own identity/preferences."""
    q = re.sub(r"[^a-z0-9\s'?]", " ", (text or "").lower())
    q = re.sub(r"\bhwho\b", "who", q)
    return bool(re.search(
        r"\b("
        r"who am i|who i am|what'?s my name|what is my name|where do i live|"
        r"what do you know about me|about me|relate to me|use what you know|"
        r"remember\b|forget\b|my preference|my preferences|i prefer|"
        r"my memory|memories about me"
        r")\b",
        q,
    ))


# ---------------------------------------------------------------------------
# Saved-memory extraction
# ---------------------------------------------------------------------------

def _minimal_saved_memory_message(messages: List[Dict]) -> Optional[Dict]:
    """Extract up to 8 saved-memory facts from injected context messages."""
    facts: List[str] = []
    seen: set[str] = set()
    for message in messages:
        if not isinstance(message, dict):
            continue
        metadata = message.get("metadata") if isinstance(message, dict) else None
        source = str((metadata or {}).get("source") or "")
        if not source.startswith("saved memory:"):
            continue
        content = str(message.get("content") or "")
        content = re.sub(r"(?m)^\s*Source:\s*saved memory:[^\n]*\n?", "", content)
        content = content.replace("Core facts about the user:", "")
        content = re.sub(
            r"Memory context\. Do not reference unless the user asks about these topics\.\s*",
            "",
            content,
        )
        for line in content.splitlines():
            line = line.strip()
            if not line.startswith("- "):
                continue
            fact = line[2:].strip()
            if not fact or fact in seen:
                continue
            seen.add(fact)
            facts.append(fact)
            if len(facts) >= 8:
                break
        if len(facts) >= 8:
            break
    if not facts:
        return None
    logger.info("[agent-intent] odysseus doc minimal memory facts=%s", len(facts))
    return {
        "role": "user",
        "content": (
            "Saved user memory facts from Odysseus Brain. These are the same "
            "user facts available in the normal prompt path. Use them when "
            "the user asks for personalization, identity, background, "
            "preferences, or anything about \"me\" or \"my\":\n"
            + "\n".join(f"- {fact}" for fact in facts)
        ),
    }


# ---------------------------------------------------------------------------
# Document-relevance detection
# ---------------------------------------------------------------------------

def _is_email_document_obj(active_document: Any) -> bool:
    """True when the active document object is an email compose window."""
    if active_document is None:
        return False
    raw_doc = getattr(active_document, "current_content", "") or ""
    title_l = (getattr(active_document, "title", "") or "").strip().lower()
    return (
        getattr(active_document, "language", None) == "email"
        or title_l in {"new email", "new mail", "new message"}
        or (
            "To:" in raw_doc[:400]
            and "Subject:" in raw_doc[:400]
            and "\n---\n" in raw_doc
        )
    )


def _turn_targets_active_document(
    intent: Dict[str, object],
    last_user: str,
    active_document: Any,
) -> bool:
    """Return whether an open editor document should affect this turn.

    The editor can stay open while the user asks unrelated things ("who am I?",
    "search news"). Injecting document context/tools in those cases makes small
    models overfit to the visible document. Keep the active document only for
    explicit document domains or common document-edit continuations.
    """
    if active_document is None:
        return False
    raw_doc = getattr(active_document, "current_content", "") or ""
    title_l = (getattr(active_document, "title", "") or "").strip().lower()
    is_email_doc = (
        getattr(active_document, "language", None) == "email"
        or title_l in {"new email", "new mail", "new message"}
        or ("To:" in raw_doc[:400] and "Subject:" in raw_doc[:400] and "\n---\n" in raw_doc)
    )
    if "documents" in (intent.get("domains") or set()):
        return True
    text = str(last_user or "").strip().lower()
    if not text:
        return False
    if is_email_doc and re.search(
        r"\b("
        r"email|mail|reply|respond|response|draft|compose|send|"
        r"tell them|tell her|tell him|say|write|make it say|"
        r"japanese|japan|polite|formal|tone|style"
        r")\b",
        text,
    ):
        return True
    if re.search(
        r"\b(?:make|change|update|fix|edit|rewrite|rework|revise|replace|remove|delete|add|append|insert|set|turn)\b"
        r".{0,80}\b(?:day\s*\d+|row|rows|column|columns|table|section|chapter|part|paragraph|line|lines|"
        r"title|heading|body|intro|introduction|conclusion|schedule|itinerary|draft|content)\b",
        text,
    ):
        return True
    if re.search(
        r"\b(?:day\s*\d+|row|rows|column|columns|table|section|chapter|part|paragraph|line|lines|"
        r"title|heading|body|intro|introduction|conclusion|schedule|itinerary)\b"
        r".{0,80}\b(?:make|change|update|fix|edit|rewrite|rework|revise|replace|remove|delete|add|append|insert|set|turn)\b",
        text,
    ):
        return True
    if re.search(
        r"\b(?:add|insert|include|apply|put)\b.+\b(?:to it|to this|there|in it|in this|in the text|in the document)\b",
        text,
    ):
        return True
    if re.search(
        r"\b(?:make it|make this|expand it|expand this|extend it|extend this|continue it|continue this)\b"
        r".*\b(?:longer|shorter|bigger|smaller|more detailed|more concise|expanded|extended)?\b",
        text,
    ):
        return True
    return bool(re.search(
        r"\b("
        r"document|doc|draft|text|poem|story|essay|outline|letter|paragraph|"
        r"stanza|line|title|heading|section|sentence|word|caps|uppercase|"
        r"lowercase|rewrite|reword|style|tone|suggest|suggestions|feedback|"
        r"improve|edit|change|remove|delete|replace|add another|append|"
        r"original text|in the document|the document|this document"
        r")\b",
        text,
    ))


# ---------------------------------------------------------------------------
# Main intent classifier
# ---------------------------------------------------------------------------

def _classify_agent_request(
    messages: List[Dict],
    last_user: str,
) -> Dict[str, object]:
    """Classify only whether this turn deserves domain tool retrieval.

    Normal chat should not inherit old Cookbook/email/document context.
    Recent context is used only for explicit continuations ("yes", "do it",
    "1"). This function does not inject tools directly; selected tools later
    decide which domain rule packs are appended to the system prompt.
    """
    text = str(last_user or "").strip()
    retry_continuation = _is_contextual_retry_continuation(messages, text)
    continuation = (
        _is_explicit_continuation(text)
        or _assistant_requested_followup(messages)
        or retry_continuation
    )
    retrieval_query = _recent_context_for_retrieval(messages) if continuation else text
    q = retrieval_query.lower()

    if not text or bool(_LOW_SIGNAL_RE.match(text)) or _is_casual_low_signal(text):
        return {
            "low_signal": True,
            "continuation": False,
            "domains": set(),
            "retrieval_query": text,
        }

    domains: Set[str] = set()

    def has(*patterns: str) -> bool:
        return any(re.search(p, q) for p in patterns)

    if has(
        r"\b(cookbook|serve|serving|served|launch|start|preset|vllm|sglang|llama\.?cpp|ollama|"
        r"download|downloading|pull|cached models?|running models?|model servers?|"
        r"models? (?:are )?running|what models?|model picker|gpu box|kierkegaard|"
        r"odysseus|ajax|qwen|gemma|llama|mistral|minimax)\b"
    ):
        domains.add("cookbook")
    if has(
        r"\b(emails?|mails?|gmail|inbox|reply|forward|cc|bcc|send email|compose email|"
        r"draft email|message chris|message him|message her)\b"
    ):
        domains.add("email")
    if has(
        r"\b(notes?|todos?|to-dos?|checklists?|task list|remind me|reminders?|buy|pickup|pick up)\b"
    ):
        domains.add("notes_calendar_tasks")
    if has(
        r"\b(every day|every morning|every evening|recurring|automatically|cron|"
        r"scheduled task|background task)\b"
    ):
        domains.add("notes_calendar_tasks")
    if has(r"\b(calendar|event|meeting|appointment|schedule)\b"):
        domains.add("notes_calendar_tasks")
    if has(
        r"\b(documents?|docs?|draft|compose|poem|story|essay|outline|letter|"
        r"edit|rewrite|proofread|suggest|feedback|review this|make a file)\b"
    ):
        domains.add("documents")
    if "notes_calendar_tasks" not in domains and has(r"\bwrite\b"):
        domains.add("documents")
    if has(
        r"\b(search|web|google|look up|latest|news|current|weather|forecast|"
        r"stock price|price of|website|url|https?://|www\.)\b"
    ):
        domains.add("web")
    if has(
        r"\b(wyszukaj|wyszukać|wyszukac)\b.*\b(internet|internecie|online|web)\b",
        r"\b(sprawd[zź]|znajd[zź])\b.*\b(internet|internecie|online|web)\b",
        r"\b(aktualn\w*|bieżąc\w*|biezac\w*|dzisiaj|teraz)\b.*\b(pogod\w*|temperatur\w*)\b",
    ):
        domains.add("web")
    if has(r"\b(research|deep dive|investigate|look into)\b"):
        domains.add("web")
    if has(
        r"\b(open|show|toggle|turn on|turn off|disable|enable|switch model|change model|"
        r"settings|theme|panel)\b"
    ):
        domains.add("ui")
    if has(r"\b(session|chat history|rename chat|delete chat|archive chat|fork chat|list chats)\b"):
        domains.add("sessions")
    if has(
        r"\b(file|folder|directory|repo|git|grep|find in files|read file|edit file|"
        r"shell|terminal|bash)\b"
    ):
        domains.add("files")
    if has(
        r"\b(run|execute|test|debug|fix|save|create|edit|read|open)\b.{0,40}\b("
        r"python|javascript|typescript|java|c\+\+|cpp|c#|csharp|rust|go|golang|"
        r"ruby|php|swift|kotlin|bash|shell|html|css|sql|code|script|program|game"
        r")\b",
        r"\b("
        r"python|javascript|typescript|java|c\+\+|cpp|c#|csharp|rust|go|golang|"
        r"ruby|php|swift|kotlin|bash|shell|html|css|sql"
        r")\b.{0,40}\b(file|script|program|app)\b",
    ):
        domains.add("files")
    if (
        has(r"\b(background|bg)\s+(jobs?|task)\b")
        or has(r"\b(kill|stop|cancel|terminate|check|tail|show|list)\b.{0,16}\bjobs?\b")
        or has(r"\bjobs?\b.{0,16}\b(output|status|done|finished|running)\b")
    ):
        domains.add("files")
    if has(r"\b(endpoint|api token|mcp|webhook|preference|configure|config|setting)\b"):
        domains.add("settings")
    if has(r"\b(contact|contacts|phone|phone number|address book|vcard)\b"):
        domains.add("contacts")
    if has(
        r"\bapi[ _]call\b",
        r"\bintegrations?\b",
        r"\b(?:home ?assistant|miniflux|gitea|linkding|jellyfin)\b",
    ):
        domains.add("integrations")

    low_signal = not continuation and not domains
    return {
        "low_signal": low_signal,
        "continuation": continuation,
        "domains": domains,
        "retrieval_query": retrieval_query,
    }
