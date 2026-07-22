# Gherkin Conventions

> How we write, organise, and automate Gherkin feature files for Odysseus v2.
> See [ADR-0004](../adr/0004-testing-standards-blackbox-100pct-mutation.md) for the mandate.

## File structure

```
features/
├── auth/
│   ├── login.feature
│   ├── registration.feature
│   ├── 2fa.feature
│   └── password-reset.feature
├── chat/
│   ├── sessions.feature
│   ├── messaging.feature
│   ├── streaming.feature
│   └── tool-calls.feature
├── documents/
│   ├── upload.feature
│   ├── viewer.feature
│   └── editor.feature
├── email/
│   ├── accounts.feature
│   ├── inbox.feature
│   └── compose.feature
├── settings/
│   ├── models.feature
│   ├── users.feature
│   └── appearance.feature
└── accessibility/
    ├── keyboard-navigation.feature
    ├── screen-reader.feature
    └── color-contrast.feature
```

- One `.feature` file per domain sub-area.
- One directory per domain (`auth/`, `chat/`, etc.).
- Cross-cutting concerns (accessibility) get their own directory.
- Feature files live at the repo root in `features/`.

## File format

```gherkin
Feature: User login
  As a registered user
  I want to log in with my credentials
  So that I can access my account

  Background:
    Given a user exists with email "test@example.com" and password "correct-horse-battery-staple"

  @api @smoke
  Scenario: Successful login with valid credentials
    When the user sends a POST request to "/api/v1/auth/login" with:
      | email    | test@example.com              |
      | password | correct-horse-battery-staple  |
    Then the response status is 200
    And the response contains a session token
    And the response contains the user profile

  @api
  Scenario: Login fails with incorrect password
    When the user sends a POST request to "/api/v1/auth/login" with:
      | email    | test@example.com  |
      | password | wrong-password     |
    Then the response status is 401
    And the error type is "AuthenticationError"
    And the error message is "Authentication required"

  @e2e @a11y
  Scenario: Login form is keyboard accessible
    Given the user is on the login page
    When the user presses Tab
    Then focus moves to the email input
    And the email input has a visible focus indicator
    When the user presses Tab
    Then focus moves to the password input
    When the user presses Tab
    Then focus moves to the submit button
    When the user presses Enter
    Then the form is submitted
```

## Tags

Tags classify scenarios by test level and characteristics. Use them to filter test runs.

| Tag | Meaning | Runner |
|-----|---------|--------|
| `@api` | Exercises an HTTP endpoint through TestClient/httpx | `pytest-bdd` |
| `@e2e` | Exercises the full stack through a browser | `playwright-bdd` |
| `@smoke` | Critical path — run on every commit | Both |
| `@slow` | Takes > 5 seconds — run in nightly/long CI only | Both |
| `@a11y` | Includes accessibility assertions (axe, roles, labels) | `playwright-bdd` |
| `@regression` | Guards against a specific past bug | Both |
| `@wip` | Work in progress — skipped in CI, run manually | Both |

**Rules:**
- Every scenario carries at least `@api` or `@e2e`.
- `@smoke` scenarios are kept to a minimum — they gate every commit.
- `@wip` scenarios must not remain `@wip` past the PR that introduces them.
- Prefer multiple focused tags over one broad tag.

## Step definitions

### Backend (pytest-bdd)

```
tests/
└── bdd/
    ├── steps/
    │   ├── conftest.py          # Shared fixtures (TestClient, in-memory DB)
    │   ├── auth_steps.py        # Given/When/Then for auth scenarios
    │   ├── chat_steps.py
    │   ├── email_steps.py
    │   └── ...
    └── conftest.py              # pytest-bdd plugin registration
```

Step definition files are named `{domain}_steps.py` and map to `features/{domain}/`.

**Rules for backend steps:**
- Steps exercise the public HTTP surface only (`TestClient` or `httpx.AsyncClient`).
- Steps never import from `routes/`, `core/`, or `src/` directly.
- Steps use the generated SDK (`packages/client-sdk`) where practical for type safety.
- Shared fixtures (database setup, auth headers) live in `tests/bdd/steps/conftest.py`.
- Step text is declarative, not procedural ("Given a user exists" not "Given INSERT INTO users...").

### Frontend (playwright-bdd)

```
e2e/
├── steps/
│   ├── fixtures.ts             # Page fixtures, auth helpers
│   ├── auth.steps.ts
│   ├── chat.steps.ts
│   ├── navigation.steps.ts
│   └── ...
└── playwright.config.ts
```

Step definition files are named `{domain}.steps.ts` and map to `features/{domain}/`.

**Rules for frontend steps:**
- Steps query the DOM by **role** and **accessible name/label** (`page.getByRole("button", { name: "Send" })`).
- Steps never use CSS selectors, `data-testid`, or XPath for element location.
- Every `@a11y` scenario includes an `axe` check: `await expect(page).toPassAxeCheck()`.
- Steps use `Given` to set up state via API calls (fast), not UI clicks (slow).
- Shared setup (login, seed data) lives in `e2e/steps/fixtures.ts`.

## Naming conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Feature file | `kebab-case.feature` | `password-reset.feature` |
| Feature name | Sentence case, describes user goal | `Feature: Password reset` |
| Scenario name | Sentence case, describes outcome | `Scenario: Reset link is sent to verified email` |
| Step text | Declarative, third person | `Given a user exists with email "x"` |
| Step definition file | `snake_case.py` (BE), `kebab-case.ts` (FE) | `auth_steps.py`, `auth.steps.ts` |
| Step function | `snake_case` (BE), `camelCase` (FE) | `def given_user_exists(...)`, `Given('...', async ({ page }) => {...})` |
| Tag | `@lowercase` | `@smoke`, `@a11y`, `@regression` |

## Scenario writing guidelines

1. **One behaviour per scenario.** If a scenario has "and then" in the middle, split it.
2. **Background over repeated Givens.** Preconditions shared by every scenario in a feature go in `Background:`.
3. **Scenario Outlines for data variations.** Use `Scenario Outline:` with `<placeholders>` and `Examples:` tables for equivalent behaviours with different inputs.
4. **No imperative detail in When steps.** Write "When the user submits the login form" not "When the user clicks the button with ID login-button".
5. **Then steps assert one fact each.** Split multi-assertion Thens into separate steps — clearer failure messages.
6. **Error scenarios name the error.** Prefer `Then the error type is "ValidationError"` over `Then an error is returned`.

## CI integration

```yaml
# Backend: run @api scenarios (exclude @slow and @wip)
pytest-bdd:
  script: pytest tests/bdd/ --gherkin-terminal-reporter -m "not slow and not wip"

# Frontend: run @e2e @smoke scenarios
playwright-bdd:
  script: npx playwright test --grep "@smoke"
```

**Gate behaviour:**
- `@api` scenarios gate `nx affected:test` (blocking).
- `@e2e @smoke` scenarios gate pre-merge (blocking).
- `@slow` scenarios run in nightly CI only (non-blocking, alert on failure).
- `@wip` scenarios are excluded from all CI runs.
