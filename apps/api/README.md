# apps/api — Odysseus Backend

FastAPI application serving the Odysseus AI assistant.

## Quick start

```bash
cd apps/api
uv sync
uv sync --all-extras  # includes dev deps (pytest, httpx2)
uv run uvicorn app:app --host 127.0.0.1 --port 7000
```

## Nx targets

| Target | Command |
|--------|---------|
| build | `nx build api` |
| serve | `nx serve api` |
| test | `nx test api` |
| lint | `nx lint api` |
| typecheck | `nx typecheck api` |

## Structure

```
apps/api/
├── src/            # Application source (Python path root)
│   ├── app.py      # FastAPI entrypoint
│   ├── core/       # Infrastructure (auth, database, middleware)
│   ├── routes/     # HTTP route handlers
│   ├── src/        # Domain logic / agent / tools (→ domain/ in P2.2)
│   └── services/   # Service layer (search, memory, TTS/STT)
├── mcp_servers/    # MCP server implementations
├── integrations/   # Third-party integrations (Claude, Codex)
├── tests/          # Test suite
├── pyproject.toml  # Python project metadata + tool config
├── project.json    # Nx project configuration
├── requirements.txt
└── requirements-optional.txt
```
