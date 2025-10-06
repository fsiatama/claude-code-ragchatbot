"""
Integration tests for RAG System

Tests the complete flow from query to response:
- Full RAG query flow with real/mock components
- Tool manager integration
- Source tracking
- Session management integration
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from rag_system import RAGSystem
from models import Source
from config import Config


class TestRAGSystemIntegration:
    """Integration test suite for RAG System"""

    @pytest.fixture
    def mock_config(self):
        """Create a test configuration"""
        config = Config()
        config.ANTHROPIC_API_KEY = "test-api-key"
        config.ANTHROPIC_MODEL = "test-model"
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 2
        config.CHROMA_PATH = "./test_chroma_db"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        return config

    @pytest.fixture
    def rag_system_with_mocks(self, mock_config):
        """Create a RAG system with mocked components"""
        with patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager') as MockSessionManager, \
             patch('rag_system.DocumentProcessor') as MockDocumentProcessor:

            # Setup mocks
            mock_vector_store = Mock()
            mock_ai_generator = Mock()
            mock_session_manager = Mock()
            mock_document_processor = Mock()

            MockVectorStore.return_value = mock_vector_store
            MockAIGenerator.return_value = mock_ai_generator
            MockSessionManager.return_value = mock_session_manager
            MockDocumentProcessor.return_value = mock_document_processor

            rag = RAGSystem(mock_config)

            # Attach mocks for testing
            rag.vector_store = mock_vector_store
            rag.ai_generator = mock_ai_generator
            rag.session_manager = mock_session_manager

            return rag

    def test_query_basic_flow_without_session(self, rag_system_with_mocks):
        """Test basic query flow without session history"""
        rag = rag_system_with_mocks

        # Setup mocks
        rag.session_manager.get_conversation_history.return_value = None
        rag.ai_generator.generate_response.return_value = "This is the answer about Python"
        rag.tool_manager.get_last_sources.return_value = [
            {"text": "Python Course - Lesson 1", "url": "https://example.com/lesson1"}
        ]

        # Execute query
        response, sources = rag.query("What is Python?", session_id=None)

        # Verify
        assert response == "This is the answer about Python"
        assert len(sources) == 1
        assert sources[0].text == "Python Course - Lesson 1"
        assert sources[0].url == "https://example.com/lesson1"

        # Verify AI generator was called correctly
        rag.ai_generator.generate_response.assert_called_once()
        call_args = rag.ai_generator.generate_response.call_args[1]
        assert "What is Python?" in call_args["query"]
        assert call_args["conversation_history"] is None
        assert call_args["tools"] is not None
        assert call_args["tool_manager"] is not None

    def test_query_with_session_history(self, rag_system_with_mocks):
        """Test query with conversation history from session"""
        rag = rag_system_with_mocks

        # Setup mocks
        history = "User: What is Python?\nAssistant: Python is a programming language."
        rag.session_manager.get_conversation_history.return_value = history
        rag.ai_generator.generate_response.return_value = "Python is used for web development"
        rag.tool_manager.get_last_sources.return_value = []

        # Execute query
        response, sources = rag.query("What is it used for?", session_id="session_123")

        # Verify history was used
        rag.session_manager.get_conversation_history.assert_called_once_with("session_123")
        call_args = rag.ai_generator.generate_response.call_args[1]
        assert call_args["conversation_history"] == history

        # Verify session was updated
        rag.session_manager.add_exchange.assert_called_once_with(
            "session_123",
            "What is it used for?",
            "Python is used for web development"
        )

    def test_query_updates_session_history(self, rag_system_with_mocks):
        """Test that query updates session history after response"""
        rag = rag_system_with_mocks

        rag.session_manager.get_conversation_history.return_value = None
        rag.ai_generator.generate_response.return_value = "Answer"
        rag.tool_manager.get_last_sources.return_value = []

        query_text = "Test question"
        response, sources = rag.query(query_text, session_id="session_456")

        # Verify session was updated with query and response
        rag.session_manager.add_exchange.assert_called_once_with(
            "session_456",
            query_text,
            "Answer"
        )

    def test_query_passes_tools_to_ai_generator(self, rag_system_with_mocks):
        """Test that tool definitions are passed to AI generator"""
        rag = rag_system_with_mocks

        rag.session_manager.get_conversation_history.return_value = None
        rag.ai_generator.generate_response.return_value = "Response"
        rag.tool_manager.get_last_sources.return_value = []

        response, sources = rag.query("Test query")

        # Verify tools were passed
        call_args = rag.ai_generator.generate_response.call_args[1]
        assert call_args["tools"] is not None
        assert call_args["tool_manager"] is not None

    def test_query_sources_are_tracked_and_reset(self, rag_system_with_mocks):
        """Test that sources are retrieved and then reset"""
        rag = rag_system_with_mocks

        rag.session_manager.get_conversation_history.return_value = None
        rag.ai_generator.generate_response.return_value = "Response"
        rag.tool_manager.get_last_sources.return_value = [
            {"text": "Course A", "url": "http://example.com"}
        ]

        response, sources = rag.query("Test")

        # Verify sources were retrieved
        rag.tool_manager.get_last_sources.assert_called_once()

        # Verify sources were reset after retrieval
        rag.tool_manager.reset_sources.assert_called_once()

    def test_query_converts_dict_sources_to_source_objects(self, rag_system_with_mocks):
        """Test that dictionary sources are converted to Source model objects"""
        rag = rag_system_with_mocks

        rag.session_manager.get_conversation_history.return_value = None
        rag.ai_generator.generate_response.return_value = "Response"
        rag.tool_manager.get_last_sources.return_value = [
            {"text": "Course", "url": "http://example.com"},
            {"text": "Course 2", "url": None}
        ]

        response, sources = rag.query("Test")

        # Verify sources are Source objects
        assert len(sources) == 2
        assert isinstance(sources[0], Source)
        assert isinstance(sources[1], Source)
        assert sources[0].text == "Course"
        assert sources[0].url == "http://example.com"
        assert sources[1].text == "Course 2"
        assert sources[1].url is None

    def test_query_handles_string_sources(self, rag_system_with_mocks):
        """Test that string sources are converted to Source objects"""
        rag = rag_system_with_mocks

        rag.session_manager.get_conversation_history.return_value = None
        rag.ai_generator.generate_response.return_value = "Response"
        rag.tool_manager.get_last_sources.return_value = ["String source"]

        response, sources = rag.query("Test")

        assert len(sources) == 1
        assert isinstance(sources[0], Source)
        assert sources[0].text == "String source"

    def test_query_prompt_format(self, rag_system_with_mocks):
        """Test that query is formatted correctly in prompt"""
        rag = rag_system_with_mocks

        rag.session_manager.get_conversation_history.return_value = None
        rag.ai_generator.generate_response.return_value = "Response"
        rag.tool_manager.get_last_sources.return_value = []

        response, sources = rag.query("What are the lessons in Python course?")

        call_args = rag.ai_generator.generate_response.call_args[1]
        query_arg = call_args["query"]

        # Verify query contains the instruction and question
        assert "What are the lessons in Python course?" in query_arg
        assert "Answer this question about course materials:" in query_arg

    def test_tool_manager_registers_tools(self, mock_config):
        """Test that tool manager has tools registered"""
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.DocumentProcessor'):

            rag = RAGSystem(mock_config)

            # Verify tools are registered
            tool_definitions = rag.tool_manager.get_tool_definitions()
            assert len(tool_definitions) >= 2  # At least search and outline tools

            # Verify search tool is registered
            tool_names = [tool["name"] for tool in tool_definitions]
            assert "search_course_content" in tool_names
            assert "get_course_outline" in tool_names

    def test_search_tool_uses_vector_store(self, rag_system_with_mocks):
        """Test that search tool is properly connected to vector store"""
        rag = rag_system_with_mocks

        # Verify search tool has access to vector store
        assert rag.search_tool.store == rag.vector_store

    def test_outline_tool_uses_vector_store(self, rag_system_with_mocks):
        """Test that outline tool is properly connected to vector store"""
        rag = rag_system_with_mocks

        # Verify outline tool has access to vector store
        assert rag.outline_tool.store == rag.vector_store

    def test_query_without_session_doesnt_call_session_methods(self, rag_system_with_mocks):
        """Test that without session_id, session methods aren't called unnecessarily"""
        rag = rag_system_with_mocks

        rag.ai_generator.generate_response.return_value = "Response"
        rag.tool_manager.get_last_sources.return_value = []

        # Query without session_id
        response, sources = rag.query("Test query", session_id=None)

        # get_conversation_history should still be called (returns None)
        # but add_exchange should not be called
        rag.session_manager.add_exchange.assert_not_called()

    def test_query_with_empty_sources(self, rag_system_with_mocks):
        """Test query handling when no sources are returned"""
        rag = rag_system_with_mocks

        rag.session_manager.get_conversation_history.return_value = None
        rag.ai_generator.generate_response.return_value = "General knowledge answer"
        rag.tool_manager.get_last_sources.return_value = []

        response, sources = rag.query("What is 2+2?")

        assert response == "General knowledge answer"
        assert sources == []

    def test_get_course_analytics(self, rag_system_with_mocks):
        """Test course analytics retrieval"""
        rag = rag_system_with_mocks

        rag.vector_store.get_course_count.return_value = 3
        rag.vector_store.get_existing_course_titles.return_value = [
            "Course 1", "Course 2", "Course 3"
        ]

        analytics = rag.get_course_analytics()

        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3
        assert "Course 1" in analytics["course_titles"]

    def test_tool_execution_during_query(self, rag_system_with_mocks):
        """Test that tools can be executed during query processing"""
        rag = rag_system_with_mocks

        # Mock vector store search
        from vector_store import SearchResults
        mock_results = SearchResults(
            documents=["Content about Python"],
            metadata=[{"course_title": "Python Course", "lesson_number": 1}],
            distances=[0.3],
            error=None
        )
        rag.vector_store.search.return_value = mock_results
        rag.vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        # Execute search tool directly to test integration
        result = rag.search_tool.execute(query="Python basics")

        assert "Python Course" in result
        assert "Lesson 1" in result
        assert "Content about Python" in result

    def test_tool_manager_execute_tool_with_search(self, rag_system_with_mocks):
        """Test tool manager can execute search tool"""
        rag = rag_system_with_mocks

        from vector_store import SearchResults
        mock_results = SearchResults(
            documents=["Result"],
            metadata=[{"course_title": "Course", "lesson_number": 1}],
            distances=[0.1],
            error=None
        )
        rag.vector_store.search.return_value = mock_results

        # Execute via tool manager
        result = rag.tool_manager.execute_tool(
            "search_course_content",
            query="test"
        )

        assert "Course" in result

    def test_tool_manager_get_last_sources_from_search(self, rag_system_with_mocks):
        """Test that tool manager retrieves sources from search tool"""
        rag = rag_system_with_mocks

        from vector_store import SearchResults
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
            error=None
        )
        rag.vector_store.search.return_value = mock_results
        rag.vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        # Execute search to populate sources
        rag.search_tool.execute(query="test")

        # Get sources via tool manager
        sources = rag.tool_manager.get_last_sources()

        assert len(sources) == 1
        assert sources[0]["text"] == "Test Course - Lesson 1"
        assert sources[0]["url"] == "https://example.com/lesson1"

    def test_tool_manager_reset_sources_clears_all(self, rag_system_with_mocks):
        """Test that reset_sources clears sources from all tools"""
        rag = rag_system_with_mocks

        # Set some sources
        rag.search_tool.last_sources = [{"text": "Source 1"}]

        # Reset
        rag.tool_manager.reset_sources()

        # Verify cleared
        assert rag.search_tool.last_sources == []

    def test_query_with_course_filter(self, rag_system_with_mocks):
        """Test that AI can use course filter in search"""
        rag = rag_system_with_mocks

        from vector_store import SearchResults
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Python Course", "lesson_number": 2}],
            distances=[0.2],
            error=None
        )
        rag.vector_store.search.return_value = mock_results

        # Execute search with course filter
        result = rag.search_tool.execute(
            query="variables",
            course_name="Python"
        )

        # Verify search was called with course_name
        rag.vector_store.search.assert_called_once_with(
            query="variables",
            course_name="Python",
            lesson_number=None
        )
