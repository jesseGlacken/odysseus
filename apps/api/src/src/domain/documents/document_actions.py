"""
document_actions.py

Reusable document actions callable from both REST routes and the task scheduler.

Moved from src/document_actions.py to src/domain/documents/document_actions.py (ODY-19 / P2.2).
The original location keeps a backward-compat shim.
"""

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


_JUNK_TITLES = {
    "untitled", "untitled document", "new document", "document",
    "new email", "new mail", "new message", "reply", "fwd", "re:",
    "test", "testing", "asdf", "asd", "foo", "bar", "baz",
    "tmp", "temp", "scratch", "scratchpad", "draft", "delete",
    "remove", "junk", "trash", "xxx", "abc", "qwerty",
}


def _norm_title(t: str) -> str:
    t = t if isinstance(t, str) else ""
    return re.sub(r"\s+", " ", t.strip()).lower()


def _content_fingerprint(content: str) -> str:
    c = content if isinstance(content, str) else ""
    c = re.sub(r'upload_id="[^"]*"', "upload_id", c)
    c = re.sub(r"\bid=ann-[A-Za-z0-9_-]+", "id=ann", c)
    c = re.sub(r"\s+", " ", c).strip().lower()
    return c


def _real_len(content: str) -> int:
    content = content if isinstance(content, str) else ""
    stripped = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)
    stripped = re.sub(r"[*_`>\-=]+", "", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return len(stripped)


async def run_document_tidy(owner: str) -> str:
    """Remove clearly-junk documents and redundant duplicates for an owner."""
    from core.database import SessionLocal, Document, Session as DbSession  # noqa: F401

    db = SessionLocal()
    try:
        if owner:
            docs = db.query(Document).filter(Document.owner == owner).all()
        else:
            docs = db.query(Document).all()

        deleted_examples = []
        deleted = 0
        kept = 0
        survivors = []
        now = datetime.now(timezone.utc)

        for doc in docs:
            created = doc.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            if created and (now - created).total_seconds() < 900:
                survivors.append(doc)
                continue

            content = (doc.current_content or "").strip()
            title = (doc.title or "").strip().lower()
            is_fresh_empty = (not content and created is not None and (now - created).total_seconds() < 1800)
            if is_fresh_empty:
                survivors.append(doc)
                continue

            stripped = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)
            stripped = re.sub(r"[*_`>\-=]+", "", stripped)
            stripped = re.sub(r"\s+", " ", stripped).strip()

            lines = [ln for ln in content.split("\n") if ln.strip()]
            quoted_lines = [ln for ln in lines if ln.lstrip().startswith(">")]
            header_lines = [ln for ln in lines if re.match(r"^On .+ wrote:?\s*$", ln.strip())]
            non_quote_content = "\n".join(
                ln for ln in lines
                if not ln.lstrip().startswith(">") and not re.match(r"^On .+ wrote:?\s*$", ln.strip())
            ).strip()
            quote_ratio = len(quoted_lines) / max(len(lines), 1)

            should_delete = False
            reason = ""

            if not content or content in ("", "# Untitled"):
                should_delete = True
                reason = "empty"
            elif title in _JUNK_TITLES:
                should_delete = True
                reason = f"junk title '{title}'"
            elif stripped.lower() in _JUNK_TITLES:
                should_delete = True
                reason = "throwaway content"
            elif (quoted_lines or header_lines) and len(non_quote_content) < 50 and quote_ratio > 0.4:
                should_delete = True
                reason = "email quote-chain only"

            if should_delete:
                if len(deleted_examples) < 5:
                    label = (doc.title or "(no title)")[:40]
                    deleted_examples.append(f"{label} ({reason})")
                db.delete(doc)
                deleted += 1
            else:
                survivors.append(doc)

        groups: dict = {}
        for doc in survivors:
            key = (_norm_title(doc.title), _content_fingerprint(doc.current_content))
            groups.setdefault(key, []).append(doc)

        for (title_key, _fp), members in groups.items():
            if len(members) < 2:
                kept += 1
                continue

            def _updated(d):
                return d.updated_at or d.created_at

            members.sort(
                key=lambda d: (_real_len(d.current_content), _updated(d) is not None, _updated(d) or datetime.min),
                reverse=True,
            )
            keeper = members[0]
            kept += 1
            dupes = members[1:]
            if len(deleted_examples) < 5:
                label = (keeper.title or "(no title)")[:40]
                deleted_examples.append(f"{label} (+{len(dupes)} duplicate copies)")
            for d in dupes:
                db.delete(d)
                deleted += 1

        if deleted:
            db.commit()

        if deleted == 0:
            from src.builtin_actions import TaskNoop
            raise TaskNoop(f"scanned {len(docs)} document(s), no junk")
        preview = "; ".join(deleted_examples)
        extra = f" (+{deleted - len(deleted_examples)} more)" if deleted > len(deleted_examples) else ""
        return f"Removed {deleted} of {len(docs)}: {preview}{extra} · {kept} kept"
    finally:
        db.close()
