"""
API Endpoint Tests

Tests for the FastAPI endpoints without importing the main app
to avoid static file mounting issues.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from typing import List

from models import Source


# ============================================================================
# Test App Creation
# ============================================================================

def create_test_app(mock_rag_system):
    """
    Create a test FastAPI app with API endpoints defined inline
    to avoid static file mounting issues from the main app.
    """
    from fastapi import HTTPException
    from pydantic import BaseModel
    from typing import Optional

    app = FastAPI(title="Test RAG System")

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Source]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # API endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        try:
            mock_rag_system.session_manager.clear_session(session_id)
            return {"status": "success", "message": f"Session {session_id} cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_app(mock_rag_system):
    """Create test FastAPI app"""
    return create_test_app(mock_rag_system)


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


# ============================================================================
# POST /api/query Tests
# ============================================================================

@pytest.mark.api
class TestQueryEndpoint:
    """Tests for the /api/query endpoint"""

    def test_query_without_session_id(self, client, mock_rag_system, sample_sources):
        """Test query endpoint without providing session_id"""
        # Setup mock
        mock_rag_system.session_manager.create_session.return_value = "new-session-123"
        mock_rag_system.query.return_value = ("Test answer", sample_sources)

        # Make request
        response = client.post(
            "/api/query",
            json={"query": "What is lesson 1 about?"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        assert data["answer"] == "Test answer"
        assert data["session_id"] == "new-session-123"
        assert len(data["sources"]) == 2

        # Verify mock was called correctly
        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with("What is lesson 1 about?", "new-session-123")

    def test_query_with_session_id(self, client, mock_rag_system, sample_sources):
        """Test query endpoint with existing session_id"""
        # Setup mock
        mock_rag_system.query.return_value = ("Test answer", sample_sources)

        # Make request
        response = client.post(
            "/api/query",
            json={
                "query": "What is lesson 2 about?",
                "session_id": "existing-session"
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "Test answer"
        assert data["session_id"] == "existing-session"
        assert len(data["sources"]) == 2

        # Verify session was not created
        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with("What is lesson 2 about?", "existing-session")

    def test_query_with_empty_sources(self, client, mock_rag_system):
        """Test query that returns no sources"""
        # Setup mock - no sources returned
        mock_rag_system.query.return_value = ("This is general knowledge.", [])
        mock_rag_system.session_manager.create_session.return_value = "session-456"

        # Make request
        response = client.post(
            "/api/query",
            json={"query": "What is 2 + 2?"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "This is general knowledge."
        assert len(data["sources"]) == 0

    def test_query_missing_query_field(self, client):
        """Test query endpoint with missing query field"""
        response = client.post(
            "/api/query",
            json={"session_id": "test"}
        )

        # Should return validation error
        assert response.status_code == 422

    def test_query_empty_query_string(self, client, mock_rag_system):
        """Test query endpoint with empty query string"""
        mock_rag_system.session_manager.create_session.return_value = "session-789"
        mock_rag_system.query.return_value = ("Please provide a query.", [])

        response = client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still accept empty string (validation happens in RAG system)
        assert response.status_code == 200

    def test_query_internal_error(self, client, mock_rag_system):
        """Test query endpoint when RAG system raises exception"""
        mock_rag_system.session_manager.create_session.return_value = "session-error"
        mock_rag_system.query.side_effect = Exception("Internal error occurred")

        response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        # Should return 500 error
        assert response.status_code == 500
        assert "Internal error occurred" in response.json()["detail"]

    def test_query_long_text(self, client, mock_rag_system, sample_sources):
        """Test query with very long query text"""
        long_query = "What is " + "very " * 100 + "long query?"

        mock_rag_system.session_manager.create_session.return_value = "session-long"
        mock_rag_system.query.return_value = ("This is the answer.", sample_sources)

        response = client.post(
            "/api/query",
            json={"query": long_query}
        )

        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with(long_query, "session-long")


# ============================================================================
# GET /api/courses Tests
# ============================================================================

@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for the /api/courses endpoint"""

    def test_get_courses_success(self, client, mock_rag_system):
        """Test successful course stats retrieval"""
        # Setup mock
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Python Basics", "JavaScript Course", "React Tutorial"]
        }

        # Make request
        response = client.get("/api/courses")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3
        assert "Python Basics" in data["course_titles"]

        # Verify mock was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_empty_database(self, client, mock_rag_system):
        """Test course stats when no courses exist"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert len(data["course_titles"]) == 0

    def test_get_courses_internal_error(self, client, mock_rag_system):
        """Test course stats endpoint when system raises exception"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Database error")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


