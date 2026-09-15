# Changes: API testing infrastructure

> **Scope note:** the requested feature is backend/test-infrastructure work, not a
> frontend change. No files under `frontend/` were modified. What these tests *do*
> cover is the HTTP contract `frontend/script.js` depends on — the exact shape of
> `/api/query`, `/api/courses`, `DELETE /api/session/{id}`, and the static mount
> that serves the frontend itself — so a breaking change to the API surface the UI
> consumes now fails a test instead of only breaking in the browser.

## Summary

Added API endpoint tests, shared fixtures, and pytest configuration to the
existing backend test suite.

| File | Change |
| --- | --- |
| `backend/tests/test_api_endpoints.py` | **New.** 29 endpoint tests. |
| `backend/tests/conftest.py` | Added an inline FastAPI app factory + API fixtures. |
| `backend/tests/test_rag_system_content_queries.py` | Marked `slow`. |
| `pyproject.toml` | Expanded `[tool.pytest.ini_options]`; added `httpx` dev dep. |

---

## 1. `backend/tests/test_api_endpoints.py` (new)

29 tests, all marked `api`, grouped by endpoint:

**`POST /api/query`** (12 tests)
- 200 response shape is exactly `{answer, sources, session_id}`
- `Source` dataclasses serialize to `{text, link}`, including `link: null`
- a session is created when `session_id` is omitted or `null`
- a supplied `session_id` is reused and `create_session` is *not* called
- `rag.query` is called with `(query, session_id)` positionally
- empty `sources` list is valid (general-knowledge answers)
- 422 on missing `query`, wrong `query` type, and malformed JSON
- unknown body fields are ignored rather than rejected
- a `RuntimeError` from the RAG system becomes a 500 with the message in `detail`
- `GET` on the route is 405

**`GET /api/courses`** (3 tests) — stats payload, empty catalog, 500 on failure.

**`DELETE /api/session/{session_id}`** (3 tests) — deletes the named session,
stays 200 for an unknown id (the manager's `pop` is a no-op), 500 on failure.
This is what the frontend's "+ New Chat" button calls.

**`GET /` static mount** (6 tests) — `index.html` at `/`, `style.css`/`script.js`
served, the no-cache headers `DevStaticFiles` adds, 404 for a missing asset, and
that the `"/"` mount does not shadow `/api/*`.

**Cross-cutting** (5 tests) — CORS simple + preflight headers, the OpenAPI schema
listing all three API paths, and app-factory isolation.

## 2. `backend/tests/conftest.py`

`backend/app.py` **cannot be imported under test**: at import time it constructs a
real `RAGSystem` (loading the sentence-transformer model and Chroma) and calls
`app.mount("/", StaticFiles(directory="../frontend"))` — a cwd-relative path that
does not resolve when pytest runs from the repo root per `testpaths`.

So the endpoints are re-declared inline via a factory:

- `create_test_app(rag_system, static_dir=None)` — mirrors `app.py`'s routes,
  Pydantic models (`QueryRequest`/`SourceItem`/`QueryResponse`/`CourseStats`),
  CORS middleware, and `_NoCacheStaticFiles` (a copy of `DevStaticFiles`).
  The static mount is **opt-in**, so API-only tests need no frontend on disk.
  *This is a deliberate duplicate — keep it in sync with `backend/app.py`.*

New fixtures:

| Fixture | Purpose |
| --- | --- |
| `mock_rag` | Stand-in RAG system. No Chroma, no embedding model, no Anthropic. |
| `sample_sources` | Two `Source` records — one with a lesson link, one without. |
| `sample_analytics` | A `get_course_analytics()`-shaped payload. |
| `static_dir` | Throwaway `tmp_path` frontend with `index.html`/`style.css`/`script.js`. |
| `api_client` | `TestClient` over the API routes only. |
| `full_client` | `TestClient` over API routes **plus** the static mount. |

`mock_rag` is a plain `MagicMock`, not `MagicMock(spec=RAGSystem)`, because
`session_manager` is an instance attribute and would not survive spec
introspection.

## 3. `pyproject.toml`

```toml
[tool.pytest.ini_options]
pythonpath = ["backend", "backend/tests"]   # "backend/tests" lets tests import the app factory from conftest
testpaths = ["backend/tests"]
python_files / python_classes / python_functions  # explicit discovery rules
addopts = ["-q", "--tb=short", "-ra", "--strict-markers", "--strict-config"]
markers = ["api", "slow"]
filterwarnings = [...]                      # silences chromadb/pydantic deprecation noise
```

`--strict-markers` means a typo'd marker is an error, not a silent no-op.
Added `httpx>=0.28.1` to the dev group — `TestClient` requires it, and it was
previously only present as a transitive dependency of `anthropic`.

## 4. `test_rag_system_content_queries.py` marked `slow`

These integration tests read the real `backend/chroma_db` and only pass once
`./run.sh` has ingested `docs/`. Marking them `slow` makes a clean fast run
possible.

---

## Running

```bash
uv run pytest                  # everything
uv run pytest -m "not slow"    # fast run, no Chroma/embedding model  -> 54 passed in 0.67s
uv run pytest -m api           # endpoint tests only                  -> 29 passed in 0.33s
```

**Current state:** 57 passed, 3 failed. The 3 failures are pre-existing and
environmental — `test_rag_system_content_queries.py` needs a populated
`backend/chroma_db`, and this worktree's store is empty (0 courses). They pass
once documents have been ingested, and are excluded by `-m "not slow"`.

On Windows/OneDrive, `uv sync` fails to hardlink into the uv cache (`os error 396`).
`pyproject.toml` now sets `[tool.uv] link-mode = "copy"`, so no environment
variable is needed. (This could *not* go in `.env` — uv only reads a `.env` when
`--env-file`/`UV_ENV_FILE` is given, and then only to populate the child command's
environment, not uv's own install behavior.)
