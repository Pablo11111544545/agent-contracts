# Core Concepts

> Deep dive into the agent-contracts architecture

---

## Overview

`agent-contracts` is built around a simple principle: **declare what your node does, not how it connects**.

```
┌─────────────────────────────────────────────────────────────┐
│                        Registry                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐               │
│  │ NodeA     │  │ NodeB     │  │ NodeC     │  ...          │
│  │ CONTRACT  │  │ CONTRACT  │  │ CONTRACT  │               │
│  └───────────┘  └───────────┘  └───────────┘               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     GraphBuilder                             │
│  • Analyzes contracts                                        │
│  • Creates supervisors                                       │
│  • Wires LangGraph automatically                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      LangGraph                               │
│  START → Supervisor ⟷ Nodes → END                           │
└─────────────────────────────────────────────────────────────┘
```

---

## NodeContract

The `NodeContract` is the heart of the library. It declares everything about a node:

```python
NodeContract(
    # === Identification ===
    name="my_node",                    # Unique identifier
    description="What this node does", # Human-readable description
    
    # === I/O Definition ===
    reads=["request", "context"],      # State slices this node reads
    writes=["response"],               # State slices this node writes
    
    # === Dependencies ===
    requires_llm=True,                 # Needs LLM?
    services=["db_service"],           # External services needed
    
    # === Routing ===
    supervisor="main",                 # Which supervisor manages this
    trigger_conditions=[...],          # When to activate this node
    is_terminal=False,                 # End flow after execution?
)
```

### Why Contracts?

| Without Contracts | With Contracts |
|-------------------|----------------|
| Manual graph wiring | Automatic graph construction |
| Hidden dependencies | Explicit I/O declaration |
| Runtime errors | Static validation |
| Hard to document | Auto-generated docs |

---

## State Slices

State in `agent-contracts` is organized into isolated **slices**:

```python
state = {
    "request": {           # Input from user
        "action": "search",
        "params": {"query": "laptop"}
    },
    "response": {          # Output to user
        "response_type": "results",
        "data": [...]
    },
    "context": {           # Shared context
        "user_preferences": {...}
    },
    "_internal": {         # Framework internal
        "decision": "search_node",
        "iteration": 1
    }
}
```

### Design Principles

1. **Separation of Concerns**: Each slice has a single purpose
2. **Explicit Access**: Nodes declare which slices they read/write
3. **Validation**: Unknown slices trigger errors

### Built-in Slices

| Slice | Purpose |
|-------|---------|
| `request` | User input (read-only recommended) |
| `response` | User output |
| `_internal` | Framework routing/iteration |

You can define custom slices:

```python
registry.add_valid_slice("shopping")
registry.add_valid_slice("interview")
```

---

## TriggerCondition

Trigger conditions control when a node should be selected:

```python
TriggerCondition(
    priority=10,                           # Higher = evaluated first
    when={"request.action": "search"},     # Match conditions
    when_not={"response.done": True},      # Negative match
    llm_hint="Use for product searches",   # LLM routing hint
)
```

### Priority Levels

| Range | Usage | Example |
|-------|-------|---------|
| 🔴 100+ | Critical/Immediate | Error handlers |
| 🟡 50-99 | Primary handlers | Main business logic |
| 🟢 1-49 | Fallbacks | Default handlers |
| ⚪ 0 | Always match | Catch-all |

### Condition Matching

```python
# Exact value match
when={"request.action": "search"}

# Boolean check
when={"context.authenticated": True}

# Nested path
when={"request.params.category": "electronics"}

# Multiple conditions (AND)
when={"request.action": "buy", "context.cart_ready": True}
```

---

## GenericSupervisor

The supervisor orchestrates node selection using a multi-phase approach:

```
┌─────────────────────────────────────────────────────────────┐
│                    Decision Flow                             │
├─────────────────────────────────────────────────────────────┤
│  1. Terminal State Check                                     │
│     └─ If response_type in terminal_states → done            │
│                                                              │
│  2. Explicit Routing                                         │
│     └─ If action="answer" → route to question owner          │
│                                                              │
│  3. Rule-Based Evaluation                                    │
│     └─ Evaluate all TriggerConditions, collect candidates    │
│                                                              │
│  4. LLM Decision (if available)                             │
│     └─ LLM chooses from candidates using llm_hints           │
│                                                              │
│  5. Fallback                                                 │
│     └─ Use highest priority rule match                       │
└─────────────────────────────────────────────────────────────┘
```

### With vs Without LLM

| Mode | Behavior |
|------|----------|
| **With LLM** | LLM makes final decision using rule hints |
| **Without LLM** | Pure rule-based, uses highest priority match |

