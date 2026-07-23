# packages/contracts — OpenAPI Schema

The single source of truth for the Odysseus API contract. Generated from the
FastAPI app via `node generate.js`.

## Targets

| Target | Command | Description |
|--------|---------|-------------|
| generate | `nx generate contracts` | Generate `openapi.json` from the running app |
| test | `nx test contracts` | Run snapshot tests against the schema |

## Schema

`openapi.json` is **committed** — it is the snapshot that CI checks. Any PR
that changes the API surface must regenerate this file and the snapshot will
fail, requiring intentional review.

## Snapshot tests

- Schema parses as valid JSON
- OpenAPI version is 3.x
- Title is "Odysseus API"
- 400+ paths exist
