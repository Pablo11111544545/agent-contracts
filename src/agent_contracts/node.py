"""ModularNode and InteractiveNode - Base classes for nodes.

All nodes inherit from ModularNode and define a CONTRACT.
Contract-based I/O is automatically validated.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from langchain_core.language_models import BaseChatModel

from agent_contracts.contracts import NodeContract, NodeInputs, NodeOutputs
from agent_contracts.utils.logging import get_logger


class ModularNode(ABC):
    """Base class for modular nodes.
    
    All nodes inherit this class and define a CONTRACT class variable.
    
    Example:
        class LikeHandlerNode(ModularNode):
            CONTRACT = NodeContract(
                name="like_handler",
                reads=["request", "card", "shopping"],
                writes=["card", "shopping", "response"],
                ...
            )
            
            async def execute(self, inputs: NodeInputs) -> NodeOutputs:
                card = inputs.get_slice("card")
                ...
                return NodeOutputs(card={...}, response={...})
    """
    
    # Subclasses must define this
    CONTRACT: ClassVar[NodeContract]
    
    def __init__(
        self,
        llm: BaseChatModel | None = None,
        **services: Any,
    ):
        """Initialize.
        
        Args:
            llm: LangChain LLM (required if CONTRACT.requires_llm is True)
            **services: Other services (declared in CONTRACT.services)
        """
        self.logger = get_logger(self.__class__.__name__)
        self.llm = llm
        
        # Service injection
        self._services = services
        for service_name in self.CONTRACT.services:
            if service_name in services:
                setattr(self, service_name, services[service_name])
        
        # Dependency validation
        self._validate_dependencies()
    
    def _validate_dependencies(self) -> None:
        """Validate declared dependencies from Contract."""
        if self.CONTRACT.requires_llm and self.llm is None:
            self.logger.warning(
                f"Node {self.CONTRACT.name} requires LLM but none provided"
            )
        
        for service_name in self.CONTRACT.services:
            if not hasattr(self, service_name):
                self.logger.warning(
                    f"Node {self.CONTRACT.name} requires {service_name} but not provided"
                )
    
    @abstractmethod
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        """Execute node's main processing.
        
        Args:
            inputs: Input slices per CONTRACT.reads
            
        Returns:
            Output slices per CONTRACT.writes
        """
        pass
    
    async def __call__(self, state: dict) -> dict:
        """LangGraph-compatible Callable.
        
        Extracts required slices from State, calls execute,
        and converts result to State update format.
        """
        # Extract input slices
        inputs = self._extract_inputs(state)
        
        # Execute
        try:
            outputs = await self.execute(inputs)
        except Exception as e:
            self.logger.error(f"Node {self.CONTRACT.name} execution failed: {e}")
            raise
        
        # Convert outputs to State update format
        return self._convert_outputs(outputs)
    
    def _extract_inputs(self, state: dict) -> NodeInputs:
        """Extract required slices from State.
        
        Only extracts slices declared in CONTRACT.reads
        and returns them as NodeInputs.
        """
        data = {}
        for slice_name in self.CONTRACT.reads:
            if slice_name == "_internal":
                data[slice_name] = state.get("_internal", {})
            else:
                data[slice_name] = state.get(slice_name, {})
        
        return NodeInputs(**data)
    
    def _convert_outputs(self, outputs: NodeOutputs) -> dict:
        """Convert NodeOutputs to LangGraph State update format.
        
        Expands from slice format to flat format.
        LangGraph expects a flat dict.
        """
        result = {}
        for slice_name, slice_data in outputs.to_state_updates().items():
            if isinstance(slice_data, dict):
                result[slice_name] = slice_data
        return result
    
    # =========================================================================
    # Helper Methods (for subclasses)
    # =========================================================================
    
    def get_request_param(self, inputs: NodeInputs, key: str, default: Any = None) -> Any:
        """Get request parameter."""
        request = inputs.get_slice("request")
        params = request.get("params") or {}
        return params.get(key, default)
    
    def build_error_response(self, message: str, code: str) -> NodeOutputs:
        """Build error response."""
        return NodeOutputs(
            response={
                "response_type": "error",
                "response_data": {"message": message, "code": code},
            }
        )


class InteractiveNode(ModularNode):
    """Base class for conversational nodes.
    
    Provides standard flow for:
    1. check_completion: Completion check
    2. process_answer: Answer processing (if previous question exists)
    3. generate_question: Next question generation (if not complete)
    
    Subclasses should implement:
    - prepare_context(inputs) -> Any
    - check_completion(context, inputs) -> bool
    - process_answer(context, inputs) -> bool
    - generate_question(context, inputs) -> NodeOutputs
    """
    
    @abstractmethod
    def prepare_context(self, inputs: NodeInputs) -> Any:
        """Prepare execution context.
        
        Extract needed data from NodeInputs and convert to
        easy-to-use object (Pydantic model, etc.).
        """
        pass
    
    @abstractmethod
    def check_completion(self, context: Any, inputs: NodeInputs) -> bool:
        """Check task completion."""
        pass
    
    @abstractmethod
    async def process_answer(self, context: Any, inputs: NodeInputs) -> bool:
        """Process user answer.
        
        Returns:
            bool: True if answer was processed and state updated
        """
        pass
    
    @abstractmethod
    async def generate_question(self, context: Any, inputs: NodeInputs) -> NodeOutputs:
        """Generate and return next question."""
        pass

    async def create_completion_output(self, context: Any, inputs: NodeInputs) -> NodeOutputs:
        """Create output for completion (default: done flag)."""
        return NodeOutputs(_internal={"decision": "done"})
    
    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        """Standard execution flow."""
        # 0. Prepare context
        context = self.prepare_context(inputs)
        
        # 1. Process answer
        await self.process_answer(context, inputs)
        
        # 2. Check completion
        if self.check_completion(context, inputs):
            return await self.create_completion_output(context, inputs)
            
        # 3. Generate question
        return await self.generate_question(context, inputs)