# ============================================================================
# DELETE /api/session/{session_id} Tests
# ============================================================================

@pytest.mark.api
class TestSessionEndpoint:
    """Tests for the /api/session endpoint"""

    def test_clear_session_success(self, client, mock_rag_system):
        """Test successful session clearing"""
        response = client.delete("/api/session/test-session-123")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "test-session-123" in data["message"]

        # Verify mock was called
        mock_rag_system.session_manager.clear_session.assert_called_once_with("test-session-123")

    def test_clear_nonexistent_session(self, client, mock_rag_system):
        """Test clearing a session that doesn't exist"""
        # Session manager should handle this gracefully
        mock_rag_system.session_manager.clear_session.return_value = None

        response = client.delete("/api/session/nonexistent-session")

        assert response.status_code == 200

    def test_clear_session_with_special_characters(self, client, mock_rag_system):
        """Test clearing session with special characters in ID"""
        session_id = "session-with-special!@#$%"

        response = client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        mock_rag_system.session_manager.clear_session.assert_called_once_with(session_id)

    def test_clear_session_internal_error(self, client, mock_rag_system):
        """Test session clearing when error occurs"""
        mock_rag_system.session_manager.clear_session.side_effect = Exception("Session error")

        response = client.delete("/api/session/error-session")

        assert response.status_code == 500
        assert "Session error" in response.json()["detail"]


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for multiple API calls"""

    def test_query_then_clear_session(self, client, mock_rag_system, sample_sources):
        """Test querying and then clearing the session"""
        # Setup mocks
        session_id = "integration-session"
        mock_rag_system.session_manager.create_session.return_value = session_id
        mock_rag_system.query.return_value = ("Answer", sample_sources)

        # First query
        response1 = client.post(
            "/api/query",
            json={"query": "First query"}
        )
        assert response1.status_code == 200
        returned_session_id = response1.json()["session_id"]

        # Second query with same session
        response2 = client.post(
            "/api/query",
            json={"query": "Second query", "session_id": returned_session_id}
        )
        assert response2.status_code == 200

        # Clear session
        response3 = client.delete(f"/api/session/{returned_session_id}")
        assert response3.status_code == 200

        # Verify both queries used same session
        assert mock_rag_system.query.call_count == 2

    def test_multiple_queries_different_sessions(self, client, mock_rag_system, sample_sources):
        """Test multiple queries with different sessions"""
        mock_rag_system.query.return_value = ("Answer", sample_sources)

        # Create three different sessions
        mock_rag_system.session_manager.create_session.side_effect = [
            "session-1",
            "session-2",
            "session-3"
        ]

        responses = []
        for i in range(3):
            response = client.post(
                "/api/query",
                json={"query": f"Query {i}"}
            )
            assert response.status_code == 200
            responses.append(response.json())

        # Verify all have different session IDs
        session_ids = [r["session_id"] for r in responses]
        assert len(set(session_ids)) == 3

    def test_get_courses_between_queries(self, client, mock_rag_system, sample_sources):
        """Test getting course stats between queries"""
        mock_rag_system.session_manager.create_session.return_value = "session-mix"
        mock_rag_system.query.return_value = ("Answer", sample_sources)
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course A", "Course B"]
        }

        # Query
        response1 = client.post("/api/query", json={"query": "Query 1"})
        assert response1.status_code == 200

        # Get courses
        response2 = client.get("/api/courses")
        assert response2.status_code == 200
        assert response2.json()["total_courses"] == 2

        # Another query
        response3 = client.post("/api/query", json={"query": "Query 2"})
        assert response3.status_code == 200


# ============================================================================
# Response Schema Tests
# ============================================================================

@pytest.mark.api
class TestResponseSchemas:
    """Tests to verify API response schemas match expected format"""

    def test_query_response_schema(self, client, mock_rag_system, sample_sources):
        """Verify query response has correct schema"""
        mock_rag_system.session_manager.create_session.return_value = "test-session"
        mock_rag_system.query.return_value = ("Test answer", sample_sources)

        response = client.post(
            "/api/query",
            json={"query": "Test"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Check types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Check source structure
        if len(data["sources"]) > 0:
            source = data["sources"][0]
            assert "text" in source
            assert "url" in source

    def test_courses_response_schema(self, client, mock_rag_system):
        """Verify courses response has correct schema"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Test Course"]
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "total_courses" in data
        assert "course_titles" in data

        # Check types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

    def test_session_delete_response_schema(self, client, mock_rag_system):
        """Verify session delete response has correct schema"""
        response = client.delete("/api/session/test")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "status" in data
        assert "message" in data

        # Check types
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "api"])
