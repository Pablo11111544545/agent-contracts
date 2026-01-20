"""Main CLI application for the tech support demo."""

import asyncio
import sys
import time
import uuid
from typing import Any

sys.path.insert(0, "src")

from agent_contracts import (
    NodeRegistry,
    GenericSupervisor,
)

from examples.interactive_tech_support.config.loader import AppConfig, ConfigLoader
from examples.interactive_tech_support.cli.display import Display
from examples.interactive_tech_support.cli.setup_wizard import SetupWizard, LLMConfiguration
from examples.interactive_tech_support.nodes import (
    ClassificationNode,
    HardwareNode,
    SoftwareNode,
    NetworkNode,
    GeneralNode,
    ClarificationNode,
)


class TechSupportCLI:
    """Interactive CLI for the tech support assistant."""

    def __init__(self, config: AppConfig | None = None):
        """Initialize the CLI.

        Args:
            config: Application configuration. Loads default if not provided.
        """
        self.config = config or ConfigLoader().load()
        self.display = Display()
        self.debug_mode = True  # Default ON for demo
        self.llm = None
        self.llm_config: LLMConfiguration | None = None
        self.conversation_turns = 0

        # Initialize registry and nodes
        self.registry = NodeRegistry(
            valid_slices={"request", "routing", "response", "support_context", "_internal"}
        )
        self._register_nodes()

        # Initialize supervisor (will be created after LLM setup)
        self.supervisor: GenericSupervisor | None = None

        # State
        self.state: dict[str, Any] = {
            "request": {
                "message": "",
                "session_id": "demo-session",
            },
            "routing": {
                "category": None,
            },
            "response": {},
            "support_context": {
                "conversation_history": [],
                "current_issue": None,
                "clarifications_count": 0,
                "resolved": False,
            },
            "_internal": {
                "decision": "",
                "needs_clarification": False,
                "needs_classification": False,
                "routing_reason": "",
            },
        }

        # Node instances
        self.node_instances: dict[str, Any] = {}

    def _register_nodes(self) -> None:
        """Register all support nodes."""
        self.registry.register(ClassificationNode)
        self.registry.register(HardwareNode)
        self.registry.register(SoftwareNode)
        self.registry.register(NetworkNode)
        self.registry.register(GeneralNode)
        self.registry.register(ClarificationNode)

    def _create_supervisor(self) -> None:
        """Create the supervisor with current configuration."""
        terminal_states = set(self.config.response_types.terminal_states)

        def context_builder(state: dict, candidates: list[str]) -> dict:
            return {
                "slices": {"request", "routing", "response", "support_context", "_internal"},
                "summary": (
                    "Routing policy:\n"
                    "- 'classification' is internal-only; do not select it unless "
                    "_internal.needs_classification is true.\n"
                    "- If routing.category is set, select the matching specialist.\n"
                    "- If routing.category is null and no rules match, use LLM semantics."
                ),
            }

        self.supervisor = GenericSupervisor(
            supervisor_name="tech_support",
            llm=self.llm,
            registry=self.registry,
            max_iterations=self.config.supervisor.max_iterations,
            terminal_response_types=terminal_states,
            context_builder=context_builder,
        )

        # Create node instances
        self.node_instances = {
            "classification": ClassificationNode(llm=self.llm),
            "hardware_support": HardwareNode(llm=self.llm),
            "software_support": SoftwareNode(llm=self.llm),
            "network_support": NetworkNode(llm=self.llm),
            "general_support": GeneralNode(llm=self.llm),
            "clarification": ClarificationNode(llm=self.llm),
        }

    def _setup_llm(self) -> None:
        """Run the LLM setup wizard."""
        wizard = SetupWizard(self.config)
        self.llm_config = wizard.run()

        if self.llm_config:
            try:
                from examples.interactive_tech_support.utils.llm_factory import LLMFactory

                self.llm = LLMFactory.create(
                    provider=self.llm_config.provider,
                    api_key=self.llm_config.api_key,
                    model=self.llm_config.model,
                    azure_endpoint=self.llm_config.azure_endpoint,
                    azure_api_version=self.llm_config.azure_api_version,
                )
                self.display.print_info(
                    f"LLM configured: {self.llm_config.provider} - {self.llm_config.model}"
                )
            except ImportError as e:
                self.display.print_error(
                    f"Could not import LLM provider library: {e}\n"
                    "Using rule-based routing only."
                )
                self.llm = None
                self.llm_config = None
            except Exception as e:
                self.display.print_error(
                    f"Failed to configure LLM: {e}\n"
                    "Using rule-based routing only."
                )
                self.llm = None
                self.llm_config = None

    def _get_llm_status(self) -> str:
        """Get current LLM status string.

        Returns:
            Status string for display.
        """
        if self.llm_config:
            return f"{self.llm_config.provider} - {self.llm_config.model}"
        return "Not configured (rule-based routing)"

    async def _process_message(self, message: str) -> dict[str, Any]:
        """Process a user message and return the response.

        Args:
            message: The user's message.

        Returns:
            Response data from the selected node.
        """
        # Update state with new message
        self.state["request"]["message"] = message
        self.state["routing"]["category"] = None
        # Clear prior response to avoid terminal-state short-circuit on new input.
        self.state["response"] = {}
        self.state["_internal"]["needs_classification"] = True
        self.state["_internal"]["needs_clarification"] = False
        self.state["_internal"]["decision"] = ""

        # Get routing decision (Supervisor handles all routing via llm_hint)
        if self.supervisor:
            for _ in range(2):
                decision = await self.supervisor.decide_with_trace(self.state)
                self.state["_internal"]["decision"] = decision.selected_node

                # Execute the selected node
                if decision.selected_node in self.node_instances:
                    node = self.node_instances[decision.selected_node]

                    # Execute node with timing
                    start_time = time.time()
                    updates = await node(self.state)
                    execution_time = time.time() - start_time

                    # Update state with outputs
                    for slice_name, slice_data in (updates or {}).items():
                        if slice_name not in self.state:
                            self.state[slice_name] = slice_data
                            continue

                        if isinstance(slice_data, dict) and isinstance(self.state[slice_name], dict):
                            if slice_name == "support_context":
                                for key, value in slice_data.items():
                                    self.state["support_context"][key] = value
                            elif slice_name == "routing":
                                for key, value in slice_data.items():
                                    self.state["routing"][key] = value
                            elif slice_name == "_internal":
                                self.state["_internal"].update(slice_data)
                            elif slice_name == "request":
                                for key, value in slice_data.items():
                                    self.state["request"][key] = value
                            else:
                                self.state[slice_name].update(slice_data)
                        else:
                            self.state[slice_name] = slice_data

                    if decision.selected_node == "classification":
                        if self.debug_mode:
                            reason_str = decision.reason.decision_type
                            if decision.reason.matched_rules:
                                rules = [f"{r.node}(P{r.priority})" for r in decision.reason.matched_rules]
                                reason_str += f" [{', '.join(rules)}]"
                            if decision.reason.llm_used:
                                reason_str += " + LLM"

                            category = (self.state.get("routing") or {}).get("category")
                            if category is not None:
                                reason_str += f" -> category={category}"

                            self.display.print_routing_trace(
                                input_message=message,
                                selected_node=decision.selected_node,
                                reason=decision.reason.decision_type,
                                routing_reason=reason_str,
                                execution_time=execution_time,
                            )
                        continue

                    # Print routing trace if debug mode
                    if self.debug_mode:
                        # Format reason for display
                        reason_str = decision.reason.decision_type
                        if decision.reason.matched_rules:
                            rules = [f"{r.node}(P{r.priority})" for r in decision.reason.matched_rules]
                            reason_str += f" [{', '.join(rules)}]"
                        if decision.reason.llm_used:
                            reason_str += " + LLM"

                        self.display.print_routing_trace(
                            input_message=message,
                            selected_node=decision.selected_node,
                            reason=decision.reason.decision_type,
                            routing_reason=reason_str,
                            execution_time=execution_time,
                        )

                    # Increment turn counter
                    self.conversation_turns += 1

                    routing_info = None
                    if self.debug_mode:
                        routing_info = decision.reason.decision_type

                    return {
                        "response_data": (self.state.get("response") or {}).get("response_data", {}),
                        "routing_info": routing_info,
                    }

        return {
            "response_data": {
                "title": "Error",
                "content": "No node was selected to handle your request.",
                "category": "error",
            },
            "routing_info": None,
        }


    def _handle_command(self, command: str) -> bool:
        """Handle a CLI command.

        Args:
            command: The command string.

        Returns:
            True if the application should continue, False to exit.
        """
        cmd = command.lower().strip()

        if cmd == "/help":
            self.display.print_help()
        elif cmd == "/setup":
            self._setup_llm()
            self._create_supervisor()
        elif cmd == "/status":
            self.display.print_status(
                llm_provider=(
                    self.llm_config.provider if self.llm_config else None
                ),
                llm_model=self.llm_config.model if self.llm_config else None,
                debug_mode=self.debug_mode,
                conversation_turns=self.conversation_turns,
            )
        elif cmd == "/debug":
            self.debug_mode = not self.debug_mode
            status = "ON" if self.debug_mode else "OFF"
            self.display.print_info(f"Debug mode: {status}")
        elif cmd == "/new":
            self._reset_session()
            self.display.print_info("New session started.")
        elif cmd == "/clear":
            self.state["support_context"]["conversation_history"] = []
            self.conversation_turns = 0
            self.display.print_info("Conversation history cleared.")
        elif cmd == "/exit":
            return False
        else:
            self.display.print_error(f"Unknown command: {command}")
            self.display.print_help()

        return True

    def _reset_session(self) -> None:
        """Reset the session to initial state."""
        self.state = {
            "request": {
                "message": "",
                "session_id": f"demo-{uuid.uuid4().hex[:8]}",
            },
            "routing": {
                "category": None,
            },
            "response": {},
            "support_context": {
                "conversation_history": [],
                "current_issue": None,
                "clarifications_count": 0,
                "resolved": False,
            },
            "_internal": {
                "decision": "",
                "needs_clarification": False,
                "needs_classification": False,
                "routing_reason": "",
            },
        }
        self.conversation_turns = 0

    def run(self) -> None:
        """Run the interactive CLI."""
        # Print banner and welcome
        self.display.print_banner()

        # Run setup wizard
        self._setup_llm()
        self._create_supervisor()

        # Print welcome with status
        self.display.print_welcome(self._get_llm_status())

        # Main loop
        while True:
            try:
                user_input = self.display.get_input()

                # Handle empty input
                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if not self._handle_command(user_input):
                        break
                    continue

                # Process message
                result = asyncio.run(self._process_message(user_input))

                # Display response
                self.display.print_response(
                    response_data=result.get("response_data", {}),
                    routing_info=result.get("routing_info"),
                    debug=self.debug_mode,
                )

            except KeyboardInterrupt:
                print()
                break
            except Exception as e:
                self.display.print_error(f"An error occurred: {e}")
                if self.debug_mode:
                    import traceback

                    traceback.print_exc()

        # Goodbye
        self.display.print_goodbye()
