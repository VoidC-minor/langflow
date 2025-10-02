import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from langflow.components.logic.multi_path_router import MultiPathRouterComponent
from langflow.schema.message import Message
from tests.base import ComponentTestBaseWithoutClient, VersionComponentMapping, DID_NOT_EXIST


class TestMultiPathRouterComponent(ComponentTestBaseWithoutClient):
    @pytest.fixture
    def component_class(self):
        return MultiPathRouterComponent

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def mock_specialized_llm(self):
        """Create a mock specialized LLM for testing."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def default_kwargs(self, mock_llm, mock_specialized_llm):
        return {
            "input_text": "Please analyze this sales data for trends",
            "classifier_llm": mock_llm,
            "analysis_llm": mock_specialized_llm,
            "creative_llm": mock_specialized_llm,
            "technical_llm": mock_specialized_llm,
            "general_llm": mock_specialized_llm,
            "task_categories": json.dumps([
                {"name": "analysis", "description": "Data analysis, research, or investigation tasks", "examples": ["analyze this data", "research the topic"]},
                {"name": "creative", "description": "Creative writing, brainstorming, or content generation", "examples": ["write a story", "brainstorm ideas"]},
                {"name": "technical", "description": "Code generation, debugging, or technical problem solving", "examples": ["write code", "fix this bug"]}
            ]),
            "include_confidence": True,
            "max_iterations": 10,
            "fallback_route": "general",
        }

    @pytest.fixture
    def file_names_mapping(self):
        return [
            VersionComponentMapping(
                version="1.1.1",
                module="logic",
                file_name="multi_path_router"
            ),
            VersionComponentMapping(
                version="1.1.0", 
                module="logic",
                file_name=DID_NOT_EXIST
            ),
            VersionComponentMapping(
                version="1.0.19",
                module="logic", 
                file_name=DID_NOT_EXIST
            ),
        ]

    def test_component_initialization(self, component_class, default_kwargs):
        """Test that the component initializes correctly."""
        component = component_class(**default_kwargs)
        assert component.display_name == "LangGraph Router"
        assert component.name == "LangGraphRouter"
        assert component.icon == "git-branch"
        assert len(component.inputs) == 14
        assert len(component.outputs) == 4

    def test_parse_task_categories_valid_json(self, component_class, default_kwargs):
        """Test parsing valid JSON task categories."""
        component = component_class(**default_kwargs)
        categories = component.parse_task_categories()
        
        assert len(categories) == 3
        assert categories[0]["name"] == "analysis"
        assert categories[1]["name"] == "creative"
        assert categories[2]["name"] == "technical"
        assert all("description" in cat for cat in categories)

    def test_parse_task_categories_invalid_json(self, component_class, default_kwargs):
        """Test handling of invalid JSON in task categories."""
        default_kwargs["task_categories"] = "invalid json"
        component = component_class(**default_kwargs)
        categories = component.parse_task_categories()
        
        assert categories == []

    def test_parse_task_categories_missing_fields(self, component_class, default_kwargs):
        """Test handling of categories with missing required fields."""
        default_kwargs["task_categories"] = json.dumps([
            {"name": "analysis"},  # Missing description
            {"name": "creative", "description": "Creative tasks"}  # Valid
        ])
        component = component_class(**default_kwargs)
        categories = component.parse_task_categories()
        
        assert len(categories) == 1
        assert categories[0]["name"] == "creative"

    def test_create_classification_prompt(self, component_class, default_kwargs):
        """Test creation of classification prompt."""
        component = component_class(**default_kwargs)
        categories = component.parse_task_categories()
        prompt = component.create_classification_prompt(categories)
        
        assert "task classification expert" in prompt
        assert "analysis" in prompt
        assert "creative" in prompt
        assert "technical" in prompt
        assert "category name" in prompt

    @pytest.mark.asyncio
    async def test_classify_input_success(self, component_class, default_kwargs):
        """Test successful input classification."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "analysis"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        
        component = component_class(**default_kwargs)
        route, reason = await component.classify_input()
        
        assert route == "analysis"
        assert "Classified as analysis" in reason
        default_kwargs["classifier_llm"].ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_input_invalid_response(self, component_class, default_kwargs):
        """Test handling of invalid classification response."""
        # Mock LLM response with invalid classification
        mock_response = MagicMock()
        mock_response.content = "invalid_category"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        
        component = component_class(**default_kwargs)
        route, reason = await component.classify_input()
        
        assert route == "general"  # Should fallback
        assert "Invalid classification" in reason

    @pytest.mark.asyncio
    async def test_classify_input_no_llm(self, component_class, default_kwargs):
        """Test handling when no classifier LLM is provided."""
        default_kwargs["classifier_llm"] = None
        component = component_class(**default_kwargs)
        route, reason = await component.classify_input()
        
        assert route == "general"
        assert "No classifier LLM available" in reason

    @pytest.mark.asyncio
    async def test_classify_input_llm_error(self, component_class, default_kwargs):
        """Test handling of LLM errors during classification."""
        # Mock LLM to raise an exception
        default_kwargs["classifier_llm"].ainvoke.side_effect = Exception("LLM error")
        
        component = component_class(**default_kwargs)
        route, reason = await component.classify_input()
        
        assert route == "general"  # Should fallback
        assert "Classification error" in reason

    @pytest.mark.asyncio
    async def test_analysis_response_matched(self, component_class, default_kwargs):
        """Test analysis response when route matches."""
        # Mock LLM to return analysis classification
        mock_response = MagicMock()
        mock_response.content = "analysis"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        default_kwargs["analysis_message"] = Message(content="Analysis task selected")
        
        component = component_class(**default_kwargs)
        response = await component.analysis_response()
        
        assert response.content == "Analysis task selected"
        assert "Routed to Analysis" in component.status

    @pytest.mark.asyncio
    async def test_analysis_response_not_matched(self, component_class, default_kwargs):
        """Test analysis response when route doesn't match."""
        # Mock LLM to return different classification
        mock_response = MagicMock()
        mock_response.content = "creative"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        
        component = component_class(**default_kwargs)
        response = await component.analysis_response()
        
        assert response.content == ""

    @pytest.mark.asyncio
    async def test_creative_response_matched(self, component_class, default_kwargs):
        """Test creative response when route matches."""
        # Mock LLM to return creative classification
        mock_response = MagicMock()
        mock_response.content = "creative"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        default_kwargs["creative_message"] = Message(content="Creative task selected")
        
        component = component_class(**default_kwargs)
        response = await component.creative_response()
        
        assert response.content == "Creative task selected"
        assert "Routed to Creative" in component.status

    @pytest.mark.asyncio
    async def test_technical_response_matched(self, component_class, default_kwargs):
        """Test technical response when route matches."""
        # Mock LLM to return technical classification
        mock_response = MagicMock()
        mock_response.content = "technical"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        default_kwargs["technical_message"] = Message(content="Technical task selected")
        
        component = component_class(**default_kwargs)
        response = await component.technical_response()
        
        assert response.content == "Technical task selected"
        assert "Routed to Technical" in component.status

    @pytest.mark.asyncio
    async def test_general_response_matched(self, component_class, default_kwargs):
        """Test general response when route matches."""
        # Mock LLM to return general classification
        mock_response = MagicMock()
        mock_response.content = "general"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        default_kwargs["general_message"] = Message(content="General task selected")
        
        component = component_class(**default_kwargs)
        response = await component.general_response()
        
        assert response.content == "General task selected"
        assert "Routed to General" in component.status

    def test_get_route_message_fallback(self, component_class, default_kwargs):
        """Test that input text is returned as fallback when no route message is set."""
        component = component_class(**default_kwargs)
        message = component.get_route_message("analysis")
        
        assert message.content == default_kwargs["input_text"]

    def test_get_route_message_with_custom_message(self, component_class, default_kwargs):
        """Test that custom route message is returned when set."""
        custom_message = Message(content="Custom analysis message")
        default_kwargs["analysis_message"] = custom_message
        component = component_class(**default_kwargs)
        message = component.get_route_message("analysis")
        
        assert message.content == "Custom analysis message"

    @pytest.mark.asyncio
    async def test_different_input_classifications(self, component_class, default_kwargs):
        """Test that different inputs get classified appropriately."""
        component = component_class(**default_kwargs)
        
        # Test analysis input
        mock_response = MagicMock()
        mock_response.content = "analysis"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        default_kwargs["input_text"] = "Please analyze this sales data"
        
        route, _ = await component.classify_input()
        assert route == "analysis"
        
        # Test creative input
        mock_response.content = "creative"
        default_kwargs["input_text"] = "Write a creative story about space"
        route, _ = await component.classify_input()
        assert route == "creative"
        
        # Test technical input
        mock_response.content = "technical"
        default_kwargs["input_text"] = "Debug this Python code"
        route, _ = await component.classify_input()
        assert route == "technical"

    def test_max_iterations_protection(self, component_class, default_kwargs):
        """Test max iterations protection mechanism."""
        default_kwargs["max_iterations"] = 1
        component = component_class(**default_kwargs)
        
        # Simulate multiple iterations
        component.update_ctx({f"{component._id}_iteration": 2})
        component.iterate_and_stop_once("analysis")
        
        # Should not raise an exception and should handle gracefully

    def test_update_build_config(self, component_class, default_kwargs):
        """Test build config update method."""
        component = component_class(**default_kwargs)
        build_config = {}
        
        updated_config = component.update_build_config(build_config, "general", "fallback_route")
        
        # Should return the config (may be unchanged for this component)
        assert isinstance(updated_config, dict)

    @pytest.mark.asyncio
    async def test_component_execution_flow(self, component_class, default_kwargs):
        """Test complete component execution flow."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "analysis"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        default_kwargs["analysis_message"] = Message(content="Analysis flow completed")
        
        component = component_class(**default_kwargs)
        
        # Test that the component can run without errors
        response = await component.message_response()
        assert isinstance(response, Message)

    def test_categories_with_examples(self, component_class, default_kwargs):
        """Test that categories with examples are processed correctly."""
        component = component_class(**default_kwargs)
        categories = component.parse_task_categories()
        
        # Check that examples are preserved
        analysis_category = next(cat for cat in categories if cat["name"] == "analysis")
        assert "examples" in analysis_category
        assert len(analysis_category["examples"]) > 0
        assert "analyze this data" in analysis_category["examples"]

    def test_categories_without_examples(self, component_class, default_kwargs):
        """Test that categories without examples get empty examples list."""
        default_kwargs["task_categories"] = json.dumps([
            {"name": "test", "description": "Test category"}  # No examples
        ])
        component = component_class(**default_kwargs)
        categories = component.parse_task_categories()
        
        assert len(categories) == 1
        assert categories[0]["examples"] == []

    def test_get_route_llm(self, component_class, default_kwargs):
        """Test getting the appropriate LLM for each route."""
        component = component_class(**default_kwargs)
        
        assert component.get_route_llm("analysis") == component.analysis_llm
        assert component.get_route_llm("creative") == component.creative_llm
        assert component.get_route_llm("technical") == component.technical_llm
        assert component.get_route_llm("general") == component.general_llm
        assert component.get_route_llm("invalid") is None

    @pytest.mark.asyncio
    async def test_execute_with_specialized_llm_success(self, component_class, default_kwargs):
        """Test successful execution with specialized LLM."""
        from langflow.schema.message import Message
        from unittest.mock import patch
        
        # Mock the get_chat_result function
        with patch('langflow.components.logic.multi_path_router.get_chat_result') as mock_get_chat_result:
            mock_get_chat_result.return_value = Message(text="Analysis result from specialized LLM")
            
            component = component_class(**default_kwargs)
            result = await component.execute_with_specialized_llm("analysis")
            
            assert result.text == "Analysis result from specialized LLM"
            mock_get_chat_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_specialized_llm_no_llm(self, component_class, default_kwargs):
        """Test execution when no specialized LLM is configured."""
        default_kwargs["analysis_llm"] = None
        component = component_class(**default_kwargs)
        result = await component.execute_with_specialized_llm("analysis")
        
        # Should return the input text as fallback
        assert result.content == default_kwargs["input_text"]

    @pytest.mark.asyncio
    async def test_analysis_response_with_specialized_llm(self, component_class, default_kwargs):
        """Test analysis response uses specialized LLM."""
        from unittest.mock import patch
        
        # Mock LLM classification response
        mock_response = MagicMock()
        mock_response.content = "analysis"
        default_kwargs["classifier_llm"].ainvoke.return_value = mock_response
        
        # Mock specialized LLM execution
        with patch('langflow.components.logic.multi_path_router.get_chat_result') as mock_get_chat_result:
            mock_get_chat_result.return_value = Message(text="Specialized analysis result")
            
            component = component_class(**default_kwargs)
            response = await component.analysis_response()
            
            assert response.text == "Specialized analysis result"
            assert "Routed to Analysis" in component.status
            mock_get_chat_result.assert_called_once()
