"""
Pytest configuration and shared fixtures

Provides common fixtures and configuration for all tests
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from typing import List

# Add parent directory to path so tests can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from models import Source


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config():
    """Create a test configuration"""
    return Config(
        CHUNK_SIZE=500,
        CHUNK_OVERLAP=50,
        MAX_RESULTS=3,
        MAX_HISTORY=2,
        ANTHROPIC_MODEL="claude-sonnet-4-20250514",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        ANTHROPIC_API_KEY="test-api-key"
    )


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_vector_store():
    """Create a mock vector store"""
    mock = MagicMock()
    mock.search.return_value = [
        {
            "text": "Test content from lesson 1",
            "metadata": {
                "course_title": "Test Course",
                "lesson_number": 1,
                "chunk_index": 0
            }
        }
    ]
    mock.get_all_course_titles.return_value = ["Test Course", "Another Course"]
    return mock


@pytest.fixture
def mock_ai_generator():
    """Create a mock AI generator"""
    mock = MagicMock()
    mock.generate_response.return_value = "This is a test response"
    return mock


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager"""
    mock = MagicMock()
    mock.create_session.return_value = "test-session-id"
    mock.get_history.return_value = []
    mock.add_exchange.return_value = None
    mock.clear_session.return_value = None
    return mock


@pytest.fixture
def mock_tool_manager():
    """Create a mock tool manager"""
    mock = MagicMock()
    mock.get_tool_definitions.return_value = []
    mock.execute_tool.return_value = "Tool execution result"
    mock.get_last_sources.return_value = []
    mock.reset_sources.return_value = None
    return mock


@pytest.fixture
def mock_rag_system(mock_vector_store, mock_ai_generator, mock_session_manager, mock_tool_manager):
    """Create a mock RAG system with all dependencies"""
    mock = MagicMock()
    mock.vector_store = mock_vector_store
    mock.ai_generator = mock_ai_generator
    mock.session_manager = mock_session_manager
    mock.tool_manager = mock_tool_manager
    mock.query.return_value = ("Test answer", [])
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Test Course", "Another Course"]
    }
    return mock


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_sources() -> List[Source]:
    """Create sample source objects"""
    return [
        Source(
            text="Test Course - Lesson 1",
            url="https://example.com/course/lesson1"
        ),
        Source(
            text="Test Course - Lesson 2",
            url="https://example.com/course/lesson2"
        )
    ]


@pytest.fixture
def sample_query_request():
    """Create a sample query request"""
    return {
        "query": "What is lesson 1 about?",
        "session_id": "test-session"
    }


@pytest.fixture
def sample_query_response(sample_sources):
    """Create a sample query response"""
    return {
        "answer": "Lesson 1 covers the basics of the topic.",
        "sources": sample_sources,
        "session_id": "test-session"
    }


@pytest.fixture
def sample_course_document():
    """Create a sample course document for testing"""
    return """Course Title: Test Course
Course Link: https://example.com/course
Course Instructor: Test Instructor

Lesson 0: Introduction
Lesson Link: https://example.com/course/lesson0
This is the introduction lesson. It covers basic concepts and setup.

Lesson 1: Getting Started
Lesson Link: https://example.com/course/lesson1
This lesson teaches you how to get started with the material.
"""


# ============================================================================
# API Test Fixtures
# ============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client"""
    mock = MagicMock()

    # Mock message response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Test AI response")]
    mock_response.stop_reason = "end_turn"

    mock.messages.create.return_value = mock_response
    return mock


@pytest.fixture
def mock_chroma_client():
    """Create a mock ChromaDB client"""
    mock = MagicMock()

    # Mock collection
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["Test document"]],
        "metadatas": [[{"course_title": "Test Course", "lesson_number": 1}]],
        "distances": [[0.5]]
    }
    mock_collection.count.return_value = 10

    mock.get_or_create_collection.return_value = mock_collection
    return mock
