"""Black-box import tests for src.domain.infra package (ODY-19 / P2.2).

These tests verify that each module in the new domain package structure is
importable and that key public symbols are accessible. No implementation
details are tested — only the public surface.
"""
import pytest


class TestDomainInfraRuntimePaths:
    """src.domain.infra.runtime_paths"""

    def test_get_app_root_importable(self):
        from src.domain.infra.runtime_paths import get_app_root
        assert callable(get_app_root)

    def test_get_default_data_dir_importable(self):
        from src.domain.infra.runtime_paths import get_default_data_dir
        assert callable(get_default_data_dir)

    def test_get_app_root_returns_string(self):
        from src.domain.infra.runtime_paths import get_app_root
        result = get_app_root()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_app_root_matches_old_path(self):
        """After the move, get_app_root() must return the same value as before."""
        from src.domain.infra.runtime_paths import get_app_root as new_root
        from src.runtime_paths import get_app_root as old_root
        assert new_root() == old_root()

    def test_get_default_data_dir_returns_string(self):
        from src.domain.infra.runtime_paths import get_default_data_dir
        result = get_default_data_dir()
        assert isinstance(result, str)


class TestDomainInfraConstants:
    """src.domain.infra.constants"""

    def test_data_dir_importable(self):
        from src.domain.infra.constants import DATA_DIR
        assert isinstance(DATA_DIR, str)

    def test_max_output_chars_importable(self):
        from src.domain.infra.constants import MAX_OUTPUT_CHARS
        assert isinstance(MAX_OUTPUT_CHARS, int)
        assert MAX_OUTPUT_CHARS > 0

    def test_internal_api_base_importable(self):
        from src.domain.infra.constants import internal_api_base
        assert callable(internal_api_base)

    def test_constants_match_legacy(self):
        """New path must expose the same constants as the old path."""
        from src.domain.infra.constants import DATA_DIR as new_dir, MAX_OUTPUT_CHARS as new_max
        from src.constants import DATA_DIR as old_dir, MAX_OUTPUT_CHARS as old_max
        assert new_dir == old_dir
        assert new_max == old_max


class TestDomainInfraExceptions:
    """src.domain.infra.exceptions"""

    def test_session_not_found_error_importable(self):
        from src.domain.infra.exceptions import SessionNotFoundError
        assert issubclass(SessionNotFoundError, Exception)

    def test_all_exceptions_importable(self):
        from src.domain.infra.exceptions import (
            SessionNotFoundError,
            InvalidFileUploadError,
            LLMServiceError,
            WebSearchError,
        )
        for exc_cls in (SessionNotFoundError, InvalidFileUploadError, LLMServiceError, WebSearchError):
            assert issubclass(exc_cls, Exception)


class TestDomainInfraActionIntents:
    """src.domain.infra.action_intents"""

    def test_classify_tool_intent_importable(self):
        from src.domain.infra.action_intents import classify_tool_intent
        assert callable(classify_tool_intent)

    def test_message_needs_tools_importable(self):
        from src.domain.infra.action_intents import message_needs_tools
        assert callable(message_needs_tools)

    def test_tool_intent_dataclass_importable(self):
        from src.domain.infra.action_intents import ToolIntent
        ti = ToolIntent(needs_tools=False)
        assert ti.needs_tools is False

    def test_classify_calendar_intent(self):
        from src.domain.infra.action_intents import classify_tool_intent
        result = classify_tool_intent("add a meeting to my calendar tomorrow")
        assert result.needs_tools is True
        assert result.category == "calendar"

    def test_classify_plain_chat_not_tools(self):
        from src.domain.infra.action_intents import classify_tool_intent
        result = classify_tool_intent("what is the capital of France?")
        assert result.needs_tools is False

    def test_message_needs_tools_email(self):
        from src.domain.infra.action_intents import message_needs_tools
        assert message_needs_tools("send an email to Alice about the project") is True

    def test_message_needs_tools_empty(self):
        from src.domain.infra.action_intents import message_needs_tools
        assert message_needs_tools("") is False


class TestDomainInfraAttachmentRefs:
    """src.domain.infra.attachment_refs"""

    def test_attachment_ref_importable(self):
        from src.domain.infra.attachment_refs import attachment_ref
        assert callable(attachment_ref)

    def test_strip_inline_data_urls_importable(self):
        from src.domain.infra.attachment_refs import strip_inline_data_urls
        assert callable(strip_inline_data_urls)

    def test_persistable_message_content_importable(self):
        from src.domain.infra.attachment_refs import persistable_message_content
        assert callable(persistable_message_content)

    def test_strip_inline_data_urls_noop_on_plain(self):
        from src.domain.infra.attachment_refs import strip_inline_data_urls
        text = "Hello, world!"
        assert strip_inline_data_urls(text) == text

    def test_strip_inline_data_urls_removes_base64(self):
        from src.domain.infra.attachment_refs import strip_inline_data_urls
        text = "before data:image/png;base64,abc123== after"
        result = strip_inline_data_urls(text)
        assert "base64" not in result
        assert "before" in result
        assert "after" in result

    def test_attachment_ref_shape(self):
        from src.domain.infra.attachment_refs import attachment_ref
        info = {"id": "abc", "name": "photo.jpg", "mime": "image/jpeg", "size": 1024}
        ref = attachment_ref(info)
        assert ref["type"] == "attachment_ref"
        assert ref["attachment_id"] == "abc"
        assert ref["mime"] == "image/jpeg"
        assert ref["size"] == 1024

    def test_persistable_message_content_string(self):
        from src.domain.infra.attachment_refs import persistable_message_content
        result = persistable_message_content("Hello!")
        assert result == "Hello!"


class TestDomainInfraGeneratedImages:
    """src.domain.infra.generated_images"""

    def test_resolve_generated_image_path_importable(self):
        from src.domain.infra.generated_images import resolve_generated_image_path
        assert callable(resolve_generated_image_path)

    def test_generated_image_headers_importable(self):
        from src.domain.infra.generated_images import GENERATED_IMAGE_HEADERS
        assert "Cache-Control" in GENERATED_IMAGE_HEADERS

    def test_invalid_filename_raises(self):
        from src.domain.infra.generated_images import resolve_generated_image_path
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            resolve_generated_image_path("../../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_invalid_extension_raises(self):
        from src.domain.infra.generated_images import resolve_generated_image_path
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            resolve_generated_image_path("deadbeef12345678.txt")


class TestDomainPackagesImportable:
    """Smoke test: all domain __init__.py files are importable."""

    def test_domain_init_importable(self):
        import src.domain

    def test_domain_infra_init_importable(self):
        import src.domain.infra

    def test_domain_auth_init_importable(self):
        import src.domain.auth

    def test_domain_chat_init_importable(self):
        import src.domain.chat

    def test_domain_documents_init_importable(self):
        import src.domain.documents

    def test_domain_email_init_importable(self):
        import src.domain.email

    def test_domain_calendar_init_importable(self):
        import src.domain.calendar

    def test_domain_cookbook_init_importable(self):
        import src.domain.cookbook

    def test_domain_research_init_importable(self):
        import src.domain.research

    def test_domain_llm_init_importable(self):
        import src.domain.llm
