"""Tests for src.agent.context — context utilities and metrics.

Black-box tests against the public function surface; no internal state
or private variables are inspected.
"""
from __future__ import annotations

from src.agent.context import (
    _build_actions_snapshot,
    _compute_final_metrics,
    _empty_response_fallback,
    _strip_think_blocks,
)


# ---------------------------------------------------------------------------
# _strip_think_blocks
# ---------------------------------------------------------------------------

class TestStripThinkBlocks:
    """Verify linear-time <think>…</think> stripping."""

    def test_empty_string_unchanged(self):
        assert _strip_think_blocks("") == ""

    def test_none_string_unchanged(self):
        assert _strip_think_blocks(None) is None  # type: ignore[arg-type]

    def test_no_think_tags_unchanged(self):
        text = "Hello, world!"
        assert _strip_think_blocks(text) == text

    def test_single_think_block_removed(self):
        assert _strip_think_blocks("<think>hidden</think>visible") == "visible"

    def test_think_tags_case_insensitive(self):
        assert _strip_think_blocks("<THINK>x</THINK>y") == "y"
        assert _strip_think_blocks("<Think>x</Think>y") == "y"

    def test_multiline_think_block_removed(self):
        text = "before<think>\nmultiline\ncontent\n</think>after"
        assert _strip_think_blocks(text) == "beforeafter"

    def test_dangling_opener_left_intact(self):
        """A <think> with no closer must be left as-is (matches lazy regex)."""
        text = "prefix<think>unclosed"
        assert _strip_think_blocks(text) == text

    def test_orphan_closer_not_stripped(self):
        """A </think> with no prior opener is left intact."""
        text = "no opener</think>text"
        assert _strip_think_blocks(text) == text

    def test_multiple_think_blocks(self):
        assert _strip_think_blocks("<think>a</think>X<think>b</think>Y") == "XY"

    def test_result_byte_for_byte_with_well_formed_input(self):
        """Matches what the regex variant produces on well-formed text."""
        import re
        text = "hello <think>hidden stuff</think> world <think>more</think> !"
        regex_result = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        assert _strip_think_blocks(text) == regex_result


# ---------------------------------------------------------------------------
# _empty_response_fallback
# ---------------------------------------------------------------------------

class TestEmptyResponseFallback:
    """Guard against completely empty final responses."""

    def test_non_empty_response_returned_as_is(self):
        resp, chunk = _empty_response_fallback("Hello!", "", [])
        assert resp == "Hello!"
        assert chunk is None

    def test_tool_events_suppress_fallback(self):
        """Even with empty full_response, tool events mean work was done."""
        resp, chunk = _empty_response_fallback("", "", [{"tool": "bash"}])
        assert resp == ""
        assert chunk is None

    def test_reasoning_only_returns_reasoning_no_chunk(self):
        """When only reasoning content exists, return it silently."""
        resp, chunk = _empty_response_fallback("", "reasoning text", [])
        assert resp == "reasoning text"
        assert chunk is None

    def test_truly_empty_returns_error_message_and_chunk(self):
        resp, chunk = _empty_response_fallback("", "", [])
        assert "empty response" in resp.lower()
        assert chunk is not None
        assert "data:" in chunk

    def test_whitespace_only_response_treated_as_empty(self):
        """Whitespace-only response with no tools and no reasoning triggers the fallback."""
        resp, chunk = _empty_response_fallback("   \n\t  ", "", [])
        # full_response.strip() == "" and no tool_events and no reasoning
        # → triggers the error-message path.
        assert chunk is not None
        assert "empty" in resp.lower()


# ---------------------------------------------------------------------------
# _compute_final_metrics (duplicates some tests from test_agent_loop.py to
# confirm the extracted module behaves identically to the original)
# ---------------------------------------------------------------------------

class TestComputeFinalMetricsExtracted:
    """Spot-check the extracted _compute_final_metrics module."""

    def _base(self, **kw):
        defaults = dict(
            messages=[{"role": "user", "content": "hello"}],
            full_response="Test response.",
            total_duration=2.0,
            time_to_first_token=0.5,
            context_length=8192,
            real_input_tokens=100,
            real_output_tokens=50,
            has_real_usage=True,
            tool_events=[],
            round_texts=[],
            model="test-model",
            last_round_input_tokens=0,
            prep_timings=None,
        )
        defaults.update(kw)
        return defaults

    def test_real_usage_used_when_flag_set(self):
        m = _compute_final_metrics(**self._base())
        assert m["input_tokens"] == 100
        assert m["output_tokens"] == 50
        assert m["usage_source"] == "real"

    def test_estimated_usage_when_flag_false(self):
        m = _compute_final_metrics(**self._base(
            has_real_usage=False,
            real_input_tokens=0,
            real_output_tokens=0,
        ))
        assert m["usage_source"] == "estimated"

    def test_tps_uses_backend_gen_tps_when_available(self):
        m = _compute_final_metrics(**self._base(
            real_output_tokens=100,
            total_duration=5.0,
        ), backend_gen_tps=42.5)
        assert m["tokens_per_second"] == 42.5
        assert m["tps_source"] == "backend"

    def test_tps_fallback_to_computed(self):
        m = _compute_final_metrics(**self._base(
            real_output_tokens=100,
            total_duration=2.0,
            has_real_usage=True,
        ))
        assert m["tokens_per_second"] == 50.0
        assert m["tps_source"] == "computed"

    def test_context_percent_capped_at_100(self):
        m = _compute_final_metrics(**self._base(
            real_input_tokens=10000,
            context_length=8192,
        ))
        assert m["context_percent"] == 100.0

    def test_no_tool_events_key_when_empty(self):
        m = _compute_final_metrics(**self._base())
        assert "tool_events" not in m
        assert "round_texts" not in m

    def test_tool_events_included_when_present(self):
        events = [{"tool": "bash"}]
        m = _compute_final_metrics(**self._base(tool_events=events, round_texts=["r"]))
        assert m["tool_events"] == events


# ---------------------------------------------------------------------------
# _build_actions_snapshot
# ---------------------------------------------------------------------------

class TestBuildActionsSnapshot:
    """Compact record of tool executions (for the completion verifier)."""

    def test_empty_events_returns_empty_string(self):
        assert _build_actions_snapshot([]) == ""

    def test_single_event_contains_tool_name(self):
        snap = _build_actions_snapshot([{"tool": "bash", "command": "ls", "output": "file.txt"}])
        assert "[bash]" in snap
        assert "ls" in snap
        assert "file.txt" in snap

    def test_long_output_truncated(self):
        snap = _build_actions_snapshot([
            {"tool": "bash", "command": "cat", "output": "x" * 2000},
        ])
        assert "…" in snap

    def test_non_zero_exit_code_shown(self):
        snap = _build_actions_snapshot([
            {"tool": "bash", "command": "false", "output": "", "exit_code": 1},
        ])
        assert "(exit 1)" in snap

    def test_zero_exit_code_not_shown(self):
        snap = _build_actions_snapshot([
            {"tool": "bash", "command": "true", "output": "ok", "exit_code": 0},
        ])
        assert "exit" not in snap

    def test_multiple_events_separated(self):
        events = [
            {"tool": "bash", "command": "ls", "output": "a"},
            {"tool": "python", "command": "print(1)", "output": "1"},
        ]
        snap = _build_actions_snapshot(events)
        assert "[bash]" in snap
        assert "[python]" in snap

    def test_snapshot_respects_limit(self):
        big = [{"tool": "bash", "command": "x", "output": "y" * 500} for _ in range(20)]
        snap = _build_actions_snapshot(big, limit=1000)
        assert len(snap) <= 1000
