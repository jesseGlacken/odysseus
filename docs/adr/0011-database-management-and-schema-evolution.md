# ADR-0011: Database management & schema evolution

- **Status:** Accepted
- **Date:** 2026-07-22
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

v1 uses SQLite with 50+ inline migrations in `core/database.py` that run at startup via
`init_db()`. These migrations are ad-hoc: they check for the absence of a column with a
`try/except` or `PRAGMA table_info` and execute `ALTER TABLE ADD COLUMN` inline. Some
migrations also backfill data or encrypt existing plaintext secrets. None of them are
tested for idempotency or data preservation.

ADR-0004 mandates 100% coverage and black-box testing. The current inline migrations
would fail a thorough black-box audit: a migration that silently drops data or produces
an inconsistent schema would not be caught by any existing test.

Phase 2.5 splits `core/database.py` into domain models. That split is the right moment
to introduce a formal migration strategy.

Industry practice: Alembic (SQLAlchemy's migration tool) is the standard for Python
database migrations. It provides versioned, reversible, auto-generated migration scripts
with transaction management and idempotency guarantees. For a SQLite-backed project,
Alembic adds minimal overhead and replaces 2,500+ LOC of ad-hoc migration code with
versioned, testable scripts.

## Decision

1. **All schema migrations use Alembic with versioned migration scripts.** Inline
   `ALTER TABLE` / `CREATE TABLE` / `PRAGMA` migrations in `core/database.py` are
   extracted into Alembic revision files during Phase 2.5.

2. **Migrations are applied at application startup** via `alembic upgrade head` in the
   `_lifespan` context, replacing the current `init_db()` inline checks. This ensures
   the schema is at the expected version before any route handles a request. Startup
   fails fast if migrations cannot be applied.

3. **Every migration is tested for:**
   - **Idempotency:** Running the migration twice produces the same schema state. The
     test upgrades, downgrades, and upgrades again, asserting no errors.
   - **Data preservation:** Creating representative data in the pre-migration schema
     and verifying its integrity after upgrade.
   - **Edge cases:** Empty tables, tables with NULL values, concurrent access (simulated
     by opening two connections).
   - **Encryption round-trip:** Migrations that encrypt plaintext secrets are verified
     to correctly encrypt and later decrypt.

4. **Migration tests run against an in-memory SQLite database** (`sqlite:///:memory:`)
   in CI for speed. A subset of tests runs against a file-backed database to verify
   WAL mode and file-system behaviour.

5. **Downgrade paths are maintained for every migration** except irreversible data-loss
   operations (e.g., dropping a column). Irreversible migrations are documented with a
   comment explaining why and marked `down_revision = None` with a `# irreversible`
   annotation.

6. **Schema drift detection runs in CI.** A test generates the expected schema from
   `alembic upgrade head`, compares it to the actual schema after application startup,
   and fails on any difference. This catches migrations that were added but not applied.

7. **Database backup and restore** (existing `routes/backup_routes.py`) continues to
   export/import as JSON. The backup format is versioned so a backup from v1 can be
   restored into v2 after schema migration.

## Consequences

- **Positive:** migrations are explicit, versioned, tested, and reversible; schema
  drift is caught in CI; eliminates 2,500+ LOC of ad-hoc migration code; Alembic's
  auto-generation reduces manual ALTER TABLE errors.
- **Negative / costs:** converting 50+ inline migrations to Alembic scripts is effort;
  the team must learn Alembic's API; migration tests add to CI runtime; downgrade
  paths require maintenance.
- **Enforcement:** schema drift test in CI (blocking); migration test suite in CI
  (blocking); PRs that modify the database schema must include a new Alembic revision
  and its tests.

## Alternatives considered

- **Alembic with auto-generation only (no handwritten scripts).** Rejected:
  auto-generation handles ADD COLUMN but not data backfill, encryption, or complex
  schema transformations. Handwritten `upgrade()`/`downgrade()` functions are
  necessary for the 50+ existing migrations.
- **Keep inline migrations, just test them.** Rejected: inline migrations in a
  monolithic `database.py` create a coupling hub (56-file fan-in). Extracting them
  into Alembic scripts cleanly separates migration concerns from runtime ORM models.
- **SQLAlchemy-Migrate.** Rejected: Alembic is maintained by the SQLAlchemy authors
  and has broader adoption.
