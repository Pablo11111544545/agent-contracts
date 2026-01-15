# Best Practices

> Design patterns and tips for building robust agents

---

## Slice Design

### ✅ Design for Data Flow

Nodes read from multiple slices and write to others, **transforming and enriching data** as it flows through the graph.

```python
class ContextEnricherNode(ModularNode):
    CONTRACT = NodeContract(
        name="context_enricher",
        description="Enrich request with user profile context",
        reads=["request", "user_profile"],   # Combine inputs
        writes=["context"],                   # Produce enriched context
        supervisor="main",
    )

class SearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="search",
        description="Perform search using request and context",
        reads=["request", "context"],        # Use context
        writes=["search_results"],           # Produce results
        supervisor="main",
    )

class ResponseBuilderNode(ModularNode):
    CONTRACT = NodeContract(
        name="response_builder",
        description="Build the final response from results",
        reads=["search_results", "context"], # From results and context
        writes=["response"],                 # Build final response
        supervisor="main",
    )
```

### ✅ Think of Slices as a Pipeline

```
request ─┬─→ [Enricher] ─→ context ─────┐
         │                              │
user_profile ─────────────────────────→ [Search] ─→ search_results
                                        │
                                        └→ [Builder] ─→ response
```

### ✅ Use Meaningful Names

```python
# Good: Clear purpose
"workflow"       # Workflow progress state
"search_results" # Search results
"user_profile"   # User information

# Avoid: Vague names
"data"           # Data of what?
"temp"           # What's temporary?
```

### ⚠️ Avoid Giant Slices

```python
# Avoid: Everything in one slice
"state": {
    "user": {...},
    "orders": {...},
    "analytics": {...},
}

# Better: Separate by domain
"user_profile": {...}
"orders": {...}
"analytics": {...}
```

---

## State Management

### ✅ Use StateAccessor Pattern

```python
from agent_contracts import Internal, Request, Response

# Good: Type-safe, IDE autocomplete
count = Internal.turn_count.get(state)
state = Internal.turn_count.set(state, count + 1)

# Avoid: Direct dictionary access
count = state["_internal"]["turn_count"]  # KeyError risk
state["_internal"]["turn_count"] = count + 1  # Mutates state!
```

### ✅ Always Return New State

```python
# Good: Immutable operations
state = Internal.turn_count.set(state, 5)
state = reset_response(state)

# Bad: Mutating in place
state["_internal"]["turn_count"] = 5  # Don't do this!
```

### ✅ Use Helper Functions

```python
from agent_contracts import increment_turn, reset_response
from agent_contracts.runtime import update_slice, merge_session

# Good: Clear intent
state = increment_turn(state)
state = reset_response(state)
state = update_slice(state, "workflow", question_count=5)

# Avoid: Manual manipulation
state["_internal"]["turn_count"] += 1
state["_internal"]["is_first_turn"] = False
```

---

## Runtime Layer

### ✅ Use AgentRuntime for Production

```python
from agent_contracts import AgentRuntime, RequestContext

# Good: Unified lifecycle management
runtime = AgentRuntime(graph=graph, session_store=store, hooks=hooks)
result = await runtime.execute(request)

# Avoid: Manual orchestration
state = create_state()
state = restore_session()
state = normalize_state()
final = await graph.ainvoke(state)
# etc... error-prone!
```

### ✅ Implement Custom Hooks

```python
class MyHooks(RuntimeHooks):
    async def prepare_state(self, state, request):
        # Load resources, normalize state
        return state
    
    async def after_execution(self, state, result):
        # Persist session based on response type
        if result.response_type in ("question", "results"):
            await self.session_store.save(...)
```

### ✅ Use StreamingRuntime for SSE

```python
from agent_contracts.runtime import StreamingRuntime

runtime = (
    StreamingRuntime()
    .add_node("step1", node1, "Processing...")
    .add_node("step2", node2, "Finalizing...")
)

async for event in runtime.stream(request):
    yield event.to_sse()  # SSE format
```

## Node Granularity

### ✅ Single Purpose Nodes

```python
# Good: Single responsibility
class SearchNode(ModularNode):
    """Handles product search."""
    
class FilterNode(ModularNode):
    """Applies filters to results."""
    
class RecommendNode(ModularNode):
    """Generates recommendations."""
```

### ❌ Avoid God Nodes

```python
# Bad: Does too much
class EverythingNode(ModularNode):
    """Handles search, filter, recommend, checkout, analytics..."""
    
    async def execute(self, inputs, config=None):
        action = inputs.get_slice("request").get("action")
        if action == "search":
            # 100 lines of search logic
        elif action == "filter":
            # 100 lines of filter logic
        elif action == "recommend":
            # 100 lines of recommend logic
        # ... more and more
```

