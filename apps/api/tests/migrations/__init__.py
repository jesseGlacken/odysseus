"""tests/migrations — migration pattern safety tests (ODY-60 / P2.8).

These tests verify the SQLite migration *pattern contracts* used by the 48+
inline migrations in core/database.py — ADD COLUMN guards, CREATE TABLE IF
NOT EXISTS, encryption round-trip, backfill WHERE clauses, and index creation.

They do NOT call individual _migrate_* functions (which require a file-backed
database and full SQLAlchemy stack).  They validate that the SQL patterns those
functions rely on are safe, idempotent, and data-preserving.

A follow-up (ODY-60b) will add file-backed integration tests that exercise the
actual _migrate_* functions through init_db().
"""
