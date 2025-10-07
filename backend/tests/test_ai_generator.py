"""
Unit tests for AIGenerator

Tests the Claude API interaction and tool calling functionality:
- Basic response generation
- Tool calling flow
- Tool execution handling
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ai_generator import AIGenerator


class TestAIGenerator:
    """Test suite for AIGenerator"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create an AIGenerator with mocked client"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client
        return generator

    def test_initialization(self):
        """Test AIGenerator initializes with correct parameters"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            generator = AIGenerator(api_key="test-api-key", model="test-model")

            mock_anthropic.assert_called_once_with(api_key="test-api-key")
            assert generator.model == "test-model"
            assert generator.base_params["model"] == "test-model"
            assert generator.base_params["temperature"] == 0
            assert generator.base_params["max_tokens"] == 800

    def test_generate_response_without_tools(self, ai_generator, mock_anthropic_client):
        """Test basic response generation without tools"""
        # Setup mock response
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="This is a test response")]
        mock_anthropic_client.messages.create.return_value = mock_response

        # Generate response
        result = ai_generator.generate_response(query="What is Python?")

        # Verify
        assert result == "This is a test response"
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-sonnet-4-20250514"
        assert call_args["messages"][0]["content"] == "What is Python?"
        assert "tools" not in call_args

    def test_generate_response_with_conversation_history(
        self, ai_generator, mock_anthropic_client
    ):
        """Test response generation includes conversation history"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response with history")]
        mock_anthropic_client.messages.create.return_value = mock_response

        conversation_history = "User: Previous question\nAssistant: Previous answer"

        result = ai_generator.generate_response(
            query="Follow-up question", conversation_history=conversation_history
        )

        assert result == "Response with history"
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert conversation_history in call_args["system"]

    def test_generate_response_with_tools_provided(
        self, ai_generator, mock_anthropic_client
    ):
        """Test that tools are passed to API when provided"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response")]
        mock_anthropic_client.messages.create.return_value = mock_response

        tools = [{"name": "test_tool", "description": "A test tool"}]

        result = ai_generator.generate_response(query="Test query", tools=tools)

        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["tools"] == tools
        assert call_args["tool_choice"] == {"type": "auto"}

    def test_generate_response_handles_tool_use(
        self, ai_generator, mock_anthropic_client
    ):
        """Test that tool_use stop_reason triggers tool execution"""
        # Setup mock initial response with tool use
        mock_tool_use_block = Mock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.id = "tool_123"
        mock_tool_use_block.name = "search_course_content"
        mock_tool_use_block.input = {"query": "Python basics"}

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_use_block]

        # Setup mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [Mock(text="Final response after tool use")]

        # Configure mock to return different responses
        mock_anthropic_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        # Setup mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool execution result"

        tools = [{"name": "search_course_content", "description": "Search tool"}]

        result = ai_generator.generate_response(
            query="Test query", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="Python basics"
        )

        # Verify second API call was made
        assert mock_anthropic_client.messages.create.call_count == 2

        # Verify final response
        assert result == "Final response after tool use"

    def test_handle_tool_execution_builds_correct_messages(
        self, ai_generator, mock_anthropic_client
    ):
        """Test that _handle_tool_execution builds correct message structure"""
        # Setup mock tool use response
        mock_tool_use_block = Mock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.id = "tool_456"
        mock_tool_use_block.name = "search_course_content"
        mock_tool_use_block.input = {"query": "test", "course_name": "Python"}

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use_block]

        # Setup mock final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final answer")]
        mock_anthropic_client.messages.create.return_value = mock_final_response

        # Setup mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = (
            "[Python Course - Lesson 1]\nContent here"
        )

        # Setup base params
        base_params = {
            "messages": [{"role": "user", "content": "Original query"}],
            "system": "System prompt",
        }

        result = ai_generator._handle_tool_execution(
            mock_initial_response, base_params, mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test", course_name="Python"
        )

        # Verify API call structure
        call_args = mock_anthropic_client.messages.create.call_args[1]
        messages = call_args["messages"]

        # Should have 3 messages: original user, assistant with tool use, user with tool results
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # Check tool result structure
        tool_results = messages[2]["content"]
        assert isinstance(tool_results, list)
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "tool_456"
        assert "[Python Course - Lesson 1]" in tool_results[0]["content"]

    def test_handle_tool_execution_no_tools_in_final_call(
        self, ai_generator, mock_anthropic_client
    ):
        """Test that final API call after tool execution does not include tools"""
        mock_tool_use_block = Mock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.id = "tool_789"
        mock_tool_use_block.name = "search_course_content"
        mock_tool_use_block.input = {"query": "test"}

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use_block]

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final")]
        mock_anthropic_client.messages.create.return_value = mock_final_response

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        base_params = {
            "messages": [{"role": "user", "content": "Query"}],
            "system": "System prompt",
            "tools": [{"name": "search_course_content"}],
            "tool_choice": {"type": "auto"},
        }

        result = ai_generator._handle_tool_execution(
            mock_initial_response, base_params, mock_tool_manager
        )

        # Verify final call does not include tools
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert "tools" not in call_args
        assert "tool_choice" not in call_args

    def test_handle_multiple_tool_calls(self, ai_generator, mock_anthropic_client):
        """Test handling multiple tool calls in one response"""
        # Setup two tool use blocks
        mock_tool_use_1 = Mock()
        mock_tool_use_1.type = "tool_use"
        mock_tool_use_1.id = "tool_1"
        mock_tool_use_1.name = "search_course_content"
        mock_tool_use_1.input = {"query": "query1"}

        mock_tool_use_2 = Mock()
        mock_tool_use_2.type = "tool_use"
        mock_tool_use_2.id = "tool_2"
        mock_tool_use_2.name = "search_course_content"
        mock_tool_use_2.input = {"query": "query2"}

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use_1, mock_tool_use_2]

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Combined result")]
        mock_anthropic_client.messages.create.return_value = mock_final_response

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        base_params = {
            "messages": [{"role": "user", "content": "Query"}],
            "system": "System",
        }

        result = ai_generator._handle_tool_execution(
            mock_initial_response, base_params, mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify both results are in the message
        call_args = mock_anthropic_client.messages.create.call_args[1]
        tool_results = call_args["messages"][2]["content"]
        assert len(tool_results) == 2

    def test_system_prompt_structure(self, ai_generator):
        """Test that SYSTEM_PROMPT has correct structure and instructions"""
        system_prompt = AIGenerator.SYSTEM_PROMPT

        # Check for key instructions
        assert "search_course_content" in system_prompt
        assert "get_course_outline" in system_prompt
        assert "Brief, Concise and focused" in system_prompt
        assert "One tool call per query maximum" in system_prompt

        # Verify it mentions not to provide meta-commentary
        assert "No meta-commentary" in system_prompt

    def test_generate_response_empty_query(self, ai_generator, mock_anthropic_client):
        """Test handling of empty query"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response")]
        mock_anthropic_client.messages.create.return_value = mock_response

        result = ai_generator.generate_response(query="")

        # Should still make API call
        mock_anthropic_client.messages.create.assert_called_once()
        assert result == "Response"

    def test_tool_execution_with_mixed_content_blocks(
        self, ai_generator, mock_anthropic_client
    ):
        """Test tool execution when response has mixed content types"""
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Let me search for that"

        mock_tool_use_block = Mock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.id = "tool_999"
        mock_tool_use_block.name = "search_course_content"
        mock_tool_use_block.input = {"query": "test"}

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_text_block, mock_tool_use_block]

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final")]
        mock_anthropic_client.messages.create.return_value = mock_final_response

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        base_params = {
            "messages": [{"role": "user", "content": "Query"}],
            "system": "System",
        }

        result = ai_generator._handle_tool_execution(
            mock_initial_response, base_params, mock_tool_manager
        )

        # Should only execute tool blocks, not text blocks
        assert mock_tool_manager.execute_tool.call_count == 1
        assert result == "Final"