### ✅ Right Size Heuristic

| Node Size | Symptom | Action |
|-----------|---------|--------|
| Too small | Many nodes, complex routing | Combine related tasks |
| Too large | Long execute(), many if/else | Split by action type |
| Just right | 20-100 lines, clear purpose | 👍 |

---

## Trigger Priority

### ✅ Use Consistent Priority Bands

```python
# Priority scheme
PRIORITY_CRITICAL = 100  # Errors, overrides
PRIORITY_PRIMARY = 50    # Main business logic
PRIORITY_SECONDARY = 30  # Alternative paths
PRIORITY_FALLBACK = 10   # Catch-all handlers

# Example
TriggerCondition(priority=PRIORITY_CRITICAL, when={"request.action": "emergency"})
TriggerCondition(priority=PRIORITY_PRIMARY, when={"request.action": "search"})
TriggerCondition(priority=PRIORITY_FALLBACK, llm_hint="General assistance")
```

### ✅ Flexible Priority Use (v0.4.0+)

v0.4.0+ accurately tracks which condition matched, enabling flexible priority design:

```python
# Option 1: Different priorities for clear ordering
class SearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="search",
        description="Search handler (single node with multiple conditions)",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=51,  # Image search has priority
                when={"request.action": "search", "request.has_image": True},
            ),
            TriggerCondition(
                priority=50,  # Regular search
                when={"request.action": "search"},
            ),
        ],
    )

# Option 2: Multiple nodes competing with same priority (v0.4.0+)
class ImageSearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="image_search",
        description="Image-based search handler",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,  # Same priority, let LLM decide
                when={"request.action": "search", "request.has_image": True},
                llm_hint="Use for image-based search. Best when user uploads an image.",
            ),
        ],
    )

class TextSearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="text_search",
        description="Text-based search handler",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,  # Same priority
                when={"request.action": "search"},
                llm_hint="Use for text-based search. Best for product names or keywords.",
            ),
        ],
    )
```

**Benefits of v0.4.0:**
- Accurate condition tracking even with same priority
- LLM receives precise information about which condition matched
- Enables flexible design patterns where multiple conditions are equally valid

**Use cases for same priority:**
- Multiple different nodes can handle the same action in different ways
- Both approaches are valid, and you want the LLM to choose based on context
- A/B testing scenarios

**Note for v0.3.x and earlier:**
If using v0.3.x or earlier, avoid using the same priority for multiple conditions, as the condition explanation may be inaccurate. In these versions, use different priorities for clear ordering.

### ✅ Document Priority Decisions

```python
class SearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="search",
        description="Search handler with documented priority",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,  # Primary handler, below error handlers (100)
                when={"request.action": "search"},
            )
        ],
    )
```

---

## Supervisor Configuration

### ✅ Customize Field Length Limits

```python
from agent_contracts import GenericSupervisor

# Good: Adjust based on your data size
supervisor = GenericSupervisor(
    supervisor_name="main",
    llm=llm,
    max_field_length=10000,  # Increase for longer content (default: 10000)
)

# For applications with very large state fields
supervisor = GenericSupervisor(
    supervisor_name="main",
    llm=llm,
    max_field_length=20000,  # Higher limit for detailed context
)
```

### ✅ Understand Data Sanitization

The Supervisor automatically sanitizes state data before sending to LLM:

```python
# Automatically handles:
# - Base64 image data → Replaced with "[IMAGE_DATA]"
# - Long strings → Truncated with preserved beginning
# - Example: "Long text..." → "Long text...[TRUNCATED:5000_chars]"
```

**Benefits**:
- Prevents token waste from image data
- Maintains context by preserving beginning of long fields
- Customizable via `max_field_length` parameter

---

## LLM Hints

### ✅ Be Specific and Actionable

```python
# Good: Clear guidance
llm_hint="Use when user explicitly asks to search for products by name or category"

# Bad: Vague
llm_hint="Handles search"
```

### ✅ Include Context About When NOT to Use

```python
# Good: Clear boundaries
llm_hint="Use for product search. Do NOT use for viewing cart or checkout."

# Bad: Only positive
llm_hint="Search products"
```

### ✅ Use Consistent Language

```python
# Good: Consistent pattern
llm_hint="Use when user wants to search products"
llm_hint="Use when user wants to view cart"
llm_hint="Use when user wants to checkout"

# Bad: Inconsistent
llm_hint="Search stuff"
llm_hint="For viewing the cart"
llm_hint="This handles checkout"
```

