# Proposed Fixes for RAG Chatbot

## Fix 1: Consistent Chunk Context Formatting

### Problem
Chunks have inconsistent context prefixes - only the first chunk of each lesson gets a context prefix, and the last lesson has a different format.

### Location
File: `backend/document_processor.py`

### Fix

**Lines 182-197** - Change from:
```python
chunks = self.chunk_text(lesson_text)
for idx, chunk in enumerate(chunks):
    # For the first chunk of each lesson, add lesson context
    if idx == 0:
        chunk_with_context = f"Lesson {current_lesson} content: {chunk}"
    else:
        chunk_with_context = chunk

    course_chunk = CourseChunk(
        content=chunk_with_context,
        course_title=course.title,
        lesson_number=current_lesson,
        chunk_index=chunk_counter
    )
    course_chunks.append(course_chunk)
    chunk_counter += 1
```

**To**:
```python
chunks = self.chunk_text(lesson_text)
for idx, chunk in enumerate(chunks):
    # Add context to ALL chunks consistently
    chunk_with_context = f"Course {course_title} Lesson {current_lesson} content: {chunk}"

    course_chunk = CourseChunk(
        content=chunk_with_context,
        course_title=course.title,
        lesson_number=current_lesson,
        chunk_index=chunk_counter
    )
    course_chunks.append(course_chunk)
    chunk_counter += 1
```

**Lines 230-243** - Already correct, keep as is:
```python
chunks = self.chunk_text(lesson_text)
for idx, chunk in enumerate(chunks):
    # Context already in correct format
    chunk_with_context = f"Course {course_title} Lesson {current_lesson} content: {chunk}"

    course_chunk = CourseChunk(
        content=chunk_with_context,
        course_title=course.title,
        lesson_number=current_lesson,
        chunk_index=chunk_counter
    )
    course_chunks.append(course_chunk)
    chunk_counter += 1
```

**Impact**: After applying this fix, you'll need to rebuild the database:
```bash
cd backend
uv run python -c "
from config import config
from rag_system import RAGSystem
rag = RAGSystem(config)
rag.add_course_folder('../docs', clear_existing=True)
"
```

---

## Fix 2: Enhanced Error Logging in API Endpoint

### Problem
When errors occur, we only see "query failed" without details about what went wrong.

### Location
File: `backend/app.py`, lines 57-75

### Fix

Replace the query endpoint with enhanced error handling:

```python
@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    import traceback
    import time

    start_time = time.time()

    try:
        # Log incoming request
        print(f"[INFO] Received query: '{request.query[:100]}...' (session: {request.session_id})")

        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
            print(f"[INFO] Created new session: {session_id}")

        # Process query using RAG system
        print(f"[INFO] Processing query with RAG system...")
        answer, sources = rag_system.query(request.query, session_id)

        elapsed = time.time() - start_time
        print(f"[SUCCESS] Query completed in {elapsed:.2f}s")
        print(f"[INFO] Generated answer length: {len(answer)} chars")
        print(f"[INFO] Number of sources: {len(sources)}")

        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        elapsed = time.time() - start_time
        error_type = type(e).__name__
        error_msg = str(e)

        # Log detailed error information
        print(f"[ERROR] Query failed after {elapsed:.2f}s")
        print(f"[ERROR] Error type: {error_type}")
        print(f"[ERROR] Error message: {error_msg}")
        print(f"[ERROR] Full traceback:")
        traceback.print_exc()

        # Return detailed error to client
        raise HTTPException(
            status_code=500,
            detail=f"{error_type}: {error_msg}"
        )
```

---

## Fix 3: Better Error Handling in RAG System

### Problem
RAG system might not handle all error cases gracefully.

### Location
File: `backend/rag_system.py`, lines 106-148

### Fix

Add error handling in the query method:

```python
def query(self, query: str, session_id: Optional[str] = None) -> Tuple[str, List[str]]:
    """
    Process a user query using the RAG system with tool-based search.

    Args:
        query: User's question
        session_id: Optional session ID for conversation context

    Returns:
        Tuple of (response, sources list - empty for tool-based approach)
    """
    try:
        # Create prompt for the AI with clear instructions
        prompt = f"""Answer this question about course materials: {query}"""

        # Get conversation history if session exists
        history = None
        if session_id:
            try:
                history = self.session_manager.get_conversation_history(session_id)
            except Exception as e:
                print(f"Warning: Failed to get conversation history: {e}")
                # Continue without history

        # Generate response using AI with tools
        try:
            response = self.ai_generator.generate_response(
                query=prompt,
                conversation_history=history,
                tools=self.tool_manager.get_tool_definitions(),
                tool_manager=self.tool_manager
            )
        except Exception as e:
            print(f"Error during AI response generation: {e}")
            raise Exception(f"Failed to generate response: {str(e)}")

        # Get sources from the search tool
        try:
            sources_data = self.tool_manager.get_last_sources()
        except Exception as e:
            print(f"Warning: Failed to get sources: {e}")
            sources_data = []

        # Convert dict sources to Source model instances
        sources = []
        for src in sources_data:
            try:
                if isinstance(src, dict):
                    sources.append(Source(**src))
                else:
                    sources.append(Source(text=str(src)))
            except Exception as e:
                print(f"Warning: Failed to convert source: {e}")

        # Reset sources after retrieving them
        try:
            self.tool_manager.reset_sources()
        except Exception as e:
            print(f"Warning: Failed to reset sources: {e}")

        # Update conversation history
        if session_id:
            try:
                self.session_manager.add_exchange(session_id, query, response)
            except Exception as e:
                print(f"Warning: Failed to update conversation history: {e}")

        # Return response with sources from tool searches
        return response, sources

    except Exception as e:
        print(f"ERROR in RAG query: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        # Re-raise with more context
        raise Exception(f"RAG system query failed: {str(e)}")
```

---

## Fix 4: API Key Validation

### Problem
If API key is missing or invalid, errors might not be clear.

### Location
File: `backend/app.py`, after imports

### Fix

Add validation at startup:

```python
@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup and validate config"""

    # Validate API key
    if not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "":
        print("=" * 70)
        print("WARNING: ANTHROPIC_API_KEY is not set!")
        print("Please set ANTHROPIC_API_KEY in your .env file")
        print("=" * 70)
    else:
        print(f"✓ ANTHROPIC_API_KEY is set (length: {len(config.ANTHROPIC_API_KEY)})")

    # Load documents
    docs_path = "../docs"
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path, clear_existing=False)
            print(f"✓ Loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"✗ Error loading documents: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"⚠ Warning: docs folder not found at {docs_path}")
```

---

## Testing After Fixes

### 1. Test chunk formatting fix
```bash
cd backend
uv run python tests/inspect_db.py
# Should show all chunks have consistent "Course X Lesson Y content:" prefix
```

### 2. Test error handling
```bash
# Start the server
cd backend
uv run uvicorn app:app --reload --port 8000

# In another terminal, test with curl
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is lesson 0 about?"}'

# Check server logs for detailed error messages
```

### 3. Run all tests
```bash
cd backend
uv run pytest tests/ -v
```

---

## Summary

These fixes address:

1. **Chunk formatting consistency** - ensures all chunks have proper context
2. **Error visibility** - detailed logging shows exactly where failures occur
3. **Graceful degradation** - system continues working even if non-critical parts fail
4. **Configuration validation** - catches API key issues early

Apply fixes in order, then rebuild database and restart server.
