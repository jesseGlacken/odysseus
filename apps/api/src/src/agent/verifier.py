"""
agent/verifier.py — Tool-call resolution, result appending, and completion
verification for the streaming agent loop.

Contains:
- ``_resolve_tool_blocks``  — choose native function calls or fenced blocks
- ``_append_tool_results``  — append execution results to message history
- ``_run_verifier_subagent`` — independent completion check (mechanism 3a)
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool sets that merit independent completion verification
# ---------------------------------------------------------------------------

#: Tools whose effects produce a checkable artifact. A turn that used one of
#: these is "effectful" and worth an independent completion check; pure
#: read-only / Q&A turns are not.
_VERIFIER_EFFECTFUL_TOOLS: frozenset[str] = frozenset({
    "create_document", "update_document", "edit_document",
    "bash", "python", "write_file",
})

#: Hard cap on re-verify cycles per turn — never loop forever.
_VERIFIER_MAX_ROUNDS: int = 2


# ---------------------------------------------------------------------------
# Tool-block resolution
# ---------------------------------------------------------------------------

def _resolve_tool_blocks(
    round_response: str,
    native_tool_calls: list,
    round_num: int,
    is_api_model: bool = False,
    allow_fenced_for_api: bool = False,
) -> tuple[list, bool, list]:
    """Choose native function calls or fenced code block parsing.

    Returns ``(tool_blocks, used_native, converted_calls)``.

    *converted_calls* is the subset of *native_tool_calls* that successfully
    converted to :class:`~src.agent_tools.ToolBlock` objects and is aligned
    1-to-1 with *tool_blocks*.

    For native models with no ``tool_calls`` in their response any fenced
    ``\`\`\`bash / \`\`\`python / \`\`\`json`` block in prose is almost always
    an illustrative example for the user — not a real invocation — so it is
    skipped (*skip_fenced=True*) to avoid accidental runs.
    """
    from src.agent_tools import parse_tool_blocks, function_call_to_tool_block

    used_native = False
    converted_calls: list = []

    if native_tool_calls:
        tool_blocks = []
        for tc in native_tool_calls:
            tc_name = tc.get("name", "")
            tc_args = tc.get("arguments", "{}")
            block = function_call_to_tool_block(tc_name, tc_args)
            if block:
                tool_blocks.append(block)
                converted_calls.append(tc)
                logger.info("  -> converted: %s -> %s", tc_name, block.tool_type)
            else:
                logger.warning(
                    "  -> FAILED to convert native call: %s args=%s",
                    tc_name,
                    tc_args[:200],
                )
        if tool_blocks:
            used_native = True

    if not used_native:
        tool_blocks = parse_tool_blocks(
            round_response,
            skip_fenced=(is_api_model and not allow_fenced_for_api),
        )
        if tool_blocks:
            logger.info(
                "Agent round %d: %d fenced tool block(s) detected",
                round_num,
                len(tool_blocks),
            )

    resp_preview = (
        round_response[:200].replace("\n", "\\n") if round_response else "(empty)"
    )
    logger.info(
        "Agent round %d summary: %d chars, %d native calls, %d tool blocks. Preview: %s",
        round_num,
        len(round_response),
        len(native_tool_calls),
        len(tool_blocks),
        resp_preview,
    )

    return tool_blocks, used_native, converted_calls


# ---------------------------------------------------------------------------
# Tool-result appending
# ---------------------------------------------------------------------------

def _append_tool_results(
    messages: List[Dict],
    round_response: str,
    native_tool_calls: list,
    tool_results: list,
    tool_result_texts: list,
    used_native: bool,
    round_num: int,
    round_reasoning: str = "",
) -> None:
    """Append tool execution results back into message history for the next LLM round.

    *round_reasoning* (DeepSeek / vLLM reasoning-parser deltas) is echoed back
    via ``reasoning_content`` on the assistant message — DeepSeek's API rejects
    follow-up requests in thinking mode that omit the prior reasoning.

    NOTE: reasoning_content is kept **only on the most recent assistant turn**
    to avoid Nemotron re-injecting every prior ``<think>`` block (which bloats
    context and reinforces repetition).

    When the model emitted only tool calls with no prose the assistant message
    ``content`` must be ``null`` (Python ``None``), not ``""``.  Google Gemini
    and Ollama both reject ``tool_calls`` alongside empty-string content with
    HTTP 400.
    """
    from src.prompt_security import untrusted_context_message

    # Strip reasoning_content from all earlier assistant turns; only the
    # newest assistant turn carries it.
    for _m in messages:
        if _m.get("role") == "assistant":
            _m.pop("reasoning_content", None)

    if used_native and native_tool_calls:
        assistant_msg: Dict = {"role": "assistant"}
        # When the model emitted ONLY tool calls (no prose), content must be
        # None, NOT an empty string.
        assistant_msg["content"] = round_response if round_response.strip() else None
        if round_reasoning:
            assistant_msg["reasoning_content"] = round_reasoning
        assistant_msg["tool_calls"] = [
            {
                "id": tc.get("id", f"call_{round_num}_{j}"),
                "type": "function",
                "function": {
                    "name": tc.get("name", ""),
                    "arguments": tc.get("arguments", "{}"),
                },
                # Gemini 3 requires the opaque thought_signature to be echoed
                # back on the follow-up turn or it returns HTTP 400. Replay it
                # when present; other providers never emit it.
                **(
                    {"extra_content": tc["extra_content"]}
                    if tc.get("extra_content")
                    else {}
                ),
            }
            for j, tc in enumerate(native_tool_calls)
        ]
        messages.append(assistant_msg)
        for j, tc in enumerate(native_tool_calls):
            result_text = tool_result_texts[j] if j < len(tool_result_texts) else ""
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", f"call_{round_num}_{j}"),
                "content": result_text,
            })
    else:
        tool_output_text = "\n\n".join(tool_results)
        msg: Dict = {"role": "assistant", "content": round_response}
        if round_reasoning:
            msg["reasoning_content"] = round_reasoning
        messages.append(msg)
        # Tool output is sourced from outside the server — wrap it as untrusted
        # data so prompt-injection inside a tool result is treated as data, not
        # instructions (ADR-0008, THREAT_MODEL.md).
        messages.append(
            untrusted_context_message("tool execution results", tool_output_text)
        )


# ---------------------------------------------------------------------------
# Completion verifier subagent
# ---------------------------------------------------------------------------

async def _run_verifier_subagent(
    instruction: str,
    actions_snapshot: str,
    *,
    endpoint_url: str,
    model: str,
    headers: dict,
) -> list:
    """Independent completion check (mechanism 3a).

    A fresh-context model instance — with NO shared history — reads the user's
    request plus a record of what the agent did and judges whether the task is
    genuinely complete.  The independent context is the whole point: a model
    checking its own work rationalises; one that didn't do the work reads it
    cold.

    Returns a list of failure reasons (empty list = pass).  Any exception
    silently returns ``[]`` so it can never block a valid completion.
    """
    from src.agent.context import _strip_think_blocks
    from src.llm_core import llm_call_async

    prompt = (
        "You are an independent verifier. Another assistant just claimed the "
        "following task is complete. Using ONLY the request and the record of "
        "what it actually did, decide whether that claim is correct. Be strict: "
        "only say SUCCESS if the work genuinely satisfies the request.\n\n"
        f"<user_request>\n{(instruction or '')[:4000]}\n</user_request>\n\n"
        f"<actions_taken>\n{actions_snapshot[:8000]}\n</actions_taken>\n\n"
        "<checklist>\n"
        "1. Every concrete deliverable the request asked for was actually produced\n"
        "2. Outputs/edits match what was asked — nothing missing, no extra or unrequested changes\n"
        "3. Tool results show success, not errors or empty output that got ignored\n"
        "4. Anything the request said to leave alone was left unchanged\n"
        "</checklist>\n\n"
        "Reason briefly (2-3 sentences max). Then output EXACTLY one of:\n"
        "  VERIFICATION: SUCCESS\n"
        "  VERIFICATION: FAIL: <one short sentence per issue, semicolon-separated>\n"
        "Output nothing after the VERIFICATION line."
    )
    try:
        raw = await llm_call_async(
            url=endpoint_url,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            headers=headers,
            temperature=0.0,
            max_tokens=600,
            timeout=60,
        )
    except Exception as e:
        logger.warning("[agent] verifier subagent failed: %s", e)
        return []

    raw = _strip_think_blocks(raw or "")
    last_v = None
    for line in raw.splitlines():
        if "VERIFICATION:" in line:
            last_v = line.strip()
    if not last_v or "VERIFICATION: FAIL:" not in last_v:
        return []
    reasons = last_v.split("VERIFICATION: FAIL:", 1)[1].strip()
    return [r.strip() for r in reasons.split(";") if r.strip()]
