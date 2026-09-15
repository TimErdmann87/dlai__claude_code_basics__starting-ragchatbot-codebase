# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) system for answering questions about course materials, using ChromaDB for vector storage, Anthropic's Claude for AI generation (via tool-calling), and a static HTML/JS frontend.

## Commands

Package management is via `uv` (not pip/poetry). Windows users run these from Git Bash.

```bash
uv sync                                     # install dependencies
```

Set `ANTHROPIC_API_KEY` in a `.env` file at the repo root (see `.env.example`).

Run the app (starts the backend and serves the frontend from the same FastAPI process):

```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

- Web UI: http://localhost:8000
- API docs: http://localhost:8000/docs

There is no test suite, linter, or build step in this repo.

## Architecture

**Request flow:** frontend (`frontend/script.js`) POSTs to `/api/query` → `app.py` → `RAGSystem.query()` (`backend/rag_system.py`) → `AIGenerator.generate_response()` (`backend/ai_generator.py`) calls Claude with the `search_course_content` tool available → Claude decides whether to invoke the tool → if it does, `ToolManager` executes `CourseSearchTool.execute()` against `VectorStore` → tool results are fed back to Claude for a final synthesized answer → sources collected from `ToolManager.get_last_sources()` are returned alongside the answer.

The key design point: retrieval is **agentic, not a fixed pipeline step**. `RAGSystem` doesn't search before calling Claude; it exposes search as a tool (see `search_tools.py`) and Claude's system prompt (`AIGenerator.SYSTEM_PROMPT`) instructs it to search only for course-specific questions, general questions are answered from Claude's own knowledge, and at most one search per query.

**Core components (`backend/`):**
- `app.py` — FastAPI app. Two endpoints: `POST /api/query` (ask a question, returns answer + sources + session_id) and `GET /api/courses` (course analytics). On startup, loads all documents from `../docs` into the vector store (skips courses already present by title). Also mounts `../frontend` as static files at `/`.
- `rag_system.py` — orchestrator (`RAGSystem`) wiring together `DocumentProcessor`, `VectorStore`, `AIGenerator`, `SessionManager`, and `ToolManager`. Entry points: `add_course_document`/`add_course_folder` (ingestion) and `query` (answering).
- `document_processor.py` — parses course documents into a `Course` + `List[CourseChunk]`. Expects a specific text format (see below), splits lesson bodies into overlapping sentence-based chunks (`CHUNK_SIZE`/`CHUNK_OVERLAP` in `config.py`), and prefixes the first chunk of each lesson with course/lesson context so embeddings retain that context even out of order.
- `vector_store.py` — wraps ChromaDB with **two collections**: `course_catalog` (one doc per course, keyed by title, used only to resolve a fuzzy `course_name` filter to an exact title via semantic search) and `course_content` (the actual chunked material, filterable by `course_title`/`lesson_number`). `VectorStore.search()` is the unified entry point: resolves course name → builds a Chroma `where` filter → queries `course_content`.
- `search_tools.py` — `Tool`/`ToolManager` abstraction for exposing search to Claude as an Anthropic tool-use tool. `CourseSearchTool` formats results with `[Course - Lesson N]` headers and tracks `last_sources` for the UI; `ToolManager.reset_sources()` is called by `RAGSystem` after each query so sources don't leak across requests.
- `ai_generator.py` — thin wrapper around the Anthropic Messages API. Single-round tool-use loop: initial call with `tools` + `tool_choice: auto` → if `stop_reason == "tool_use"`, execute the tool call(s) via `tool_manager` and make one follow-up call *without* tools to get the final text.
- `session_manager.py` — in-memory (non-persistent) per-session conversation history, truncated to `MAX_HISTORY` exchanges.
- `models.py` — Pydantic models: `Course`, `Lesson`, `CourseChunk`. `Course.title` is used as the unique ID throughout (Chroma document ID in `course_catalog`, filter key in `course_content`).
- `config.py` — central `Config` dataclass (loaded from `.env` via `python-dotenv`): model name, embedding model, chunk size/overlap, max search results, max history, Chroma path.

**Expected course document format** (see `docs/*.txt`), parsed line-by-line by `DocumentProcessor.process_course_document`:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <lesson title>
Lesson Link: <url>
<lesson body text...>

Lesson 1: <lesson title>
...
```

**Frontend (`frontend/`):** plain HTML/CSS/vanilla JS, no build step or framework. `script.js` calls `/api/query` and `/api/courses` directly and renders responses/sources into the DOM.
