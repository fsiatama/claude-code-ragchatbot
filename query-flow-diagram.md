# RAG System Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND                                     │
│                            (frontend/script.js)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ 1. User Query
                                     │ POST /api/query
                                     │ { query: "What is lesson 1?",
                                     │   session_id: "abc123" }
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI ENDPOINT                                │
│                              (backend/app.py)                                │
│                                                                              │
│  @app.post("/api/query")                                                    │
│  async def query_documents(request)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ 2. Route to RAG System
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RAG SYSTEM                                      │
│                          (backend/rag_system.py)                            │
│                                                                              │
│  def query(query, session_id):                                              │
│    ├─► Get conversation history ────────────┐                              │
│    │                                          │                              │
│    └─► Generate AI response with tools       │                              │
└──────────────────────────────────────────────┼──────────────────────────────┘
                    │                           │
                    │                           ▼
                    │            ┌─────────────────────────────┐
                    │            │    SESSION MANAGER          │
                    │            │ (session_manager.py)        │
                    │            │                             │
                    │            │ • Get conversation history  │
                    │            │ • Store exchanges           │
                    │            └─────────────────────────────┘
                    │
                    │ 3. Call AI Generator
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AI GENERATOR                                      │
│                        (backend/ai_generator.py)                            │
│                                                                              │
│  def generate_response(query, history, tools, tool_manager):               │
│    ├─► Call Claude API with tools                                          │
│    │                                                                         │
│    └─► If stop_reason == "tool_use":                                       │
│          └─► Execute tool & get final response                             │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                           │
                    │ 4a. Initial Response      │ 4b. Tool Execution
                    │     (no tool use)         │
                    │                           ▼
                    │            ┌─────────────────────────────────────────┐
                    │            │       ANTHROPIC CLAUDE API              │
                    │            │                                         │
                    │            │  System Prompt: "Use search tool for   │
                    │            │   course-specific questions..."        │
                    │            │                                         │
                    │            │  Tools Available:                       │
                    │            │  - search_course_content()             │
                    │            │                                         │
                    │            │  Response: {                            │
                    │            │    stop_reason: "tool_use",            │
                    │            │    content: [{                          │
                    │            │      type: "tool_use",                 │
                    │            │      name: "search_course_content",    │
                    │            │      input: {                           │
                    │            │        query: "lesson 1 content",      │
                    │            │        course_name: "Python"           │
                    │            │      }                                  │
                    │            │    }]                                   │
                    │            │  }                                      │
                    │            └─────────────────────────────────────────┘
                    │                           │
                    │                           │ 5. Execute Tool
                    │                           ▼
                    │            ┌─────────────────────────────────────────┐
                    │            │         TOOL MANAGER                    │
                    │            │     (backend/search_tools.py)           │
                    │            │                                         │
                    │            │  def execute_tool(name, **kwargs):     │
                    │            │    ├─► Route to CourseSearchTool       │
                    │            │    └─► Track sources                   │
                    │            └─────────────────────────────────────────┘
                    │                           │
                    │                           │ 6. Search Content
                    │                           ▼
                    │            ┌─────────────────────────────────────────┐
                    │            │      COURSE SEARCH TOOL                 │
                    │            │     (backend/search_tools.py)           │
                    │            │                                         │
                    │            │  def execute(query, course_name,       │
                    │            │              lesson_number):            │
                    │            │    ├─► Call vector_store.search()      │
                    │            │    ├─► Format results                  │
                    │            │    └─► Store sources in last_sources   │
                    │            └─────────────────────────────────────────┘
                    │                           │
                    │                           │ 7. Vector Search
                    │                           ▼
                    │            ┌─────────────────────────────────────────┐
                    │            │         VECTOR STORE                    │
                    │            │     (backend/vector_store.py)           │
                    │            │                                         │
                    │            │  def search(query, course_name,        │
                    │            │             lesson_number):             │
                    │            │                                         │
                    │            │  Step 1: Resolve Course Name           │
                    │            │  ┌───────────────────────────────┐    │
                    │            │  │  course_catalog.query(         │    │
                    │            │  │    "Python"                    │    │
                    │            │  │  )                             │    │
                    │            │  │  Returns: "Python Basics"      │    │
                    │            │  └───────────────────────────────┘    │
                    │            │                                         │
                    │            │  Step 2: Build Filter                  │
                    │            │  ┌───────────────────────────────┐    │
                    │            │  │  {                             │    │
                    │            │  │    course_title: "Python..."   │    │
                    │            │  │    lesson_number: 1            │    │
                    │            │  │  }                             │    │
                    │            │  └───────────────────────────────┘    │
                    │            │                                         │
                    │            │  Step 3: Semantic Search               │
                    │            │  ┌───────────────────────────────┐    │
                    │            │  │  course_content.query(         │    │
                    │            │  │    query_texts=["lesson 1"],   │    │
                    │            │  │    n_results=5,                │    │
                    │            │  │    where=filter_dict           │    │
                    │            │  │  )                             │    │
                    │            │  └───────────────────────────────┘    │
                    │            └─────────────────────────────────────────┘
                    │                           │
                    │                           │ 8. Return Results
                    │                           │
                    │            ┌──────────────▼──────────────────────────┐
                    │            │      CHROMADB                           │
                    │            │                                         │
                    │            │  Collections:                           │
                    │            │  ┌────────────────────────────────┐   │
                    │            │  │ course_catalog                 │   │
                    │            │  │ - Course titles (metadata)     │   │
                    │            │  │ - Instructor info              │   │
                    │            │  │ - Lesson summaries             │   │
                    │            │  └────────────────────────────────┘   │
                    │            │                                         │
                    │            │  ┌────────────────────────────────┐   │
                    │            │  │ course_content                 │   │
                    │            │  │ - Text chunks with embeddings  │   │
                    │            │  │ - Course + lesson metadata     │   │
                    │            │  │ - Chunk indices                │   │
                    │            │  └────────────────────────────────┘   │
                    │            │                                         │
                    │            │  Returns: SearchResults                │
                    │            │  {                                      │
                    │            │    documents: ["Lesson 1 teaches..."], │
                    │            │    metadata: [{course_title: "...",    │
                    │            │                lesson_number: 1}],     │
                    │            │    distances: [0.23]                   │
                    │            │  }                                      │
                    │            └─────────────────────────────────────────┘
                    │                           │
                    │                           │ 9. Tool Results
                    │                           │ "[Python Basics - Lesson 1]
                    │                           │  Lesson 1 teaches..."
                    │                           │
                    │            ┌──────────────▼──────────────────────────┐
                    │            │    BACK TO CLAUDE API                   │
                    │            │                                         │
                    │            │  messages: [                            │
                    │            │    {role: "assistant",                  │
                    │            │     content: tool_use_request},         │
                    │            │    {role: "user",                       │
                    │            │     content: tool_results}              │
                    │            │  ]                                      │
                    │            │                                         │
                    │            │  Returns: "Lesson 1 covers Python      │
                    │            │            basics including..."         │
                    │            └─────────────────────────────────────────┘
                    │                           │
                    │ 10. Final Response        │
                    │ (with tool results)       │
                    ◄───────────────────────────┘
                    │
                    │ 11. Extract Sources & Update Session
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACK TO RAG SYSTEM                                  │
│                                                                              │
│  sources = tool_manager.get_last_sources()                                  │
│  # ["Python Basics - Lesson 1"]                                            │
│                                                                              │
│  session_manager.add_exchange(session_id, query, response)                 │
│                                                                              │
│  return (response, sources)                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ 12. Return to API
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI RESPONSE                                │
│                                                                              │
│  return QueryResponse(                                                      │
│    answer: "Lesson 1 covers Python basics...",                             │
│    sources: ["Python Basics - Lesson 1"],                                  │
│    session_id: "abc123"                                                     │
│  )                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ 13. JSON Response
                                     │ {
                                     │   "answer": "...",
                                     │   "sources": [...],
                                     │   "session_id": "abc123"
                                     │ }
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND DISPLAY                                   │
│                                                                              │
│  • Display answer with markdown rendering                                   │
│  • Show collapsible sources section                                         │
│  • Update conversation history UI                                           │
│  • Store session_id for next query                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Flow Points