---

## InteractiveNode

For conversational agents, use `InteractiveNode`:

```python
from agent_contracts import InteractiveNode


class InterviewNode(InteractiveNode):
    CONTRACT = NodeContract(...)
    
    def prepare_context(self, inputs):
        """Extract context from inputs."""
        return inputs.get_slice("interview")
    
    def check_completion(self, context, inputs):
        """Check if interview is complete."""
        return len(context.get("answers", [])) >= 5
    
    async def process_answer(self, context, inputs, config=None):
        """Process user's answer."""
        answer = inputs.get_slice("request").get("answer")
        # Store answer...
        return True
    
    async def generate_question(self, context, inputs, config=None):
        """Generate next question."""
        # Generate question with LLM...
        return NodeOutputs(response={"question": "What color?"})
```

### Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                  InteractiveNode Flow                        │
├─────────────────────────────────────────────────────────────┤
│  1. prepare_context()     → Extract needed data              │
│  2. check_completion()    → Already done?                    │
│       └─ Yes → create_completion_output()                    │
│       └─ No ↓                                               │
│  3. process_answer()      → Handle user's response           │
│  4. check_completion()    → Now done?                        │
│       └─ Yes → create_completion_output()                    │
│       └─ No → generate_question()                           │
└─────────────────────────────────────────────────────────────┘
```

---

## ContractValidator

Validate contracts before running:

```python
from agent_contracts import ContractValidator

validator = ContractValidator(
    registry,
    known_services={"db_service", "cache_service"},
)
result = validator.validate()

if result.has_errors:
    print(result)  # Show errors
    exit(1)
```

### Validation Levels

| Level | Example |
|-------|---------|
| **ERROR** | Unknown slice in reads/writes |
| **WARNING** | Unknown service, unreachable node |
| **INFO** | Shared writers (multiple nodes write same slice) |


---

## StateSummarizer

For intelligent state slice summarization with recursive structure preservation:

```python
from agent_contracts.utils import StateSummarizer, summarize_state_slice

# Create summarizer with custom settings
summarizer = StateSummarizer(
    max_depth=2,          # Maximum recursion depth
    max_dict_items=3,     # Max dict items per level
    max_list_items=2,     # Max list items per level
    max_str_length=50,    # Max string length
)

# Summarize complex nested data
profile = {
    "user_id": "user123",
    "preferences": {
        "style": "casual",
        "colors": ["blue", "green", "red"],
        "brands": ["Nike", "Adidas", "Puma", "Reebok"],
    },
    "history": [
        {"item": "shirt", "date": "2024-01-01"},
        {"item": "pants", "date": "2024-01-02"},
    ]
}

summary = summarizer.summarize(profile)
# Output: {'user_id': 'user123', 'preferences': {'style': 'casual', 
#          'colors': [...] (3 items), 'brands': [...] (4 items)}, 
#          'history': [{'item', 'date'} (2 items), ...] (2 items)}

# Or use convenience function
summary = summarize_state_slice(profile, max_depth=2)
```

### Key Features

- **Recursive Traversal**: Preserves nested structure (dicts in lists, lists in dicts)
- **Depth Limiting**: Prevents excessive nesting (default: 2 levels)
- **Item Count Control**: Limits items shown per collection (default: 3 for dicts, 2 for lists)
- **Structure Preservation**: Shows hierarchical relationships, not just keys
- **Size Indicators**: Displays total item counts for truncated collections

### Use Cases

1. **LLM Context Building**: Provide rich context without overwhelming token budgets
2. **Debugging**: Quick overview of complex state structures
3. **Logging**: Concise representation of large data structures
4. **API Responses**: Human-readable summaries of nested data

### Integration with Supervisor

`GenericSupervisor` automatically uses `StateSummarizer` for context building:

```python
supervisor = GenericSupervisor("shopping", llm=llm)
# Internally uses StateSummarizer for _summarize_slice()
decision = await supervisor.decide(state)
```

The supervisor's context now includes:
- Nested structure visibility (not just top-level keys)
- First few items from large collections
- Total item counts for truncated data
- Hierarchical relationships preserved

---

## Traceable Routing

For debugging, use `decide_with_trace()`:

```python
decision = await supervisor.decide_with_trace(state)

print(f"Selected: {decision.selected_node}")
print(f"Type: {decision.reason.decision_type}")

for rule in decision.reason.matched_rules:
    print(f"  {rule.node} (P{rule.priority}): {rule.condition}")
