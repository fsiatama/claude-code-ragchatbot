"""
End-to-end test with real Anthropic API

This test requires ANTHROPIC_API_KEY to be set and will make actual API calls.
It tests the complete flow from query to response with real AI.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config
from rag_system import RAGSystem


@pytest.mark.skipif(not config.ANTHROPIC_API_KEY, reason="ANTHROPIC_API_KEY not set")
class TestEndToEndWithAPI:
    """End-to-end tests with real Anthropic API"""

    @pytest.fixture
    def rag_system(self):
        """Create a real RAG system"""
        return RAGSystem(config)

    def test_simple_content_query(self, rag_system):
        """Test a simple content query that should trigger tool use"""
        response, sources = rag_system.query(
            "What is lesson 0 about in the Building Towards Computer Use course?"
        )

        print(f"\n{'='*70}")
        print("QUERY: What is lesson 0 about in the Building Towards Computer Use course?")
        print(f"{'='*70}")
        print(f"RESPONSE: {response}")
        print(f"\nSOURCES ({len(sources)}):")
        for i, source in enumerate(sources):
            print(f"  {i+1}. {source.text}")
            if source.url:
                print(f"     URL: {source.url}")

        # Assertions
        assert response is not None
        assert len(response) > 0
        assert response != "query failed"

        # Should have sources if tool was used
        if len(sources) > 0:
            print("\n✓ Tool was used (sources present)")
        else:
            print("\n⚠ No sources returned - tool may not have been used")

    def test_course_outline_query(self, rag_system):
        """Test a query that should use the outline tool"""
        response, sources = rag_system.query(
            "What lessons are in the MCP course?"
        )

        print(f"\n{'='*70}")
        print("QUERY: What lessons are in the MCP course?")
        print(f"{'='*70}")
        print(f"RESPONSE: {response}")
        print(f"\nSOURCES ({len(sources)}):")
        for i, source in enumerate(sources):
            print(f"  {i+1}. {source.text}")

        # Assertions
        assert response is not None
        assert len(response) > 0
        assert response != "query failed"

        # Should mention lessons
        assert "lesson" in response.lower() or "Lesson" in response

    def test_general_knowledge_query(self, rag_system):
        """Test a general knowledge query that shouldn't use tools"""
        response, sources = rag_system.query(
            "What is 2 + 2?"
        )

        print(f"\n{'='*70}")
        print("QUERY: What is 2 + 2?")
        print(f"{'='*70}")
        print(f"RESPONSE: {response}")
        print(f"SOURCES: {len(sources)}")

        # Assertions
        assert response is not None
        assert len(response) > 0
        assert response != "query failed"

        # Probably won't have sources (no tool use needed)
        if len(sources) == 0:
            print("✓ No tools used for general knowledge question (expected)")

    def test_query_with_course_filter(self, rag_system):
        """Test query about a specific course"""
        response, sources = rag_system.query(
            "What does the Building Towards Computer Use course teach about tool use?"
        )

        print(f"\n{'='*70}")
        print("QUERY: What does the Building Towards Computer Use course teach about tool use?")
        print(f"{'='*70}")
        print(f"RESPONSE: {response}")
        print(f"\nSOURCES ({len(sources)}):")
        for i, source in enumerate(sources):
            print(f"  {i+1}. {source.text}")

        # Assertions
        assert response is not None
        assert len(response) > 0
        assert response != "query failed"

    def test_nonexistent_content_query(self, rag_system):
        """Test query about content that doesn't exist"""
        response, sources = rag_system.query(
            "What does the course teach about quantum computing?"
        )

        print(f"\n{'='*70}")
        print("QUERY: What does the course teach about quantum computing?")
        print(f"{'='*70}")
        print(f"RESPONSE: {response}")
        print(f"SOURCES: {len(sources)}")

        # Should still get a response (not "query failed")
        assert response is not None
        assert len(response) > 0
        assert response != "query failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
