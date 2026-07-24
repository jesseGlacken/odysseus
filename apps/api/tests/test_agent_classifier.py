"""Tests for src.agent.classifier — intent classification and request analysis.

Black-box tests through the public function interface.
"""
from __future__ import annotations

from src.agent.classifier import (
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
    _note_list_summary_from_tool_output,
    _turn_targets_active_document,
    _user_turn_count,
)


# ---------------------------------------------------------------------------
# _is_explicit_continuation
# ---------------------------------------------------------------------------

class TestIsExplicitContinuation:
    def test_yes(self):
        assert _is_explicit_continuation("yes") is True

    def test_ok(self):
        assert _is_explicit_continuation("ok") is True

    def test_do_it(self):
        assert _is_explicit_continuation("do it") is True

    def test_number_one(self):
        assert _is_explicit_continuation("1") is True

    def test_ok_with_period(self):
        assert _is_explicit_continuation("ok.") is True

    def test_full_sentence_is_not_continuation(self):
        assert _is_explicit_continuation("yes please write the python code") is False

    def test_empty_string(self):
        assert _is_explicit_continuation("") is False

    def test_greeting_is_not_continuation(self):
        assert _is_explicit_continuation("hello") is False


# ---------------------------------------------------------------------------
# _is_casual_low_signal
# ---------------------------------------------------------------------------

class TestIsCasualLowSignal:
    def test_hi(self):
        assert _is_casual_low_signal("hi") is True

    def test_hello(self):
        assert _is_casual_low_signal("hello") is True

    def test_thanks(self):
        assert _is_casual_low_signal("thanks") is True

    def test_lol(self):
        assert _is_casual_low_signal("lol") is True

    def test_greeting_with_task_is_not_low_signal(self):
        assert _is_casual_low_signal("hey search for the weather") is False

    def test_greeting_with_model_ref_is_not_low_signal(self):
        assert _is_casual_low_signal("hi serve the model") is False

    def test_question_is_not_low_signal(self):
        assert _is_casual_low_signal("what is the capital of France?") is False


# ---------------------------------------------------------------------------
# _extract_last_user_message
# ---------------------------------------------------------------------------

class TestExtractLastUserMessage:
    def test_returns_last_user_text(self):
        msgs = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "second"},
        ]
        assert _extract_last_user_message(msgs) == "second"

    def test_multimodal_list_content(self):
        msgs = [{"role": "user", "content": [
            {"type": "text", "text": "hello"},
            {"type": "image_url", "image_url": "..."},
        ]}]
        assert _extract_last_user_message(msgs) == "hello"

    def test_empty_messages_returns_empty(self):
        assert _extract_last_user_message([]) == ""

    def test_no_user_messages_returns_empty(self):
        msgs = [{"role": "assistant", "content": "hi"}]
        assert _extract_last_user_message(msgs) == ""


# ---------------------------------------------------------------------------
# _user_turn_count
# ---------------------------------------------------------------------------

class TestUserTurnCount:
    def test_counts_only_user_roles(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "1"},
            {"role": "assistant", "content": "a"},
            {"role": "user", "content": "2"},
        ]
        assert _user_turn_count(msgs) == 2

    def test_empty_returns_zero(self):
        assert _user_turn_count([]) == 0

    def test_none_returns_zero(self):
        assert _user_turn_count(None) == 0  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _insert_before_latest_user
# ---------------------------------------------------------------------------

class TestInsertBeforeLatestUser:
    def test_inserts_before_last_user(self):
        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "latest"},
        ]
        ctx = {"role": "system", "content": "context"}
        out = _insert_before_latest_user(messages, ctx)
        assert out.index(ctx) < out.index(messages[-1])
        assert len(out) == 4

    def test_does_not_mutate_original(self):
        messages = [{"role": "user", "content": "only"}]
        ctx = {"role": "system", "content": "ctx"}
        _ = _insert_before_latest_user(messages, ctx)
        assert len(messages) == 1

    def test_appends_when_no_user_message(self):
        messages = [{"role": "assistant", "content": "hi"}]
        ctx = {"role": "system", "content": "ctx"}
        out = _insert_before_latest_user(messages, ctx)
        assert out[-1] == ctx


# ---------------------------------------------------------------------------
# _looks_like_notes_list_request
# ---------------------------------------------------------------------------

class TestLooksLikeNotesListRequest:
    def test_show_notes(self):
        assert _looks_like_notes_list_request("show my notes") is True

    def test_list_notes(self):
        assert _looks_like_notes_list_request("list notes") is True

    def test_create_note_is_not_list(self):
        assert _looks_like_notes_list_request("create a note") is False

    def test_empty_is_not_list(self):
        assert _looks_like_notes_list_request("") is False


# ---------------------------------------------------------------------------
# _note_list_summary_from_tool_output
# ---------------------------------------------------------------------------

