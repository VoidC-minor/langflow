import json
from typing import Any

from langflow.base.models.chat_result import get_chat_result
from langflow.custom.custom_component.component import Component
from langflow.io import BoolInput, DropdownInput, HandleInput, IntInput, MessageInput, MessageTextInput, MultilineInput, Output
from langflow.schema.message import Message


class AgentRouterComponent(Component):
    display_name = "Agent Router"
    description = "Routes tasks to different specialized agents based on agent descriptions and capabilities."
    documentation: str = "https://docs.langflow.org/components-logic#agent-router"
    icon = "users"
    name = "AgentRouter"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__iteration_updated = False
        self._routing_plan = ""

    inputs = [
        MessageTextInput(
            name="input_task",
            display_name="Input Task",
            info="The task or query to route to the most appropriate agent.",
            required=True,
        ),
        HandleInput(
            name="router_llm",
            display_name="Router LLM",
            input_types=["LanguageModel"],
            required=True,
            info="LLM that will analyze the task and decide which agent should handle it.",
        ),
        MultilineInput(
            name="agent_descriptions",
            display_name="Agent Descriptions",
            info="JSON object defining available agents and their capabilities.",
            value='{"AgentA": {"desc": "a data analysis agent"}, "AgentB": {"desc": "a creative agent"}, "AgentC": {"desc": "a database agent"}}',
            required=True,
        ),
        HandleInput(
            name="agent_a",
            display_name="Agent A",
            input_types=["LanguageModel"],
            info="First specialized agent (e.g., data analysis agent).",
            advanced=True,
        ),
        HandleInput(
            name="agent_b",
            display_name="Agent B",
            input_types=["LanguageModel"],
            info="Second specialized agent (e.g., creative agent).",
            advanced=True,
        ),
        HandleInput(
            name="agent_c",
            display_name="Agent C",
            input_types=["LanguageModel"],
            info="Third specialized agent (e.g., database agent).",
            advanced=True,
        ),
        HandleInput(
            name="fallback_agent",
            display_name="Fallback Agent",
            input_types=["LanguageModel"],
            info="Fallback agent for tasks that don't match any specific agent.",
            advanced=True,
        ),
        BoolInput(
            name="return_plan",
            display_name="Return Routing Plan",
            info="If true, returns the routing decision and plan along with the result.",
            value=False,
            advanced=True,
        ),
        MessageInput(
            name="agent_a_message",
            display_name="Agent A Custom Message",
            info="Optional custom message to pass to Agent A.",
            advanced=True,
        ),
        MessageInput(
            name="agent_b_message",
            display_name="Agent B Custom Message",
            info="Optional custom message to pass to Agent B.",
            advanced=True,
        ),
        MessageInput(
            name="agent_c_message",
            display_name="Agent C Custom Message",
            info="Optional custom message to pass to Agent C.",
            advanced=True,
        ),
        MessageInput(
            name="fallback_message",
            display_name="Fallback Custom Message",
            info="Optional custom message to pass to fallback agent.",
            advanced=True,
        ),
        IntInput(
            name="max_iterations",
            display_name="Max Iterations",
            info="Maximum number of iterations to prevent infinite loops.",
            value=10,
            advanced=True,
        ),
        DropdownInput(
            name="default_agent",
            display_name="Default Agent",
            options=["agent_a", "agent_b", "agent_c", "fallback"],
            info="Default agent to use when routing fails.",
            value="fallback",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Agent A", name="agent_a", method="agent_a_response", group_outputs=True),
        Output(display_name="Agent B", name="agent_b", method="agent_b_response", group_outputs=True),
        Output(display_name="Agent C", name="agent_c", method="agent_c_response", group_outputs=True),
        Output(display_name="Fallback", name="fallback", method="fallback_response", group_outputs=True),
    ]

    def _pre_run_setup(self):
        self.__iteration_updated = False
        self._routing_plan = ""

    def parse_agent_descriptions(self) -> dict[str, Any]:
        """Parse the agent descriptions JSON string into a dictionary."""
        try:
            agents = json.loads(self.agent_descriptions)
            if not isinstance(agents, dict):
                self.log("Agent descriptions must be a JSON object", "error")
                return {}
            
            # Validate each agent description
            valid_agents = {}
            for agent_name, agent_info in agents.items():
                if not isinstance(agent_info, dict) or "desc" not in agent_info:
                    self.log(f"Skipping invalid agent description for {agent_name}", "warning")
                    continue
                valid_agents[agent_name] = agent_info
            
            return valid_agents
            
        except json.JSONDecodeError as e:
            self.log(f"Invalid JSON in agent descriptions: {e}", "error")
            return {}

    def create_routing_prompt(self, agents: dict[str, Any]) -> str:
        """Create the system prompt for agent routing."""
        agents_text = ""
        for agent_name, agent_info in agents.items():
            agents_text += f'"{agent_name}": {{"desc": "{agent_info["desc"]}"}}\n'
        
        prompt = f"""You are an intelligent task router. Your job is to analyze incoming tasks and assign them to the most appropriate specialized agent.

Available Agents:
{agents_text}

Your task is to:
1. Analyze the incoming task/query
2. Determine which agent is best suited to handle it based on their descriptions
3. Create a routing plan that assigns the task to the appropriate agent

Respond with a JSON object in this exact format:
{{
  "plan": {{
    "selected_agent": "AgentA" or "AgentB" or "AgentC",
    "reason": "Brief explanation of why this agent was selected",
    "task": "The specific task to assign to the selected agent"
  }}
}}

If the task doesn't clearly match any agent, select "fallback" as the agent.

Important: Respond ONLY with the JSON object, no additional text."""
        
        return prompt

    async def route_task(self) -> tuple[str, str, str]:
        """Use router LLM to determine which agent should handle the task."""
        if not self.router_llm:
            self.log("No router LLM provided, using default agent", "warning")
            return self.default_agent, "No router LLM available", self.input_task
        
        agents = self.parse_agent_descriptions()
        if not agents:
            self.log("No valid agent descriptions found, using default agent", "error")
            return self.default_agent, "No valid agent descriptions", self.input_task
        
        try:
            system_prompt = self.create_routing_prompt(agents)
            
            # Create messages for the router LLM
            system_message = {"role": "system", "content": system_prompt}
            user_message = {"role": "user", "content": f"Task to route: {self.input_task}"}
            
            self.log("Requesting routing decision from router LLM...")
            self.status = "Analyzing task and selecting agent..."
            
            # Get response from router LLM
            response = await self.router_llm.ainvoke([system_message, user_message])
            routing_response = response.content.strip()
            
            # Parse the JSON response
            try:
                routing_plan = json.loads(routing_response)
                if "plan" not in routing_plan:
                    raise ValueError("Missing 'plan' in routing response")
                
                plan = routing_plan["plan"]
                selected_agent = plan.get("selected_agent", "").lower()
                reason = plan.get("reason", "No reason provided")
                task = plan.get("task", self.input_task)
                
                # Map agent names to our output names
                agent_mapping = {
                    "agenta": "agent_a",
                    "agentb": "agent_b", 
                    "agentc": "agent_c",
                    "fallback": "fallback"
                }
                
                # Find the best match for the selected agent
                mapped_agent = agent_mapping.get(selected_agent)
                if not mapped_agent:
                    # Try partial matching
                    for key, value in agent_mapping.items():
                        if key in selected_agent or selected_agent in key:
                            mapped_agent = value
                            break
                    
                    if not mapped_agent:
                        self.log(f"Unknown agent '{selected_agent}', using default", "warning")
                        mapped_agent = self.default_agent
                
                self._routing_plan = f"Selected: {selected_agent} | Reason: {reason} | Task: {task}"
                self.log(f"Router selected agent: {mapped_agent} - {reason}")
                return mapped_agent, reason, task
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                self.log(f"Failed to parse routing response: {e}", "error")
                self.log(f"Raw response: {routing_response}", "error")
                return self.default_agent, f"Parse error: {str(e)}", self.input_task
                
        except Exception as e:
            self.log(f"Error during task routing: {e}", "error")
            return self.default_agent, f"Routing error: {str(e)}", self.input_task

    def get_agent_for_route(self, route_name: str):
        """Get the appropriate agent for a given route."""
        if route_name == "agent_a":
            return self.agent_a
        elif route_name == "agent_b":
            return self.agent_b
        elif route_name == "agent_c":
            return self.agent_c
        elif route_name == "fallback":
            return self.fallback_agent
        else:
            return None

    def get_custom_message(self, route_name: str) -> Message:
        """Get the custom message for a given route."""
        if route_name == "agent_a" and self.agent_a_message:
            return self.agent_a_message
        elif route_name == "agent_b" and self.agent_b_message:
            return self.agent_b_message
        elif route_name == "agent_c" and self.agent_c_message:
            return self.agent_c_message
        elif route_name == "fallback" and self.fallback_message:
            return self.fallback_message
        else:
            return Message(content="")

    async def execute_with_agent(self, route_name: str, task: str) -> Message:
        """Execute the task with the selected agent."""
        agent = self.get_agent_for_route(route_name)
        
        if not agent:
            self.log(f"No agent configured for {route_name} route, returning task", "warning")
            return Message(content=task)
        
        try:
            # Use custom message if available, otherwise use the routed task
            custom_message = self.get_custom_message(route_name)
            input_text = custom_message.content if custom_message.content else task
            
            self.log(f"Executing task with {route_name} agent...")
            self.status = f"Processing with {route_name} agent..."
            
            # Execute with the selected agent
            input_message_obj = Message(text=input_text)
            result = get_chat_result(
                runnable=agent,
                input_value=input_message_obj,
            )
            
            # Convert result to Message if needed
            if isinstance(result, Message):
                final_result = result
            else:
                final_result = Message(text=str(result))
            
            # Add routing plan if requested
            if self.return_plan and self._routing_plan:
                final_result.text = f"[ROUTING PLAN: {self._routing_plan}]\n\n{final_result.text}"
            
            return final_result
                
        except Exception as e:
            self.log(f"Error executing with {route_name} agent: {e}", "error")
            # Fallback to task text
            return Message(content=task)

    def iterate_and_stop_once(self, route_to_stop: str):
        """Handle iteration counting and stopping to prevent infinite loops."""
        if not self.__iteration_updated:
            self.update_ctx({f"{self._id}_iteration": self.ctx.get(f"{self._id}_iteration", 0) + 1})
            self.__iteration_updated = True
            
            # Check if we've exceeded max iterations
            if self.ctx.get(f"{self._id}_iteration", 0) >= self.max_iterations:
                self.log(f"Max iterations ({self.max_iterations}) reached, using default agent", "warning")
                route_to_stop = self.default_agent
            
            self.stop(route_to_stop)

    async def agent_a_response(self) -> Message:
        """Handle Agent A output."""
        selected_agent, reason, task = await self.route_task()
        if selected_agent == "agent_a":
            self.status = f"Routed to Agent A - {reason}"
            result = await self.execute_with_agent("agent_a", task)
            self.iterate_and_stop_once("agent_b")  # Stop other routes
            return result
        self.iterate_and_stop_once("agent_a")  # Stop this route
        return Message(content="")

    async def agent_b_response(self) -> Message:
        """Handle Agent B output."""
        selected_agent, reason, task = await self.route_task()
        if selected_agent == "agent_b":
            self.status = f"Routed to Agent B - {reason}"
            result = await self.execute_with_agent("agent_b", task)
            self.iterate_and_stop_once("agent_c")  # Stop other routes
            return result
        self.iterate_and_stop_once("agent_b")  # Stop this route
        return Message(content="")

    async def agent_c_response(self) -> Message:
        """Handle Agent C output."""
        selected_agent, reason, task = await self.route_task()
        if selected_agent == "agent_c":
            self.status = f"Routed to Agent C - {reason}"
            result = await self.execute_with_agent("agent_c", task)
            self.iterate_and_stop_once("fallback")  # Stop other routes
            return result
        self.iterate_and_stop_once("agent_c")  # Stop this route
        return Message(content="")

    async def fallback_response(self) -> Message:
        """Handle Fallback output."""
        selected_agent, reason, task = await self.route_task()
        if selected_agent == "fallback":
            self.status = f"Routed to Fallback - {reason}"
            result = await self.execute_with_agent("fallback", task)
            self.iterate_and_stop_once("agent_a")  # Stop other routes
            return result
        self.iterate_and_stop_once("fallback")  # Stop this route
        return Message(content="")

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Update build configuration based on field changes."""
        if field_name == "default_agent":
            # Could add logic to show/hide agent inputs based on default agent
            pass
        return build_config