---

## Testing Nodes

### ✅ Unit Test Individual Nodes

```python
import pytest
from agent_contracts import NodeInputs


class TestSearchNode:
    @pytest.fixture
    def node(self):
        return SearchNode(llm=mock_llm)
    
    @pytest.mark.asyncio
    async def test_search_returns_results(self, node):
        inputs = NodeInputs(
            request={"action": "search", "params": {"query": "laptop"}}
        )
        
        outputs = await node.execute(inputs)
        
        assert outputs.response["response_type"] == "search_results"
        assert len(outputs.response["results"]) > 0
```

### ✅ Test Edge Cases

```python
@pytest.mark.asyncio
async def test_empty_query_returns_error(self, node):
    inputs = NodeInputs(
        request={"action": "search", "params": {"query": ""}}
    )
    
    outputs = await node.execute(inputs)
    
    assert outputs.response["response_type"] == "error"
```

### ✅ Mock External Services

```python
from unittest.mock import AsyncMock


@pytest.fixture
def node_with_mock_service():
    mock_db = AsyncMock()
    mock_db.search.return_value = [{"id": 1, "name": "Test"}]
    return SearchNode(llm=None, db_service=mock_db)
```

---

## Validation

### ✅ Validate Early

```python
# In your main.py or app startup
from agent_contracts import ContractValidator, get_node_registry

registry = get_node_registry()

# Register all nodes
registry.register(NodeA)
registry.register(NodeB)

# Validate BEFORE building graph
validator = ContractValidator(registry)
result = validator.validate()

if result.has_errors:
    print("❌ Contract validation failed:")
    print(result)
    exit(1)

# Now safe to build
graph = build_graph_from_registry(registry, llm)
```

### ✅ Check Shared Writers

```python
# Understand your data flow
shared = validator.get_shared_writers()
for slice_name, writers in shared.items():
    if len(writers) > 1:
        print(f"⚠️  {slice_name} written by: {', '.join(writers)}")
```

### ✅ Provide Known Services

```python
# Be explicit about available services
validator = ContractValidator(
    registry,
    known_services={"db_service", "search_api", "cache"},
)
```

---

## Common Patterns

### Pattern: Error Handler

```python
class ErrorHandlerNode(ModularNode):
    CONTRACT = NodeContract(
        name="error_handler",
        description="Handles error states and returns an error response",
        reads=["_internal"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=100,  # Highest priority
                when={"_internal.error": True},
            )
        ],
        is_terminal=True,  # End flow after handling
    )
```

### Pattern: Fallback Handler

```python
class FallbackNode(ModularNode):
    CONTRACT = NodeContract(
        name="fallback",
        description="Catch-all fallback handler",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=1,  # Lowest priority
                # No 'when' condition = always matches
                llm_hint="Use as fallback for unhandled requests",
            )
        ],
    )
```

### Pattern: Multi-Stage Workflow

```python
# Stage 1: Basic info
class BasicInfoNode(InteractiveNode):
    CONTRACT = NodeContract(
        name="basic_info",
        description="Collect basic information for the workflow",
        reads=["request", "workflow"],
        writes=["response", "workflow"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"workflow.stage": "basic"},
            )
        ],
    )

# Stage 2: Details
class DetailsNode(InteractiveNode):
    CONTRACT = NodeContract(
        name="details",
        description="Collect detailed information for the workflow",
        reads=["request", "workflow"],
        writes=["response", "workflow"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"workflow.stage": "details"},
            )
        ],
    )
```

---

## Anti-Patterns

### ❌ Circular Dependencies

```python
# Bad: NodeA reads X, writes Y
#      NodeB reads Y, writes X
# This can cause infinite loops!

# Solution: Use a coordinator node or redesign data flow
```

### ❌ Overusing LLM Routing

```python
# Bad: Every decision goes to LLM
# Slow, expensive, unpredictable

# Good: Use rule-based for clear actions, LLM for ambiguity
TriggerCondition(
    priority=100,
    when={"request.action": "search"},  # Clear intent = rule-based
)
TriggerCondition(
    priority=10,
    llm_hint="Use when intent is unclear",  # Ambiguous = LLM
)
```

### ❌ Ignoring Validation Warnings

```python
# Warnings exist for a reason!
if result.has_warnings:
    for warning in result.warnings:
        print(f"⚠️  {warning}")
    # Consider fixing before production
```

---

## Next Steps

- 🐛 [Troubleshooting](troubleshooting.md) - Common issues
- 📚 [Core Concepts](core_concepts.md) - Deep dive
