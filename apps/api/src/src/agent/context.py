"""
agent/context.py — Context-window utilities for the streaming agent loop.

Contains:
- ``_strip_think_blocks`` — remove <think>…</think> from model output (linear)
- ``_empty_response_fallback`` — guard against a completely empty response
- ``_compute_final_metrics`` — build the metrics dict streamed at turn end
- ``_build_actions_snapshot`` — compact record of what the agent did (for
  the completion-verifier)
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Think-block stripping
# ---------------------------------------------------------------------------

def _strip_think_blocks(text: str) -> str:
    """Remove ``<think>…</think>`` blocks in a single forward scan (O(n)).

    The naive ``re.sub(r'<think>.*?</think>', '', text, flags=DOTALL|IGNORECASE)``
    rescans from every ``<think>`` opener when a closer is missing, making it
    O(n²) on untrusted model output.  This implementation is byte-for-byte
    compatible with that regex for well-formed input and is linear even when
    the model emits thousands of un-closed openers.

    * A dangling opener with no closer is left intact.
    * An orphan ``</think>`` with no opener is never stripped.
    """
    if not text:
        return text
    lowered = text.lower()
    parts: list[str] = []
    pos = 0
    while True:
        start = lowered.find("<think>", pos)
        if start == -1:
            parts.append(text[pos:])
            break
        end = lowered.find("</think>", start + 7)
        if end == -1:
            # No closer — leave remainder intact (matches lazy-regex behaviour).
            parts.append(text[pos:])
            break
        parts.append(text[pos:start])
        pos = end + 8  # len("</think>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Empty-response guard
# ---------------------------------------------------------------------------

def _empty_response_fallback(
    full_response: str,
    round_reasoning: str,
    tool_events: list,
) -> tuple[str, str | None]:
    """Return *(final_response, sse_chunk_or_none)* for the end-of-loop guard.

    When a thinking model routes all tokens to ``reasoning_content``
    (``content=""``) ``full_response`` is empty but ``round_reasoning`` has
    content.  The reasoning was already streamed as ``{thinking:true}`` chunks
    — do not re-emit it as a normal delta; just persist it and yield nothing.

    Returns
    -------
    final_response : str
        The text to persist / pass on.
    chunk : str | None
        An SSE string to ``yield``, or ``None`` when nothing should be emitted.
    """
    import json as _json

    if full_response.strip() or tool_events:
        return full_response, None
    if round_reasoning.strip():
        return round_reasoning, None
    _error_msg = (
        "The model returned an empty response. "
        "Please try again or switch to a different model."
    )
    return _error_msg, f'data: {_json.dumps({"delta": _error_msg})}\n\n'


# ---------------------------------------------------------------------------
# Final metrics computation
# ---------------------------------------------------------------------------

def _compute_final_metrics(
    messages: List[Dict],
    full_response: str,
    total_duration: float,
    time_to_first_token: Optional[float],
    context_length: int,
    real_input_tokens: int,
    real_output_tokens: int,
    has_real_usage: bool,
    tool_events: list,
    round_texts: list,
    model: str = "",
    last_round_input_tokens: int = 0,
    prep_timings: Optional[Dict[str, float]] = None,
    backend_gen_tps: float = 0,
    backend_prefill_tps: float = 0,
) -> dict:
    """Compute token counts, TPS, and build the final metrics dict.

    Uses real API-reported usage when *has_real_usage* is ``True``, otherwise
    falls back to rough character-based estimation (len // 4).

    Prefers *backend_gen_tps* (pure decode speed from llama.cpp timings) over
    the tokens/wall-clock fallback, which reads low because it includes prefill
    and agent overhead.
    """

    if has_real_usage:
        input_tokens = real_input_tokens
        output_tokens = real_output_tokens
    else:
        input_content = ""
        for msg in messages:
            if isinstance(msg.get("content"), str):
                input_content += msg["content"] + "\n"
        input_tokens = len(input_content) // 4
        output_tokens = len(full_response) // 4

    # Prefer backend-reported true generation speed when available.
    if backend_gen_tps and backend_gen_tps > 0:
        tps = backend_gen_tps
    else:
        tps = output_tokens / total_duration if total_duration > 0 else 0

    # Use last round's input tokens for context % (peak usage) when available.
    ctx_tokens = last_round_input_tokens if last_round_input_tokens > 0 else input_tokens
    ctx_pct = (
        min(round((ctx_tokens / context_length) * 100, 1), 100.0)
        if context_length
        else 0
    )

    metrics: dict = {
        "response_time": round(total_duration, 2),
        "time_to_first_token": round(time_to_first_token, 2) if time_to_first_token else 0,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tokens_per_second": round(tps, 2),
        # ``backend`` = true decode speed; ``computed`` = tokens/wall-clock
        # (reads low — includes prefill/overhead).
        "tps_source": "backend" if (backend_gen_tps and backend_gen_tps > 0) else "computed",
        "total_tokens": input_tokens + output_tokens,
        "context_length": context_length,
        "context_percent": ctx_pct,
        "usage_source": "real" if has_real_usage else "estimated",
        "model": model,
    }
    if backend_prefill_tps and backend_prefill_tps > 0:
        metrics["prefill_tps"] = round(backend_prefill_tps, 2)
    if prep_timings:
        prep_total = round(sum(prep_timings.values()), 3)
        metrics["agent_prep_time"] = prep_total
        metrics["agent_model_wait_time"] = round(
            max((time_to_first_token or 0) - prep_total, 0), 3
        )
        metrics["agent_prep_breakdown"] = {
            key: round(value, 3) for key, value in prep_timings.items()
        }
    if tool_events:
        metrics["tool_events"] = tool_events
        metrics["round_texts"] = round_texts
    return metrics


# ---------------------------------------------------------------------------
# Actions snapshot (for the completion verifier)
# ---------------------------------------------------------------------------

def _build_actions_snapshot(tool_events: list, limit: int = 8000) -> str:
    """Compact record of what the agent actually did this turn.

    One block per tool execution: the command and a head of its output.
    Used by the independent completion-verifier subagent so it can judge
    whether the agent's claimed "done" is accurate.
    """
    parts = []
    for ev in tool_events:
        tool = ev.get("tool", "?")
        cmd = (ev.get("command") or "").strip()
        out = (ev.get("output") or "").strip()
        rc = ev.get("exit_code")
        head = f"[{tool}] {cmd}" if cmd else f"[{tool}]"
        rc_s = f" (exit {rc})" if rc not in (None, 0) else ""
        body = (out[:1200] + " …") if len(out) > 1200 else (out or "(no output)")
        parts.append(f"{head}{rc_s}\n-> {body}")
    snap = "\n\n".join(parts)
    return snap[:limit] if len(snap) > limit else snap
