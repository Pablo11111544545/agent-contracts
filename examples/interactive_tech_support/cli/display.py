"""Display helpers for the tech support CLI.

This module provides text-based display functionality that works
without requiring the 'rich' library. For enhanced output with
colors and formatting, install rich: pip install rich
"""

from typing import Any


class Display:
    """Display helper for CLI output.

    Provides formatted output using plain text, with optional
    support for rich formatting if available.
    """

    # Category colors/prefixes
    CATEGORY_PREFIXES = {
        "hardware": "[HW]",
        "software": "[SW]",
        "network": "[NET]",
        "general": "[FAQ]",
        "clarification": "[?]",
    }

    def __init__(self, use_rich: bool = False):
        """Initialize the display helper.

        Args:
            use_rich: Whether to attempt using rich library for output.
        """
        self.use_rich = use_rich
        self._console = None

        if use_rich:
            try:
                from rich.console import Console

                self._console = Console()
            except ImportError:
                self.use_rich = False

    def print_banner(self) -> None:
        """Print the welcome banner."""
        banner = """
================================================================
              Tech Support Assistant
           Powered by agent-contracts
================================================================
"""
        print(banner)

    def print_welcome(self, llm_status: str = "Not configured") -> None:
        """Print the welcome message.

        Args:
            llm_status: Current LLM configuration status.
        """
        print()
        print("Welcome! I can help you with:")
        print("  * Hardware issues (printers, monitors, peripherals)")
        print("  * Software problems (crashes, errors, installations)")
        print("  * Network troubles (WiFi, internet, connectivity)")
        print()
        print(f"LLM Status: {llm_status}")
        print()
        print("Type /help for commands, or describe your issue.")
        print("-" * 60)

    def print_help(self) -> None:
        """Print available commands."""
        print()
        print("Available commands:")
        print("  /help   - Show this help message")
        print("  /setup  - Configure LLM provider")
        print("  /status - Show current configuration")
        print("  /debug  - Toggle debug mode (show routing info)")
        print("  /new    - Start a new session")
        print("  /clear  - Clear conversation history")
        print("  /exit   - Exit the application")
        print()

    def print_response(
        self,
        response_data: dict[str, Any],
        routing_info: str | None = None,
        debug: bool = False,
    ) -> None:
        """Print a formatted response.

        Args:
            response_data: The response data from a node.
            routing_info: Optional routing information for debug mode.
            debug: Whether to show debug information.
        """
        category = response_data.get("category", "general")
        prefix = self.CATEGORY_PREFIXES.get(category, "[?]")
        title = response_data.get("title", "Response")

        print()
        print("=" * 60)
        print(f"{prefix} {title}")

        if debug and routing_info:
            print(f"Routed via: {routing_info}")

        print("-" * 60)

        # Handle different response formats
        if "steps" in response_data:
            print()
            print("Try these steps:")
            for step in response_data.get("steps", []):
                print(f"  {step}")
        elif "content" in response_data:
            print()
            print(response_data.get("content", ""))
        elif "options" in response_data:
            print()
            question = response_data.get("question", "")
            print(question)
            print()
            for i, option in enumerate(response_data.get("options", []), 1):
                print(f"  {i}. {option}")

        # Print follow-up if available
        follow_up = response_data.get("follow_up")
        if follow_up:
            print()
            print(f">> {follow_up}")

        print("=" * 60)
        print()

    def print_error(self, message: str) -> None:
        """Print an error message.

        Args:
            message: The error message to display.
        """
        print()
        print(f"[ERROR] {message}")
        print()

    def print_status(
        self,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        debug_mode: bool = False,
        conversation_turns: int = 0,
    ) -> None:
        """Print current status information.

        Args:
            llm_provider: Current LLM provider name.
            llm_model: Current LLM model name.
            debug_mode: Whether debug mode is enabled.
            conversation_turns: Number of conversation turns.
        """
        print()
        print("Current Status:")
        print("-" * 40)
        if llm_provider:
            print(f"  LLM Provider: {llm_provider}")
            print(f"  Model: {llm_model or 'default'}")
        else:
            print("  LLM: Not configured (rule-based routing only)")
        print(f"  Debug Mode: {'ON' if debug_mode else 'OFF'}")
        print(f"  Conversation Turns: {conversation_turns}")
        print("-" * 40)
        print()

    def print_goodbye(self) -> None:
        """Print goodbye message."""
        print()
        print("Thank you for using Tech Support Assistant!")
        print("Goodbye!")
        print()

    def get_input(self, prompt: str = "You: ") -> str:
        """Get input from the user.

        Args:
            prompt: The prompt to display.

        Returns:
            The user's input string.
        """
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return "/exit"

    def print_info(self, message: str) -> None:
        """Print an informational message.

        Args:
            message: The message to display.
        """
        print(f"[INFO] {message}")

    def print_debug(self, message: str) -> None:
        """Print a debug message.

        Args:
            message: The debug message to display.
        """
        print(f"[DEBUG] {message}")

    def print_routing_trace(
        self,
        input_message: str,
        selected_node: str,
        reason: str,
        routing_reason: str | None,
        execution_time: float | None = None,
    ) -> None:
        """Print detailed routing trace for demo/debug purposes.

        Args:
            input_message: The user's input message.
            selected_node: The selected node name.
            reason: The decision reason.
            routing_reason: The detailed routing reason.
            execution_time: Optional execution time in seconds.
        """
        print()
        print("┌" + "─" * 60 + "┐")
        print("│ SUPERVISOR DECISION" + " " * 40 + "│")
        print("├" + "─" * 60 + "┤")
        
        # Truncate input if too long
        display_input = input_message[:50] + "..." if len(input_message) > 50 else input_message
        print(f"│ Input: {display_input}" + " " * max(0, 52 - len(display_input)) + "│")
        
        print(f"│ Selected: {selected_node}" + " " * max(0, 49 - len(selected_node)) + "│")
        
        if routing_reason:
            # Handle potentially long routing reason
            reason_display = routing_reason[:45] + "..." if len(routing_reason) > 45 else routing_reason
            print(f"│ Reason: {reason_display}" + " " * max(0, 51 - len(reason_display)) + "│")
        
        print("└" + "─" * 60 + "┘")
        
        if execution_time is not None:
            print()
            print("┌" + "─" * 60 + "┐")
            print(f"│ NODE EXECUTION: {selected_node}" + " " * max(0, 43 - len(selected_node)) + "│")
            print("├" + "─" * 60 + "┤")
            time_str = f"{execution_time:.3f}s"
            print(f"│ Execution time: {time_str}" + " " * max(0, 43 - len(time_str)) + "│")
            print("└" + "─" * 60 + "┘")