1. **Frontend** → User types query, sends POST request with session_id
2. **FastAPI** → Routes to RAG system orchestrator
3. **RAG System** → Gets history, calls AI generator with tools
4. **AI Generator** → Sends query to Claude with tool definitions
5. **Claude API** → Decides to use `search_course_content` tool
6. **Tool Manager** → Executes CourseSearchTool
7. **Vector Store** → Resolves course name + filters + semantic search
8. **ChromaDB** → Returns relevant chunks with metadata
9. **Tool Results** → Sent back to Claude for final answer generation
10. **Claude API** → Generates natural language response
11. **RAG System** → Extracts sources, updates session history
12. **FastAPI** → Returns JSON with answer + sources
13. **Frontend** → Displays formatted response to user

## Data Flow Summary

```
User Query → API → RAG System → AI Generator → Claude API
                                                    ↓
                                              (tool_use?)
                                                    ↓
                                            Tool Manager
                                                    ↓
                                          CourseSearchTool
                                                    ↓
                                            Vector Store
                                                    ↓
                                              ChromaDB
                                                    ↓
                                          Search Results
                                                    ↓
                                Claude API (with context) → Final Answer
                                                    ↓
                                            RAG System (+ sources)
                                                    ↓
                                              API Response
                                                    ↓
                                            Frontend Display
```
