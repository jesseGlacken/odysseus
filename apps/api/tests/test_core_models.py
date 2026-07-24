"""Black-box importability and identity tests for core.models (ODY-21 / P2.5).

Verifies:
1. New canonical paths (core.models.*) work.
2. Legacy paths (core.database.*) still work (backward compat).
3. Both paths yield the SAME class object (same mapper registration, not a
   duplicate class that would conflict in SQLAlchemy's registry).
"""
from __future__ import annotations


class TestSessionModelsNewPath:
    def test_session_importable_from_core_models(self):
        from core.models.session_models import Session
        assert Session.__tablename__ == "sessions"

    def test_chat_message_importable_from_core_models(self):
        from core.models.session_models import ChatMessage
        assert ChatMessage.__tablename__ == "chat_messages"

    def test_session_importable_from_core_models_init(self):
        from core.models import DbSession
        assert DbSession.__tablename__ == "sessions"

    def test_chat_message_importable_from_core_models_init(self):
        from core.models import DbChatMessage
        assert DbChatMessage.__tablename__ == "chat_messages"


class TestDocumentModelsNewPath:
    def test_document_importable_from_core_models(self):
        from core.models.document_models import Document
        assert Document.__tablename__ == "documents"

    def test_document_version_importable_from_core_models(self):
        from core.models.document_models import DocumentVersion
        assert DocumentVersion.__tablename__ == "document_versions"

    def test_document_importable_from_core_models_init(self):
        from core.models import Document
        assert Document.__tablename__ == "documents"

    def test_document_version_importable_from_core_models_init(self):
        from core.models import DocumentVersion
        assert DocumentVersion.__tablename__ == "document_versions"


class TestEmailModelsNewPath:
    def test_email_account_importable_from_core_models(self):
        from core.models.email_models import EmailAccount
        assert EmailAccount.__tablename__ == "email_accounts"

    def test_email_account_importable_from_core_models_init(self):
        from core.models import EmailAccount
        assert EmailAccount.__tablename__ == "email_accounts"


class TestLegacyBackwardCompat:
    """from core.database import X must still work for all 65 existing importers."""

    def test_session_importable_from_core_database(self):
        from core.database import Session
        assert Session.__tablename__ == "sessions"

    def test_chat_message_importable_from_core_database(self):
        from core.database import ChatMessage
        assert ChatMessage.__tablename__ == "chat_messages"

    def test_document_importable_from_core_database(self):
        from core.database import Document
        assert Document.__tablename__ == "documents"

    def test_document_version_importable_from_core_database(self):
        from core.database import DocumentVersion
        assert DocumentVersion.__tablename__ == "document_versions"

    def test_email_account_importable_from_core_database(self):
        from core.database import EmailAccount
        assert EmailAccount.__tablename__ == "email_accounts"


class TestClassIdentity:
    """New path and legacy path must resolve to the SAME class object.

    Two distinct class objects with the same __tablename__ would raise a
    SQLAlchemy mapper conflict (InvalidRequestError: Table 'sessions' is
    already defined for this MetaData instance). The fact that tests pass
    at all implies identity, but we assert it explicitly for clarity.
    """

    def test_session_same_object(self):
        from core.models.session_models import Session as NewSession
        from core.database import Session as LegacySession
        assert NewSession is LegacySession

    def test_chat_message_same_object(self):
        from core.models.session_models import ChatMessage as NewCM
        from core.database import ChatMessage as LegacyCM
        assert NewCM is LegacyCM

    def test_document_same_object(self):
        from core.models.document_models import Document as NewDoc
        from core.database import Document as LegacyDoc
        assert NewDoc is LegacyDoc

    def test_document_version_same_object(self):
        from core.models.document_models import DocumentVersion as NewDV
        from core.database import DocumentVersion as LegacyDV
        assert NewDV is LegacyDV

    def test_email_account_same_object(self):
        from core.models.email_models import EmailAccount as NewEA
        from core.database import EmailAccount as LegacyEA
        assert NewEA is LegacyEA


class TestModelStructure:
    """Spot-check that key columns survived the extraction intact."""

    def test_session_has_messages_relationship(self):
        from core.models import DbSession
        assert hasattr(DbSession, 'messages')

    def test_session_has_to_dict(self):
        from core.models import DbSession
        assert callable(getattr(DbSession, 'to_dict', None))

    def test_chat_message_has_session_fk(self):
        from core.models import DbChatMessage
        col = DbChatMessage.__table__.c['session_id']
        assert col is not None

    def test_document_has_versions_relationship(self):
        from core.models import Document
        assert hasattr(Document, 'versions')

    def test_document_version_has_document_relationship(self):
        from core.models import DocumentVersion
        assert hasattr(DocumentVersion, 'document')

    def test_email_account_has_imap_host(self):
        from core.models import EmailAccount
        col = EmailAccount.__table__.c['imap_host']
        assert col is not None

    def test_email_account_has_oauth_columns(self):
        from core.models import EmailAccount
        assert 'oauth_provider' in EmailAccount.__table__.c
        assert 'oauth_access_token' in EmailAccount.__table__.c
