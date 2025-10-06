"""
Real system tests - Tests with actual database and components

This test will help identify if the issue is with the RAG system integration
or with the AI API calls.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config
from rag_system import RAGSystem
from vector_store import SearchResults


class TestRealSystem:
    """Tests with real database but mocked AI"""

    @pytest.fixture
    def rag_with_real_db_mocked_ai(self):
        """Create RAG system with real database but mocked AI generator"""
        with patch('rag_system.AIGenerator') as MockAIGenerator:
            mock_ai = Mock()
            MockAIGenerator.return_value = mock_ai

            rag = RAGSystem(config)
            rag.ai_generator = mock_ai

            yield rag

    def test_tool_search_with_real_database(self, rag_with_real_db_mocked_ai):
        """Test that search tool works with real database"""
        rag = rag_with_real_db_mocked_ai

        # Execute search tool directly
        result = rag.search_tool.execute(
            query="What is computer use?",
            course_name="Building"
        )

        # Verify we got results
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Building Towards Computer Use with Anthropic" in result or "computer use" in result.lower()

        # Verify sources were tracked
        assert len(rag.search_tool.last_sources) > 0
        print(f"\nSources tracked: {rag.search_tool.last_sources}")

    def test_tool_manager_executes_search(self, rag_with_real_db_mocked_ai):
        """Test tool manager can execute search with real database"""
        rag = rag_with_real_db_mocked_ai

        result = rag.tool_manager.execute_tool(
            "search_course_content",
            query="introduction",
            lesson_number=0
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        print(f"\nSearch result: {result[:200]}...")

    def test_tool_manager_get_sources(self, rag_with_real_db_mocked_ai):
        """Test that tool manager retrieves sources after search"""
        rag = rag_with_real_db_mocked_ai

        # Execute search first
        rag.tool_manager.execute_tool(
            "search_course_content",
            query="Python basics"
        )

        # Get sources
        sources = rag.tool_manager.get_last_sources()

        assert isinstance(sources, list)
        if len(sources) > 0:
            assert "text" in sources[0]
            print(f"\nRetrieved sources: {sources}")

    def test_query_flow_with_mocked_ai_response(self, rag_with_real_db_mocked_ai):
        """Test full query flow with mocked AI but real tools"""
        rag = rag_with_real_db_mocked_ai

        # Mock AI to NOT use tools (direct response)
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="This is a test response")]

        rag.ai_generator.generate_response.return_value = "This is a test response"

        # Execute query
        response, sources = rag.query("What is Python?")

        # Verify response
        assert response == "This is a test response"
        assert isinstance(sources, list)
        print(f"\nQuery response: {response}")
        print(f"Sources: {sources}")

    def test_query_simulating_tool_use(self, rag_with_real_db_mocked_ai):
        """
        Test query flow simulating what happens when AI uses tools.
        We'll manually trigger tool execution to see if it works.
        """
        rag = rag_with_real_db_mocked_ai

        # Simulate AI requesting tool use
        # First, execute the tool directly as AI would
        tool_result = rag.tool_manager.execute_tool(
            "search_course_content",
            query="computer use introduction"
        )

        # Verify tool executed
        assert tool_result is not None
        assert len(tool_result) > 0
        print(f"\nTool execution result: {tool_result[:300]}...")

        # Check if sources were populated
        sources = rag.tool_manager.get_last_sources()
        print(f"Sources from tool: {sources}")

        # Now mock AI response AFTER tool use
        rag.ai_generator.generate_response.return_value = "Computer use allows Claude to control computers."

        # Execute query
        response, sources = rag.query("What is computer use?")

        assert response is not None
        print(f"\nFinal response: {response}")
        print(f"Final sources: {sources}")

    def test_vector_store_search_directly(self, rag_with_real_db_mocked_ai):
        """Test vector store search directly"""
        rag = rag_with_real_db_mocked_ai

        results = rag.vector_store.search(
            query="introduction to Claude",
            limit=3
        )

        assert not results.is_empty()
        assert len(results.documents) > 0
        print(f"\nDirect vector store search returned {len(results.documents)} results")
        for i, (doc, meta) in enumerate(zip(results.documents, results.metadata)):
            print(f"\nResult {i+1}:")
            print(f"  Course: {meta.get('course_title')}")
            print(f"  Lesson: {meta.get('lesson_number')}")
            print(f"  Preview: {doc[:100]}...")

    def test_search_with_nonexistent_course(self, rag_with_real_db_mocked_ai):
        """Test search with course that doesn't exist"""
        rag = rag_with_real_db_mocked_ai

        result = rag.search_tool.execute(
            query="test query",
            course_name="Nonexistent Course XYZ"
        )

        # Should get error message about course not found
        assert "No course found" in result or "No relevant content" in result
        print(f"\nResult for nonexistent course: {result}")

    def test_outline_tool_with_real_db(self, rag_with_real_db_mocked_ai):
        """Test course outline tool with real database"""
        rag = rag_with_real_db_mocked_ai

        result = rag.tool_manager.execute_tool(
            "get_course_outline",
            course_name="Building"
        )

        assert result is not None
        assert "Building Towards Computer Use with Anthropic" in result
        assert "Lesson" in result
        print(f"\nCourse outline result:\n{result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
