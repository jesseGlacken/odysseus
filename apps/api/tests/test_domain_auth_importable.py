"""Black-box import tests for src.domain.auth package (ODY-19 / P2.2)."""
import pytest


class TestDomainAuthHelpers:
    """src.domain.auth.auth_helpers"""

    def test_get_current_user_importable(self):
        from src.domain.auth.auth_helpers import get_current_user
        assert callable(get_current_user)

    def test_require_user_importable(self):
        from src.domain.auth.auth_helpers import require_user
        assert callable(require_user)

    def test_require_privilege_importable(self):
        from src.domain.auth.auth_helpers import require_privilege
        assert callable(require_privilege)

    def test_owner_filter_importable(self):
        from src.domain.auth.auth_helpers import owner_filter
        assert callable(owner_filter)

    def test_effective_user_importable(self):
        from src.domain.auth.auth_helpers import effective_user
        assert callable(effective_user)


class TestDomainUserTime:
    """src.domain.auth.user_time"""

    def test_set_user_tz_offset_importable(self):
        from src.domain.auth.user_time import set_user_tz_offset
        assert callable(set_user_tz_offset)

    def test_get_user_tz_offset_importable(self):
        from src.domain.auth.user_time import get_user_tz_offset
        assert callable(get_user_tz_offset)

    def test_current_datetime_context_message_importable(self):
        from src.domain.auth.user_time import current_datetime_context_message
        assert callable(current_datetime_context_message)

    def test_clear_user_time_context(self):
        from src.domain.auth.user_time import clear_user_time_context, set_user_tz_offset, get_user_tz_offset
        set_user_tz_offset(300)
        assert get_user_tz_offset() == 300
        clear_user_time_context()
        assert get_user_tz_offset() is None

    def test_set_invalid_offset_ignored(self):
        from src.domain.auth.user_time import set_user_tz_offset, get_user_tz_offset, clear_user_time_context
        clear_user_time_context()
        set_user_tz_offset(99999)  # way out of range
        assert get_user_tz_offset() is None

    def test_format_utc_offset(self):
        from src.domain.auth.user_time import format_utc_offset
        assert format_utc_offset(60) == "+01:00"
        assert format_utc_offset(-330) == "-05:30"
        assert format_utc_offset(0) == "+00:00"

    def test_current_datetime_context_message_shape(self):
        from src.domain.auth.user_time import current_datetime_context_message
        msg = current_datetime_context_message()
        assert msg["role"] == "user"
        assert "date" in msg["content"].lower() or "time" in msg["content"].lower()


class TestDomainSessionActions:
    """src.domain.auth.session_actions"""

    def test_is_session_recently_active_importable(self):
        from src.domain.auth.session_actions import is_session_recently_active
        assert callable(is_session_recently_active)

    def test_run_auto_sort_importable(self):
        from src.domain.auth.session_actions import run_auto_sort
        assert callable(run_auto_sort)


class TestDomainSessionSearch:
    """src.domain.auth.session_search"""

    def test_search_session_messages_importable(self):
        from src.domain.auth.session_search import search_session_messages
        assert callable(search_session_messages)

    def test_session_search_result_importable(self):
        from src.domain.auth.session_search import SessionSearchResult
        assert hasattr(SessionSearchResult, "to_dict")
