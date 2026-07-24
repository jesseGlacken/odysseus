"""Tests for src.agent.runaway — runaway-loop detection.

These are black-box tests against the public function interface;
no internal state is inspected.
"""
import collections

from src.agent.runaway import _detect_runaway_call


class TestDetectRunawayCall:
    """Tests for _detect_runaway_call."""

    def _freq(self, *sigs: str) -> collections.Counter:
        """Build a Counter from a list of call signatures."""
        return collections.Counter(sigs)

    # ── Should NOT flag ──────────────────────────────────────────────────

    def test_no_calls_returns_none(self):
        assert _detect_runaway_call(collections.Counter()) is None

    def test_single_call_returns_none(self):
        assert _detect_runaway_call(self._freq("bash:ls")) is None

    def test_fourteen_identical_calls_returns_none(self):
        c = collections.Counter({"bash:ls": 14})
        assert _detect_runaway_call(c) is None

    def test_distinct_calls_to_same_tool_returns_none(self):
        """A legitimate batch of distinct manage_calendar calls is not runaway."""
        sigs = [f"manage_calendar:create_event {i}" for i in range(20)]
        c = self._freq(*sigs)
        assert _detect_runaway_call(c) is None

    def test_threshold_is_exclusive_at_fourteen(self):
        """14 calls (< 15) must not trigger."""
        c = collections.Counter({"web_search:cats": 14})
        assert _detect_runaway_call(c) is None

    # ── Should flag ──────────────────────────────────────────────────────

    def test_fifteen_identical_calls_returns_tool_name(self):
        c = collections.Counter({"bash:ls -la": 15})
        assert _detect_runaway_call(c) == "bash"

    def test_sixteen_identical_calls_returns_tool_name(self):
        c = collections.Counter({"web_search:weather": 16})
        assert _detect_runaway_call(c) == "web_search"

    def test_returns_first_offending_tool(self):
        """When multiple sigs cross the threshold return one of them."""
        c = collections.Counter({
            "bash:cat /tmp/foo": 20,
            "python:print('hi')": 18,
        })
        result = _detect_runaway_call(c)
        assert result in ("bash", "python")

    # ── Custom threshold ─────────────────────────────────────────────────

    def test_custom_threshold_five(self):
        c = collections.Counter({"bash:echo hi": 5})
        assert _detect_runaway_call(c, threshold=5) == "bash"

    def test_custom_threshold_five_below_returns_none(self):
        c = collections.Counter({"bash:echo hi": 4})
        assert _detect_runaway_call(c, threshold=5) is None

    # ── Tool name extraction from compound signature ──────────────────────

    def test_signature_with_colon_in_content_still_returns_tool_name(self):
        """Signature contains ':' inside the content part; only first segment is tool."""
        c = collections.Counter({"bash:curl https://example.com": 20})
        assert _detect_runaway_call(c) == "bash"
