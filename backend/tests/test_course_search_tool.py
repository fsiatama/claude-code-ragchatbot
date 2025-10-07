"""
Unit tests for CourseSearchTool

Tests the execute() method of CourseSearchTool with various scenarios:
- Valid queries with and without filters
- Invalid course names
- Empty results
- Source tracking functionality
"""

import pytest
from unittest.mock import Mock, MagicMock
from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool"""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store"""
        mock_store = Mock()
        mock_store.search = Mock()
        mock_store.get_lesson_link = Mock(return_value="https://example.com/lesson1")
        mock_store.get_course_link = Mock(return_value="https://example.com/course")
        return mock_store

    @pytest.fixture
    def search_tool(self, mock_vector_store):
        """Create a CourseSearchTool with mock vector store"""
        return CourseSearchTool(mock_vector_store)

    def test_execute_basic_query_success(self, search_tool, mock_vector_store):
        """Test basic query without filters returns formatted results"""
        # Setup mock results
        mock_results = SearchResults(
            documents=["This is lesson 1 content about Python basics."],
            metadata=[{"course_title": "Python Basics Course", "lesson_number": 1}],
            distances=[0.5],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        # Execute search
        result = search_tool.execute(query="What are Python basics?")

        # Verify
        assert result is not None
        assert "Python Basics Course" in result
        assert "Lesson 1" in result
        assert "This is lesson 1 content" in result
        mock_vector_store.search.assert_called_once_with(
            query="What are Python basics?", course_name=None, lesson_number=None
        )

    def test_execute_with_course_filter(self, search_tool, mock_vector_store):
        """Test query with course_name filter"""
        mock_results = SearchResults(
            documents=["Content about computer use"],
            metadata=[
                {
                    "course_title": "Building Towards Computer Use with Anthropic",
                    "lesson_number": 2,
                }
            ],
            distances=[0.3],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="computer use", course_name="Computer Use")

        assert result is not None
        assert "Building Towards Computer Use with Anthropic" in result
        mock_vector_store.search.assert_called_once_with(
            query="computer use", course_name="Computer Use", lesson_number=None
        )

    def test_execute_with_lesson_filter(self, search_tool, mock_vector_store):
        """Test query with lesson_number filter"""
        mock_results = SearchResults(
            documents=["Lesson 3 specific content"],
            metadata=[{"course_title": "Python Course", "lesson_number": 3}],
            distances=[0.2],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="specific topic", lesson_number=3)

        assert result is not None
        assert "Lesson 3" in result
        mock_vector_store.search.assert_called_once_with(
            query="specific topic", course_name=None, lesson_number=3
        )

    def test_execute_with_both_filters(self, search_tool, mock_vector_store):
        """Test query with both course_name and lesson_number filters"""
        mock_results = SearchResults(
            documents=["Targeted content"],
            metadata=[{"course_title": "Specific Course", "lesson_number": 5}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(
            query="targeted query", course_name="Specific Course", lesson_number=5
        )

        assert result is not None
        assert "Specific Course" in result
        assert "Lesson 5" in result
        mock_vector_store.search.assert_called_once_with(
            query="targeted query", course_name="Specific Course", lesson_number=5
        )

    def test_execute_handles_error_from_vector_store(
        self, search_tool, mock_vector_store
    ):
        """Test that tool properly handles error from vector store"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="No course found matching 'InvalidCourse'",
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="some query", course_name="InvalidCourse")

        assert result == "No course found matching 'InvalidCourse'"

    def test_execute_empty_results_without_filters(
        self, search_tool, mock_vector_store
    ):
        """Test empty results without filters returns appropriate message"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="nonexistent topic")

        assert result == "No relevant content found."

    def test_execute_empty_results_with_course_filter(
        self, search_tool, mock_vector_store
    ):
        """Test empty results with course filter shows filter in message"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="topic", course_name="Some Course")

        assert "No relevant content found" in result
        assert "in course 'Some Course'" in result

    def test_execute_empty_results_with_lesson_filter(
        self, search_tool, mock_vector_store
    ):
        """Test empty results with lesson filter shows filter in message"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="topic", lesson_number=10)

        assert "No relevant content found" in result
        assert "in lesson 10" in result

    def test_execute_multiple_results(self, search_tool, mock_vector_store):
        """Test formatting multiple search results"""
        mock_results = SearchResults(
            documents=["First document content", "Second document content"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course A", "lesson_number": 2},
            ],
            distances=[0.3, 0.4],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="test query")

        assert "Course A" in result
        assert "Lesson 1" in result
        assert "Lesson 2" in result
        assert "First document content" in result
        assert "Second document content" in result
        # Check that results are separated
        assert result.count("[Course A") == 2

    def test_source_tracking_with_lesson_links(self, search_tool, mock_vector_store):
        """Test that sources are properly tracked with lesson links"""
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        search_tool.execute(query="test")

        assert len(search_tool.last_sources) == 1
        assert search_tool.last_sources[0]["text"] == "Test Course - Lesson 1"
        assert search_tool.last_sources[0]["url"] == "https://example.com/lesson1"
        mock_vector_store.get_lesson_link.assert_called_once_with("Test Course", 1)

    def test_source_tracking_without_lesson_number(
        self, search_tool, mock_vector_store
    ):
        """Test source tracking for results without lesson number"""
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test Course", "lesson_number": None}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_course_link.return_value = "https://example.com/course"

        search_tool.execute(query="test")

        assert len(search_tool.last_sources) == 1
        assert search_tool.last_sources[0]["text"] == "Test Course"
        assert search_tool.last_sources[0]["url"] == "https://example.com/course"
        mock_vector_store.get_course_link.assert_called_once_with("Test Course")

    def test_source_tracking_with_unknown_course(self, search_tool, mock_vector_store):
        """Test source tracking handles unknown course title"""
        mock_results = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "unknown", "lesson_number": None}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        search_tool.execute(query="test")

        assert len(search_tool.last_sources) == 1
        assert search_tool.last_sources[0]["text"] == "unknown"
        # Should not call get_course_link for 'unknown' course
        mock_vector_store.get_course_link.assert_not_called()

    def test_get_tool_definition_structure(self, search_tool):
        """Test that tool definition has correct structure for Anthropic API"""
        definition = search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "properties" in definition["input_schema"]
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]

    def test_format_results_preserves_order(self, search_tool, mock_vector_store):
        """Test that _format_results preserves document order"""
        mock_results = SearchResults(
            documents=["Doc 1", "Doc 2", "Doc 3"],
            metadata=[
                {"course_title": "Course", "lesson_number": 1},
                {"course_title": "Course", "lesson_number": 2},
                {"course_title": "Course", "lesson_number": 3},
            ],
            distances=[0.1, 0.2, 0.3],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="test")

        # Verify order is preserved
        doc1_pos = result.find("Doc 1")
        doc2_pos = result.find("Doc 2")
        doc3_pos = result.find("Doc 3")

        assert doc1_pos < doc2_pos < doc3_pos