class TestNoteListSummaryFromToolOutput:
    _SAMPLE = (
        "- [1] **Buy groceries** (due tomorrow)\n"
        "- [2] **Call dentist**\n"
        "- [3] **Read book**\n"
    )

    def test_extracts_titles(self):
        result = _note_list_summary_from_tool_output(self._SAMPLE)
        assert "Buy groceries" in result
        assert "Call dentist" in result

    def test_empty_raw_returns_empty(self):
        assert _note_list_summary_from_tool_output("") == ""

    def test_no_notes_found_message(self):
        result = _note_list_summary_from_tool_output("no notes found")
        assert "No notes found" in result

    def test_non_string_returns_empty(self):
        assert _note_list_summary_from_tool_output(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _looks_like_notes_turn
# ---------------------------------------------------------------------------

class TestLooksLikeNotesTurn:
    def test_add_note(self):
        assert _looks_like_notes_turn("add a note to buy milk") is True

    def test_checklist(self):
        assert _looks_like_notes_turn("create a checklist") is True

    def test_remind_me(self):
        assert _looks_like_notes_turn("remind me to call dentist") is True

    def test_buy_is_notes(self):
        assert _looks_like_notes_turn("buy some coffee beans") is True

    def test_buy_for_meeting_is_not_notes(self):
        """'Buy' near 'calendar' language is excluded."""
        assert _looks_like_notes_turn("buy a ticket for the meeting event") is False

    def test_unrelated_request_is_not_notes(self):
        assert _looks_like_notes_turn("write a python script") is False


# ---------------------------------------------------------------------------
# _looks_like_memory_identity_turn
# ---------------------------------------------------------------------------

class TestLooksLikeMemoryIdentityTurn:
    def test_who_am_i(self):
        assert _looks_like_memory_identity_turn("who am i") is True

    def test_what_is_my_name(self):
        assert _looks_like_memory_identity_turn("what's my name") is True

    def test_remember_this(self):
        assert _looks_like_memory_identity_turn("remember this") is True

    def test_unrelated_question(self):
        assert _looks_like_memory_identity_turn("what is the weather?") is False


# ---------------------------------------------------------------------------
# _detect_admin_intent  (supplement tests already in test_agent_loop.py)
# ---------------------------------------------------------------------------

class TestDetectAdminIntentExtracted:
    """Verify the extracted function is callable and behaves correctly."""

    def test_no_messages_returns_false(self):
        assert _detect_admin_intent([]) is False

    def test_mcp_keyword_detected(self):
        msgs = [{"role": "user", "content": "add an MCP server"}]
        assert _detect_admin_intent(msgs) is True

    def test_unrelated_returns_false(self):
        msgs = [{"role": "user", "content": "write a haiku"}]
        assert _detect_admin_intent(msgs) is False


# ---------------------------------------------------------------------------
# _classify_agent_request
# ---------------------------------------------------------------------------

class TestClassifyAgentRequest:
    def test_email_domain_detected(self):
        intent = _classify_agent_request([], "check my inbox")
        assert "email" in intent["domains"]

    def test_web_domain_detected(self):
        intent = _classify_agent_request([], "search the web for python tips")
        assert "web" in intent["domains"]

    def test_low_signal_hello(self):
        intent = _classify_agent_request([], "hello")
        assert intent["low_signal"] is True

    def test_low_signal_empty(self):
        intent = _classify_agent_request([], "")
        assert intent["low_signal"] is True

    def test_polish_internet_search_detects_web_domain(self):
        intent = _classify_agent_request(
            [],
            "Wyszukaj w internecie i podaj temperaturę w Lubartowie dzisiaj",
        )
        assert intent["low_signal"] is False
        assert "web" in intent["domains"]

    def test_continuation_flag_set_for_yes(self):
        msgs = [
            {"role": "user", "content": "create a document"},
            {"role": "assistant", "content": "What title would you like?"},
        ]
        intent = _classify_agent_request(msgs, "yes")
        assert intent["continuation"] is True

    def test_notes_domain_detected(self):
        intent = _classify_agent_request([], "add a note: pick up dry cleaning")
        assert "notes_calendar_tasks" in intent["domains"]

    def test_files_domain_for_bash(self):
        intent = _classify_agent_request([], "run this bash script")
        assert "files" in intent["domains"]


# ---------------------------------------------------------------------------
# _is_email_document_obj
# ---------------------------------------------------------------------------

class TestIsEmailDocumentObj:
    class _Doc:
        def __init__(self, language=None, title="", current_content=""):
            self.language = language
            self.title = title
            self.current_content = current_content

    def test_none_active_document_returns_false(self):
        assert _is_email_document_obj(None) is False

    def test_email_language_detected(self):
        doc = self._Doc(language="email")
        assert _is_email_document_obj(doc) is True

    def test_new_email_title_detected(self):
        doc = self._Doc(title="New Email")
        assert _is_email_document_obj(doc) is True

    def test_header_content_detected(self):
        doc = self._Doc(
            current_content="To: user@example.com\nSubject: Test\n---\nBody",
        )
        assert _is_email_document_obj(doc) is True

    def test_regular_document_is_not_email(self):
        doc = self._Doc(language="markdown", title="My Notes", current_content="# Notes")
        assert _is_email_document_obj(doc) is False


# ---------------------------------------------------------------------------
# _turn_targets_active_document
# ---------------------------------------------------------------------------

class TestTurnTargetsActiveDocument:
    class _Doc:
        language = "markdown"
        title = "My Doc"
        current_content = "Some content here"

    def test_none_document_returns_false(self):
        assert _turn_targets_active_document({}, "edit this", None) is False

    def test_documents_domain_in_intent_returns_true(self):
        intent = {"domains": {"documents"}, "low_signal": False}
        assert _turn_targets_active_document(intent, "edit the doc", self._Doc()) is True

    def test_edit_request_matches_document_keywords(self):
        intent = {"domains": set(), "low_signal": False}
        assert _turn_targets_active_document(intent, "fix this document", self._Doc()) is True

    def test_unrelated_query_returns_false(self):
        intent = {"domains": set(), "low_signal": False}
        assert _turn_targets_active_document(intent, "what is the capital of france", self._Doc()) is False
