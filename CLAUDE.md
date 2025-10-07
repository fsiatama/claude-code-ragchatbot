# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) chatbot that answers questions about course materials using semantic search with ChromaDB and Anthropic's Claude API. The system uses **tool-based RAG** where Claude decides when to search (not automatic retrieval).

**Tech Stack:** Python 3.13+, FastAPI, ChromaDB, Anthropic Claude API, Sentence Transformers, vanilla JS frontend

**Important:** This project uses `uv` as the Python package manager. Always use `uv run` to execute Python commands—never use `pip` directly.

## Running the Application

### Quick Start
```bash
./run.sh
```
This creates the `docs/` directory, starts the backend server on port 8000, and serves the frontend.

### Manual Start
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

**Access:**
- Web UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### Environment Setup
Create `.env` in the root directory:
```
ANTHROPIC_API_KEY=your_key_here
```

### Installing Dependencies
```bash
uv sync
```

## Code Quality Tools

This project uses automated code quality tools to maintain consistency and catch issues early.

**Tools:**
- **Black**: Automatic code formatting (88 character line length)
- **Ruff**: Fast Python linter with import sorting
- **Mypy**: Static type checker

**Configuration:** All tools are configured in `pyproject.toml`

### Running Quality Checks

**Format code:**
```bash
# Linux/Mac
./scripts/format.sh

# Windows
scripts\format.bat
```

**Check linting:**
```bash
# Linux/Mac
./scripts/lint.sh

# Windows
scripts\lint.bat
```

**Run type checking:**
```bash
# Linux/Mac
./scripts/typecheck.sh

# Windows
scripts\typecheck.bat
```

**Run all checks:**
```bash
# Linux/Mac
./scripts/check-all.sh

# Windows
scripts\check-all.bat
```

**Best Practice:** Run `./scripts/format.sh` before committing code. The formatter automatically fixes most style issues.

## Architecture

### RAG System Flow (Tool-Based)

1. **User Query** → FastAPI endpoint (`/api/query`)
2. **RAG System** → Orchestrates the process, manages session history
3. **AI Generator** → Calls Claude API with tool definitions
4. **Claude Decision** → Decides whether to use `search_course_content` tool
5. **Tool Execution** (if needed) → CourseSearchTool queries vector store
6. **Vector Store** → Two-tier search:
   - **course_catalog** collection: Fuzzy course name matching (resolves "Python" → "Python Basics Course")
   - **course_content** collection: Semantic search on chunks with filters
7. **Second Claude Call** → Receives tool results, generates final answer
8. **Response** → Returns answer + sources to frontend

**Key Point:** Claude uses tools via Anthropic's tool calling API. The search is NOT automatic—Claude decides when to search based on the query.

### Core Components

**backend/rag_system.py** - Main orchestrator
- Coordinates document_processor, vector_store, ai_generator, session_manager, and tool_manager
- `add_course_folder()`: Processes documents from `docs/` directory
- `query()`: Handles user queries with conversation history

**backend/ai_generator.py** - Claude API integration
- `generate_response()`: Makes API calls with optional tools
- `_handle_tool_execution()`: Two-round trip for tool use (request → results → final answer)
- System prompt emphasizes brief, focused responses and proper tool usage

**backend/vector_store.py** - ChromaDB wrapper
- **Two collections:**
  - `course_catalog`: Course metadata (titles, instructors, lesson summaries) for fuzzy matching
  - `course_content`: Text chunks with embeddings for semantic search
- `search()`: Unified interface with course name resolution
- `_resolve_course_name()`: Semantic search to match partial course names

**backend/search_tools.py** - Tool system
- `CourseSearchTool`: Implements search with optional `course_name` and `lesson_number` filters
- `ToolManager`: Registers tools and provides definitions to Claude API
- Tracks sources (`last_sources`) for UI display

**backend/document_processor.py** - Document parsing
- Expects structured format: `Course Title:`, `Course Link:`, `Course Instructor:`, then `Lesson N:` markers
- `chunk_text()`: Sentence-based chunking with overlap
- Adds context to chunks: `"Course [title] Lesson [N] content: [text]"`

