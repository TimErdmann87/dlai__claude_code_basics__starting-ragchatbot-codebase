"""Shared fixtures for the backend diagnostic test suite."""

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ai_generator import AIGenerator
from rag_system import RAGSystem
from search_tools import ToolManager
from vector_store import SearchResults, VectorStore

# ---------------------------------------------------------------------------
# Objective 1 helpers: CourseSearchTool / ToolManager unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vector_store():
    """A fully mocked VectorStore -- no real Chroma, no network, no disk I/O."""
    return MagicMock(spec=VectorStore)


@pytest.fixture
def make_results():
    """Factory for building SearchResults without boilerplate."""

    def _make(documents=None, metadata=None, distances=None, error=None):
        return SearchResults(
            documents=documents or [],
            metadata=metadata or [],
            distances=distances or [],
            error=error,
        )

    return _make


# ---------------------------------------------------------------------------
# Objective 2 helpers: AIGenerator unit tests (Anthropic client mocked)
# ---------------------------------------------------------------------------


@pytest.fixture
def ai_generator():
    """A real AIGenerator with its Anthropic client's create() call mocked out."""
    generator = AIGenerator(api_key="test-key-not-used", model="claude-sonnet-5")
    generator.client.messages.create = MagicMock()
    return generator


@pytest.fixture
def mock_tool_manager():
    return MagicMock(spec=ToolManager)


@pytest.fixture
def text_response():
    """Build a fake Anthropic response whose content is a single text block."""

    def _make(text, stop_reason="end_turn"):
        return SimpleNamespace(
            stop_reason=stop_reason,
            content=[SimpleNamespace(type="text", text=text)],
        )

    return _make


@pytest.fixture
def tool_use_response():
    """
    Build a fake Anthropic response containing one or more tool_use blocks.
    tool_calls: list of {"name": str, "input": dict, "id": optional str}
    """

    def _make(tool_calls, stop_reason="tool_use"):
        blocks = [
            SimpleNamespace(
                type="tool_use",
                name=call["name"],
                input=call["input"],
                id=call.get("id", f"toolu_{i}"),
            )
            for i, call in enumerate(tool_calls)
        ]
        return SimpleNamespace(stop_reason=stop_reason, content=blocks)

    return _make


# ---------------------------------------------------------------------------
# Objective 3 helpers: real VectorStore + real ToolManager, scripted Anthropic
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent.parent
REAL_CHROMA_PATH = str(BACKEND_DIR / "chroma_db")


@dataclass
class _TestConfig:
    """
    Mirrors config.Config but with an absolute CHROMA_PATH, so this works
    regardless of the cwd pytest is invoked from (config.Config's default
    './chroma_db' is relative and assumes cwd == backend/, which is NOT
    true when pytest runs from the repo root per testpaths=['backend/tests']).
    """

    ANTHROPIC_API_KEY: str = "test-key-not-used"
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = REAL_CHROMA_PATH


@pytest.fixture(scope="session")
def rag_system():
    """
    A RAGSystem wired to the REAL, already-populated backend/chroma_db,
    with real VectorStore/ToolManager/CourseSearchTool/CourseOutlineTool.
    Session-scoped because constructing VectorStore loads the sentence-
    transformer embedding model, which is slow. Never make a live Anthropic
    call from this fixture -- see _isolate_rag_system below.
    """
    return RAGSystem(_TestConfig())


@pytest.fixture(autouse=True)
def _isolate_rag_system(request):
    """
    Give every test that uses `rag_system` a clean slate: no leftover
    session history, no leftover tool sources, and a fresh mock in place
    of the real Anthropic client so no live network call ever happens.
    """
    if "rag_system" in request.fixturenames:
        rag = request.getfixturevalue("rag_system")
        rag.session_manager.sessions.clear()
        rag.tool_manager.reset_sources()
        rag.ai_generator.client.messages.create = MagicMock()
    yield
