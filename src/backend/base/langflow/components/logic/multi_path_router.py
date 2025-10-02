import re
from typing import Any

from langflow.base.models.chat_result import get_chat_result
from langflow.custom.custom_component.component import Component
from langflow.io import BoolInput, DropdownInput, HandleInput, IntInput, MessageInput, MessageTextInput, MultilineInput, Output
from langflow.schema.message import Message


class MultiPathRouterComponent(Component):
    display_name = "LangGraph Router"
    description = "Classifies input and routes it to specialized followup tasks using AI-powered classification."
    documentation: str = "https://docs.langflow.org/components-logic#langgraph-router"
    icon = "git-branch"
    name = "LangGraphRouter"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__iteration_updated = False

    inputs = [
        MessageTextInput(
            name="input_text",
            display_name="Input Text",
            info="The input text to classify and route to appropriate specialized task.",
            required=True,
        ),
        HandleInput(
            name="classifier_llm",
            display_name="Classifier LLM",
            input_types=["LanguageModel"],
            required=True,
            info="LLM that will classify the input and determine the appropriate route.",
        ),
        MultilineInput(
            name="task_categories",
            display_name="Task Categories",
            info="JSON array defining the task categories. Each should have: name, description, and examples.",
            value='[{"name": "analysis", "description": "Data analysis, research, or investigation tasks", "examples": ["analyze this data", "research the topic", "investigate the issue"]}, {"name": "creative", "description": "Creative writing, brainstorming, or content generation", "examples": ["write a story", "brainstorm ideas", "create content"]}, {"name": "technical", "description": "Code generation, debugging, or technical problem solving", "examples": ["write code", "fix this bug", "solve technical problem"]}]',
            required=True,
        ),
        BoolInput(
            name="include_confidence",
            display_name="Include Confidence Score",
            info="If true, the classifier will provide confidence scores for its decisions.",
            value=True,
            advanced=True,
        ),
        HandleInput(
            name="analysis_llm",
            display_name="Analysis LLM",
            input_types=["LanguageModel"],
            info="Specialized LLM for analysis tasks (data analysis, research, investigation).",
            advanced=True,
        ),
        HandleInput(
            name="creative_llm",
            display_name="Creative LLM", 
            input_types=["LanguageModel"],
            info="Specialized LLM for creative tasks (writing, brainstorming, content generation).",
            advanced=True,
        ),
        HandleInput(
            name="technical_llm",
            display_name="Technical LLM",
            input_types=["LanguageModel"],
            info="Specialized LLM for technical tasks (coding, debugging, problem solving).",
            advanced=True,
        ),
        HandleInput(
            name="general_llm",
            display_name="General LLM",
            input_types=["LanguageModel"],
            info="General-purpose LLM for fallback and mixed tasks.",
            advanced=True,
        ),
        MessageInput(
            name="analysis_message",
            display_name="Analysis Route Message",
            info="Optional message to pass when routed to analysis tasks.",
            advanced=True,
        ),
        MessageInput(
            name="creative_message",
            display_name="Creative Route Message",
            info="Optional message to pass when routed to creative tasks.",
            advanced=True,
        ),
        MessageInput(
            name="technical_message",
            display_name="Technical Route Message",
            info="Optional message to pass when routed to technical tasks.",
            advanced=True,
        ),
        MessageInput(
            name="general_message",
            display_name="General Route Message",
            info="Optional message to pass when routed to general tasks (fallback).",
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
            name="fallback_route",
            display_name="Fallback Route",
            options=["analysis", "creative", "technical", "general"],
            info="Route to use when classification fails or is uncertain.",
            value="general",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Analysis", name="analysis", method="analysis_response", group_outputs=True),
        Output(display_name="Creative", name="creative", method="creative_response", group_outputs=True),
        Output(display_name="Technical", name="technical", method="technical_response", group_outputs=True),
        Output(display_name="General", name="general", method="general_response", group_outputs=True),
    ]

    def _pre_run_setup(self):
        self.__iteration_updated = False

    def parse_task_categories(self) -> list[dict[str, Any]]:
        """Parse the task categories JSON string into a list of dictionaries."""
        try:
            import json
            categories = json.loads(self.task_categories)
            if not isinstance(categories, list):
                self.log("Task categories must be a JSON array", "error")
                return []
            
            # Validate each category
            valid_categories = []
            for category in categories:
                if not isinstance(category, dict):
                    continue
                if not all(key in category for key in ["name", "description"]):
                    self.log(f"Skipping invalid category: {category}", "warning")
                    continue
                # Ensure examples exist
                if "examples" not in category:
                    category["examples"] = []
                valid_categories.append(category)
            
            return valid_categories
            
        except json.JSONDecodeError as e:
            self.log(f"Invalid JSON in task categories: {e}", "error")
            return []

    def create_classification_prompt(self, categories: list[dict[str, Any]]) -> str:
        """Create the system prompt for task classification."""
        categories_text = ""
        for i, category in enumerate(categories):
            examples_text = ""
            if category.get("examples"):
                examples_text = f"\n  Examples: {', '.join(category['examples'])}"
            
            categories_text += f"{i+1}. {category['name']}: {category['description']}{examples_text}\n"
        
        prompt = f"""You are a task classification expert. Your job is to analyze user input and classify it into one of the following categories:

{categories_text}
Analyze the user's input and respond with ONLY the category name (e.g., "analysis", "creative", "technical", etc.).

If you're unsure or the input doesn't clearly fit any category, respond with "general".

Do not provide explanations or reasoning, just the category name."""
        
        return prompt

    async def classify_input(self) -> tuple[str, str]:
        """Use LLM to classify the input text into appropriate task category."""
        if not self.classifier_llm:
            self.log("No classifier LLM provided, using fallback route", "warning")
            return self.fallback_route, "No classifier LLM available"
        
        categories = self.parse_task_categories()
        if not categories:
            self.log("No valid task categories found, using fallback route", "error")
            return self.fallback_route, "No valid categories"
        
        try:
            system_prompt = self.create_classification_prompt(categories)
            
            # Create messages for the LLM
            system_message = {"role": "system", "content": system_prompt}
            user_message = {"role": "user", "content": f"Classify this input: {self.input_text}"}
            
            self.log("Requesting classification from LLM...")
            self.status = "Classifying input..."
            
            # Get response from classifier LLM
            response = await self.classifier_llm.ainvoke([system_message, user_message])
            classification = response.content.strip().lower()
            
            # Validate the classification result
            valid_routes = ["analysis", "creative", "technical", "general"]
            if classification in valid_routes:
                self.log(f"Input classified as: {classification}")
                return classification, f"Classified as {classification}"
            else:
                self.log(f"Invalid classification '{classification}', using fallback", "warning")
                return self.fallback_route, f"Invalid classification '{classification}', using fallback"
                
        except Exception as e:
            self.log(f"Error during classification: {e}", "error")
            return self.fallback_route, f"Classification error: {str(e)}"

    async def determine_route(self) -> tuple[str, str]:
        """Determine which route to take using AI classification."""
        return await self.classify_input()

    def iterate_and_stop_once(self, route_to_stop: str):
        """Handle iteration counting and stopping to prevent infinite loops."""
        if not self.__iteration_updated:
            self.update_ctx({f"{self._id}_iteration": self.ctx.get(f"{self._id}_iteration", 0) + 1})
            self.__iteration_updated = True
            
            # Check if we've exceeded max iterations
            if self.ctx.get(f"{self._id}_iteration", 0) >= self.max_iterations:
                self.log(f"Max iterations ({self.max_iterations}) reached, using fallback route", "warning")
                route_to_stop = self.fallback_route
            
            self.stop(route_to_stop)

    def get_route_llm(self, route_name: str):
        """Get the appropriate LLM for a given route."""
        if route_name == "analysis":
            return self.analysis_llm
        elif route_name == "creative":
            return self.creative_llm
        elif route_name == "technical":
            return self.technical_llm
        elif route_name == "general":
            return self.general_llm
        else:
            return None

    def get_route_message(self, route_name: str) -> Message:
        """Get the appropriate message for a given route."""
        if route_name == "analysis" and self.analysis_message:
            return self.analysis_message
        elif route_name == "creative" and self.creative_message:
            return self.creative_message
        elif route_name == "technical" and self.technical_message:
            return self.technical_message
        elif route_name == "general" and self.general_message:
            return self.general_message
        else:
            # Return input text as fallback
            return Message(content=self.input_text)

    async def execute_with_specialized_llm(self, route_name: str) -> Message:
        """Execute the input with the specialized LLM for the given route."""
        specialized_llm = self.get_route_llm(route_name)
        
        if not specialized_llm:
            self.log(f"No specialized LLM configured for {route_name} route, returning input message", "warning")
            return self.get_route_message(route_name)
        
        try:
            # Use the route-specific message if available, otherwise use input text
            route_message = self.get_route_message(route_name)
            input_text = route_message.content if route_message.content else self.input_text
            
            self.log(f"Executing with specialized {route_name} LLM...")
            self.status = f"Processing with specialized {route_name} LLM..."
            
            # Execute with the specialized LLM
            input_message_obj = Message(text=input_text)
            result = get_chat_result(
                runnable=specialized_llm,
                input_value=input_message_obj,
            )
            
            # Convert result to Message if needed
            if isinstance(result, Message):
                return result
            else:
                return Message(text=str(result))
                
        except Exception as e:
            self.log(f"Error executing with specialized {route_name} LLM: {e}", "error")
            # Fallback to route message or input text
            return self.get_route_message(route_name)

    async def analysis_response(self) -> Message:
        """Handle Analysis output."""
        selected_route, reason = await self.determine_route()
        if selected_route == "analysis":
            self.status = f"Routed to Analysis - {reason}"
            result = await self.execute_with_specialized_llm("analysis")
            self.iterate_and_stop_once("creative")  # Stop other routes
            return result
        self.iterate_and_stop_once("analysis")  # Stop this route
        return Message(content="")

    async def creative_response(self) -> Message:
        """Handle Creative output."""
        selected_route, reason = await self.determine_route()
        if selected_route == "creative":
            self.status = f"Routed to Creative - {reason}"
            result = await self.execute_with_specialized_llm("creative")
            self.iterate_and_stop_once("technical")  # Stop other routes
            return result
        self.iterate_and_stop_once("creative")  # Stop this route
        return Message(content="")

    async def technical_response(self) -> Message:
        """Handle Technical output."""
        selected_route, reason = await self.determine_route()
        if selected_route == "technical":
            self.status = f"Routed to Technical - {reason}"
            result = await self.execute_with_specialized_llm("technical")
            self.iterate_and_stop_once("general")  # Stop other routes
            return result
        self.iterate_and_stop_once("technical")  # Stop this route
        return Message(content="")

    async def general_response(self) -> Message:
        """Handle General output."""
        selected_route, reason = await self.determine_route()
        if selected_route == "general":
            self.status = f"Routed to General - {reason}"
            result = await self.execute_with_specialized_llm("general")
            self.iterate_and_stop_once("analysis")  # Stop other routes
            return result
        self.iterate_and_stop_once("general")  # Stop this route
        return Message(content="")

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Update build configuration based on field changes."""
        if field_name == "fallback_route":
            # Could add logic to show/hide route message inputs based on fallback route
            pass
        return build_config
