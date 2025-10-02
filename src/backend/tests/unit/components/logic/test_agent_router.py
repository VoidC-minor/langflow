import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from langflow.components.logic.agent_router import AgentRouterComponent
from langflow.schema.message import Message
from tests.base import ComponentTestBaseWithoutClient, VersionComponentMapping, DID_NOT_EXIST


class TestAgentRouterComponent(ComponentTestBaseWithoutClient):
    @pytest.fixture
    def component_class(self):
        return AgentRouterComponent

    @pytest.fixture
    def mock_router_llm(self):
        """Create a mock router LLM for testing."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = MagicMock()
        agent.ainvoke = AsyncMock()
        return agent

    @pytest.fixture
    def default_kwargs(self, mock_router_llm, mock_agent):
        return {
            "input_task": "Analyze the sales data to find trends",
            "router_llm": mock_router_llm,
            "agent_descriptions": json.dumps({
                "AgentA": {"desc": "a data analysis agent"},
                "AgentB": {"desc": "a creative agent"},
                "AgentC": {"desc": "a database agent"}
            }),
            "agent_a": mock_agent,
            "agent_b": mock_agent,
            "agent_c": mock_agent,
            "fallback_agent": mock_agent,
            "return_plan": False,
            "max_iterations": 10,
            "default_agent": "fallback",
        }

    @pytest.fixture
    def file_names_mapping(self):
        return [
            VersionComponentMapping(
                version="1.1.1",
                module="logic",
                file_name="agent_router"
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
        assert component.display_name == "Agent Router"
        assert component.name == "AgentRouter"
        assert component.icon == "users"
        assert len(component.inputs) == 14
        assert len(component.outputs) == 4

    def test_parse_agent_descriptions_valid_json(self, component_class, default_kwargs):
        """Test parsing valid JSON agent descriptions."""
        component = component_class(**default_kwargs)
        agents = component.parse_agent_descriptions()
        
        assert len(agents) == 3
        assert "AgentA" in agents
        assert "AgentB" in agents
        assert "AgentC" in agents
        assert agents["AgentA"]["desc"] == "a data analysis agent"

    def test_parse_agent_descriptions_invalid_json(self, component_class, default_kwargs):
        """Test handling of invalid JSON in agent descriptions."""
        default_kwargs["agent_descriptions"] = "invalid json"
        component = component_class(**default_kwargs)
        agents = component.parse_agent_descriptions()
        
        assert agents == {}

    def test_parse_agent_descriptions_missing_desc(self, component_class, default_kwargs):
        """Test handling of agent descriptions with missing desc field."""
        default_kwargs["agent_descriptions"] = json.dumps({
            "AgentA": {"desc": "a data analysis agent"},
            "AgentB": {"invalid": "missing desc field"},  # Invalid
            "AgentC": {"desc": "a database agent"}
        })
        component = component_class(**default_kwargs)
        agents = component.parse_agent_descriptions()
        
        assert len(agents) == 2
        assert "AgentA" in agents
        assert "AgentC" in agents
        assert "AgentB" not in agents

    def test_create_routing_prompt(self, component_class, default_kwargs):
        """Test creation of routing prompt."""
        component = component_class(**default_kwargs)
        agents = component.parse_agent_descriptions()
        prompt = component.create_routing_prompt(agents)
        
        assert "task router" in prompt
        assert "AgentA" in prompt
        assert "data analysis agent" in prompt
        assert "JSON object" in prompt
        assert "selected_agent" in prompt

    @pytest.mark.asyncio
    async def test_route_task_success(self, component_class, default_kwargs):
        """Test successful task routing."""
        # Mock router LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "plan": {
                "selected_agent": "AgentA",
                "reason": "Task requires data analysis",
                "task": "Analyze the sales data to find trends"
            }
        })
        default_kwargs["router_llm"].ainvoke.return_value = mock_response
        
        component = component_class(**default_kwargs)
        agent, reason, task = await component.route_task()
        
        assert agent == "agent_a"
        assert "data analysis" in reason
        assert task == "Analyze the sales data to find trends"

    @pytest.mark.asyncio
    async def test_route_task_fallback_agent(self, component_class, default_kwargs):
        """Test routing to fallback agent."""
        # Mock router LLM response with fallback
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "plan": {
                "selected_agent": "fallback",
                "reason": "Task doesn't match any specific agent",
                "task": "Handle general query"
            }
        })
        default_kwargs["router_llm"].ainvoke.return_value = mock_response
        
        component = component_class(**default_kwargs)
        agent, reason, task = await component.route_task()
        
        assert agent == "fallback"
        assert "general" in reason.lower()

    @pytest.mark.asyncio
    async def test_route_task_invalid_json_response(self, component_class, default_kwargs):
        """Test handling of invalid JSON response from router LLM."""
        # Mock router LLM response with invalid JSON
        mock_response = MagicMock()
        mock_response.content = "invalid json response"
        default_kwargs["router_llm"].ainvoke.return_value = mock_response
        
        component = component_class(**default_kwargs)
        agent, reason, task = await component.route_task()
        
        assert agent == "fallback"  # Should fallback
        assert "Parse error" in reason

    @pytest.mark.asyncio
    async def test_route_task_no_router_llm(self, component_class, default_kwargs):
        """Test handling when no router LLM is provided."""
        default_kwargs["router_llm"] = None
        component = component_class(**default_kwargs)
        agent, reason, task = await component.route_task()
        
        assert agent == "fallback"
        assert "No router LLM available" in reason

    @pytest.mark.asyncio
    async def test_route_task_unknown_agent(self, component_class, default_kwargs):
        """Test handling of unknown agent in router response."""
        # Mock router LLM response with unknown agent
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "plan": {
                "selected_agent": "UnknownAgent",
                "reason": "Test unknown agent",
                "task": "Test task"
            }
        })
        default_kwargs["router_llm"].ainvoke.return_value = mock_response
        
        component = component_class(**default_kwargs)
        agent, reason, task = await component.route_task()
        
        assert agent == "fallback"  # Should fallback to default

    def test_get_agent_for_route(self, component_class, default_kwargs):
        """Test getting the appropriate agent for each route."""
        component = component_class(**default_kwargs)
        
        assert component.get_agent_for_route("agent_a") == component.agent_a
        assert component.get_agent_for_route("agent_b") == component.agent_b
        assert component.get_agent_for_route("agent_c") == component.agent_c
        assert component.get_agent_for_route("fallback") == component.fallback_agent
        assert component.get_agent_for_route("invalid") is None

    def test_get_custom_message(self, component_class, default_kwargs):
        """Test getting custom messages for routes."""
        default_kwargs["agent_a_message"] = Message(content="Custom message for Agent A")
        component = component_class(**default_kwargs)
        
        message = component.get_custom_message("agent_a")
        assert message.content == "Custom message for Agent A"
        
        # Test route without custom message
        message = component.get_custom_message("agent_b")
        assert message.content == ""

    @pytest.mark.asyncio
    async def test_execute_with_agent_success(self, component_class, default_kwargs):
        """Test successful execution with an agent."""
        from unittest.mock import patch
        
        # Mock the get_chat_result function
        with patch('langflow.components.logic.agent_router.get_chat_result') as mock_get_chat_result:
            mock_get_chat_result.return_value = Message(text="Agent A analysis result")
            
            component = component_class(**default_kwargs)
            result = await component.execute_with_agent("agent_a", "Analyze data")
            
            assert result.text == "Agent A analysis result"
            mock_get_chat_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_agent_no_agent(self, component_class, default_kwargs):
        """Test execution when no agent is configured."""
        default_kwargs["agent_a"] = None
        component = component_class(**default_kwargs)
        result = await component.execute_with_agent("agent_a", "Test task")
        
        # Should return the task text
        assert result.content == "Test task"

    @pytest.mark.asyncio
    async def test_execute_with_agent_with_plan(self, component_class, default_kwargs):
        """Test execution with routing plan included."""
        from unittest.mock import patch
        
        default_kwargs["return_plan"] = True
        component = component_class(**default_kwargs)
        component._routing_plan = "Selected: AgentA | Reason: Test | Task: Test task"
        
        with patch('langflow.components.logic.agent_router.get_chat_result') as mock_get_chat_result:
            mock_get_chat_result.return_value = Message(text="Agent result")
            
            result = await component.execute_with_agent("agent_a", "Test task")
            
            assert "[ROUTING PLAN:" in result.text
            assert "Agent result" in result.text

    @pytest.mark.asyncio
    async def test_agent_a_response_matched(self, component_class, default_kwargs):
        """Test Agent A response when route matches."""
        from unittest.mock import patch
        
        # Mock router LLM to select Agent A
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "plan": {
                "selected_agent": "AgentA",
                "reason": "Data analysis task",
                "task": "Analyze data"
            }
        })
        default_kwargs["router_llm"].ainvoke.return_value = mock_response
        
        # Mock agent execution
        with patch('langflow.components.logic.agent_router.get_chat_result') as mock_get_chat_result:
            mock_get_chat_result.return_value = Message(text="Analysis complete")
            
            component = component_class(**default_kwargs)
            response = await component.agent_a_response()
            
            assert response.text == "Analysis complete"
            assert "Routed to Agent A" in component.status

    @pytest.mark.asyncio
    async def test_agent_a_response_not_matched(self, component_class, default_kwargs):
        """Test Agent A response when route doesn't match."""
        # Mock router LLM to select different agent
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "plan": {
                "selected_agent": "AgentB",
                "reason": "Creative task",
                "task": "Create content"
            }
        })
        default_kwargs["router_llm"].ainvoke.return_value = mock_response
        
        component = component_class(**default_kwargs)
        response = await component.agent_a_response()
        
        assert response.content == ""

    @pytest.mark.asyncio
    async def test_fallback_response_matched(self, component_class, default_kwargs):
        """Test fallback response when route matches."""
        from unittest.mock import patch
        
        # Mock router LLM to select fallback
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "plan": {
                "selected_agent": "fallback",
                "reason": "General task",
                "task": "Handle general query"
            }
        })
        default_kwargs["router_llm"].ainvoke.return_value = mock_response
        
        # Mock agent execution
        with patch('langflow.components.logic.agent_router.get_chat_result') as mock_get_chat_result:
            mock_get_chat_result.return_value = Message(text="Fallback handled")
            
            component = component_class(**default_kwargs)
            response = await component.fallback_response()
            
            assert response.text == "Fallback handled"
            assert "Routed to Fallback" in component.status

    def test_max_iterations_protection(self, component_class, default_kwargs):
        """Test max iterations protection mechanism."""
        default_kwargs["max_iterations"] = 1
        component = component_class(**default_kwargs)
        
        # Simulate multiple iterations
        component.update_ctx({f"{component._id}_iteration": 2})
        component.iterate_and_stop_once("agent_a")
        
        # Should not raise an exception and should handle gracefully

    def test_update_build_config(self, component_class, default_kwargs):
        """Test build config update method."""
        component = component_class(**default_kwargs)
        build_config = {}
        
        updated_config = component.update_build_config(build_config, "fallback", "default_agent")
        
        # Should return the config (may be unchanged for this component)
        assert isinstance(updated_config, dict)

    @pytest.mark.asyncio
    async def test_component_execution_flow(self, component_class, default_kwargs):
        """Test complete component execution flow."""
        from unittest.mock import patch
        
        # Mock router LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "plan": {
                "selected_agent": "AgentA",
                "reason": "Analysis task",
                "task": "Analyze data"
            }
        })
        default_kwargs["router_llm"].ainvoke.return_value = mock_response
        
        # Mock agent execution
        with patch('langflow.components.logic.agent_router.get_chat_result') as mock_get_chat_result:
            mock_get_chat_result.return_value = Message(text="Task completed")
            
            component = component_class(**default_kwargs)
            
            # Test that the component can run without errors
            response = await component.message_response()
            assert isinstance(response, Message)