```

### Decision Types

| Type | Meaning |
|------|---------|
| `terminal_state` | Response type triggered exit |
| `explicit_routing` | Answer routed to question owner |
| `rule_match` | TriggerCondition matched |
| `llm_decision` | LLM made the choice |
| `fallback` | No match, using default |


## Supervisor Context Building

The `GenericSupervisor` automatically builds rich context for LLM-based routing decisions by analyzing the contracts of candidate nodes.

### How It Works

When the Supervisor needs to make a routing decision:

1. **Collect Base Slices**: Always includes `request`, `response`, `_internal`
2. **Analyze Candidates**: Examines the `reads` field of each candidate node's contract
3. **Merge Slices**: Combines base slices with candidate-specific slices
4. **Summarize**: Converts each slice to a concise string representation
5. **Provide to LLM**: Passes the enriched context for informed decision-making

### Example

```python
# Node contracts
node_a = NodeContract(
    name="profile_analyzer",
    reads=["request", "profile_card", "interview"],
    ...
)

node_b = NodeContract(
    name="search_handler",
    reads=["request", "search_history"],
    ...
)

# When both are candidates, Supervisor provides:
# - request (base)
# - response (base)
# - _internal (base)
# - profile_card (from node_a)
# - interview (from node_a)
# - search_history (from node_b)
```

### Benefits

- **Contract-Driven**: No application-specific knowledge required
- **Efficient**: Only includes relevant state information
- **Automatic**: Works for any node without configuration
- **Scalable**: Adapts as you add new nodes

### Customization

The context building is automatic, but you can influence it through:

1. **Node Contracts**: Declare what your node reads
2. **State Organization**: Keep slices focused and well-named
3. **Slice Size**: Large slices are automatically truncated

```python
# The Supervisor will automatically include these slices
# when this node is a candidate
CONTRACT = NodeContract(
    name="my_node",
    reads=["request", "user_profile", "conversation_history"],
    ...
)
```

---

## StateAccessor Pattern

Type-safe, immutable access to state fields:

```python
from agent_contracts import Internal, Request, Response, reset_response

# Read state
count = Internal.turn_count.get(state)
action = Request.action.get(state)

# Write state (immutable - returns new state)
state = Internal.turn_count.set(state, 5)
state = reset_response(state)
```

### Available Accessors

| Class | Fields |
|-------|--------|
| `Internal` | `turn_count`, `is_first_turn`, `active_mode`, `next_node`, `error` |
| `Request` | `session_id`, `action`, `params`, `message`, `image` |
| `Response` | `response_type`, `response_data`, `response_message` |

### Convenience Functions

```python
from agent_contracts import increment_turn, set_error, clear_error

state = increment_turn(state)  # turn_count++, is_first_turn=False
state = set_error(state, "Something failed")
state = clear_error(state)
```

---

## Runtime Layer

For production applications, use the Runtime Layer for unified execution:

### AgentRuntime

```python
from agent_contracts import AgentRuntime, RequestContext, InMemorySessionStore

runtime = AgentRuntime(
    graph=compiled_graph,
    session_store=InMemorySessionStore(),
)

result = await runtime.execute(RequestContext(
    session_id="abc123",
    action="answer",
    message="I like casual",
    resume_session=True,
))
```

### Execution Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                  AgentRuntime Lifecycle                      │
├─────────────────────────────────────────────────────────────┤
│  1. Create initial state                                     │
│  2. Restore session (if resume_session=True)                 │
│  3. hooks.prepare_state() → Pre-execution customization      │
│  4. graph.ainvoke() → Execute LangGraph                      │
│  5. Build ExecutionResult                                    │
│  6. hooks.after_execution() → Persistence, cleanup           │
└─────────────────────────────────────────────────────────────┘
```

### Custom Hooks

```python
from agent_contracts import RuntimeHooks

class MyHooks(RuntimeHooks):
    async def prepare_state(self, state, request):
        # Normalize state, load resources
        return state
    
    async def after_execution(self, state, result):
        # Save session, log, etc.
        await self.session_store.save(...)
```

### StreamingRuntime (SSE)

```python
from agent_contracts.runtime import StreamingRuntime, StreamEventType

runtime = (
    StreamingRuntime()
    .add_node("search", search_node, "Searching...")
    .add_node("stylist", stylist_node, "Generating...")
)

async for event in runtime.stream(request):
    if event.type == StreamEventType.NODE_END:
        print(f"Node {event.node_name} complete")
    yield event.to_sse()
```

---

## Next Steps

- 🎯 [Best Practices](best_practices.md) - Design patterns
- 🐛 [Troubleshooting](troubleshooting.md) - Common issues