**backend/session_manager.py** - Conversation history
- Maintains last N exchanges per session (configured via `MAX_HISTORY`)
- Formatted history passed to Claude for context

**backend/config.py** - Configuration
- `CHUNK_SIZE`: 800 characters
- `CHUNK_OVERLAP`: 100 characters
- `MAX_RESULTS`: 5 search results
- `MAX_HISTORY`: 2 conversation exchanges
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (Sentence Transformers)

### Document Processing

**Expected Format:**
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: [title]
Lesson Link: [url]
[lesson content]

Lesson 1: [title]
...
```

**Processing Steps:**
1. Parse metadata (first 3 lines)
2. Split content by `Lesson N:` markers
3. Chunk each lesson's content with sentence-aware splitting
4. Prefix chunks with context for better retrieval
5. Store in ChromaDB with metadata (course_title, lesson_number, chunk_index)

**Adding Documents:**
- Place `.txt`, `.pdf`, or `.docx` files in `docs/` directory
- Restart server (documents loaded on startup via `app.py:startup_event`)
- Duplicate detection by course title (skips re-processing)

## Key Implementation Details

### Two-Tier Search Strategy
The vector store uses separate collections for different purposes:
- **Fuzzy course matching**: Query "Python" in `course_catalog` → resolves to exact title "Python Basics Course"
- **Content search**: Use resolved title + lesson filters to query `course_content` collection

This enables natural queries like "What does lesson 1 in the Python course teach?" where "Python" needs fuzzy matching.

### Tool Execution Flow
When Claude decides to use a tool:
1. Initial API call returns `stop_reason: "tool_use"` with tool parameters
2. `_handle_tool_execution()` extracts tool calls and executes via `ToolManager`
3. Tool results appended to conversation as user message
4. Second API call (without tools) generates final response

### Session Management
- Sessions created on first query (if no `session_id` provided)
- History limited to `MAX_HISTORY * 2` messages (pairs of user/assistant)
- History formatted as "User: [msg]\nAssistant: [msg]" and included in system prompt

### Source Tracking
- `CourseSearchTool` stores sources in `last_sources` during execution
- `ToolManager.get_last_sources()` retrieves for API response
- `ToolManager.reset_sources()` clears after each query
- Frontend displays sources in collapsible section

## Database Persistence

ChromaDB data stored in `backend/chroma_db/` directory (persists between restarts). To rebuild:

```bash
cd backend
uv run python -c "
from config import config
from rag_system import RAGSystem
rag = RAGSystem(config)
rag.add_course_folder('../docs', clear_existing=True)
"
```

**Important:** Always use `uv run python` or `uv run [command]` to execute Python code. Never use `pip` or direct Python commands—`uv` manages the virtual environment and dependencies.

## Configuration Tuning

Edit `backend/config.py` to adjust:
- **CHUNK_SIZE/CHUNK_OVERLAP**: Affects retrieval granularity (larger = more context per chunk)
- **MAX_RESULTS**: Number of chunks returned to Claude (more = better context but higher tokens)
- **MAX_HISTORY**: Conversation memory (more = better continuity but higher tokens)
- **ANTHROPIC_MODEL**: Change Claude model version

## Frontend API Integration

**POST /api/query**
```javascript
{
  query: "What is lesson 1 about?",
  session_id: "session_1" // optional
}
```

**Response:**
```javascript
{
  answer: "Lesson 1 covers...",
  sources: ["Course Title - Lesson 1"],
  session_id: "session_1"
}
```

**GET /api/courses** - Returns course statistics (total count, titles)

## Windows Development Note

The README specifies using **Git Bash** for Windows users to run shell commands (`run.sh`). The `uv` package manager should work in PowerShell/CMD as well for direct Python commands.
- always use uv to run the server do not use pip directly
- make sure to use uv to manage all dependencies
- use uv to run Python files
- dont run the server using ./run.sh I will start it myself