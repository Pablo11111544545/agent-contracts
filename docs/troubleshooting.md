# Troubleshooting

> Common issues and their solutions

---

## Validation Errors

### "Unknown slice 'X' in node 'Y' reads/writes"

**Cause**: The slice name is not registered in the registry.

**Solution**:

```python
# Option 1: Add the slice to the registry
registry.add_valid_slice("your_slice_name")

# Option 2: Check for typos
# Maybe "shoping" should be "shopping"
```

**Prevention**:
```python
# Define slice names as constants
SLICE_SHOPPING = "shopping"
SLICE_INTERVIEW = "interview"

# Use constants in contracts
reads=[SLICE_SHOPPING]
```

---

### "Node requires LLM but not provided"

**Cause**: Contract has `requires_llm=True` but no LLM was injected.

**Solution**:
```python
# Provide LLM when instantiating
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
node = MyNode(llm=llm)

# Or when building graph
graph = build_graph_from_registry(
    registry=registry,
    llm=llm,  # Passed to all nodes
)
```

---

### "Unknown service 'X' required by node 'Y'"

**Cause**: The service is declared in `services` but not available.

**Solution**:
```python
# Provide all required services
db_service = DatabaseService()
cache_service = CacheService()

node = MyNode(
    llm=llm,
    db_service=db_service,
    cache_service=cache_service,
)
```

**Prevention**:
```python
# Validate with known services
validator = ContractValidator(
    registry,
    known_services={"db_service", "cache_service"},
)
```

---

## Routing Issues

### "Node is never called"

**Possible causes and solutions**:

1. **No matching TriggerCondition**
   ```python
   # Check: Is your 'when' condition correct?
   when={"request.action": "serch"}  # Typo! Should be "search"
   ```

2. **Priority too low**
   ```python
   # Another node with higher priority is matching first
   # Use decide_with_trace() to debug
   decision = await supervisor.decide_with_trace(state)
   print(decision.reason.matched_rules)
   ```

3. **Missing from supervisor**
   ```python
   # Check: Is the node registered to the correct supervisor?
   supervisor="main"  # Must match supervisors= in build_graph_from_registry
   ```

4. **Unreachable (no trigger conditions)**
   ```python
   # Add a trigger condition
   trigger_conditions=[
       TriggerCondition(priority=10, when={"request.action": "my_action"})
   ]
   ```

---

### "Wrong node is being selected"

**Debug with traceable routing**:
```python
decision = await supervisor.decide_with_trace(state)

print(f"Selected: {decision.selected_node}")
print(f"Type: {decision.reason.decision_type}")
print(f"Matched rules:")
for rule in decision.reason.matched_rules:
    print(f"  P{rule.priority}: {rule.node} - {rule.condition}")
```

**Common fixes**:
- Adjust priority values
- Make `when` conditions more specific
- Add `when_not` to exclude unwanted matches

---

### "LLM routing is unpredictable"

**Solutions**:

1. **Improve llm_hints**
   ```python
   # Bad
   llm_hint="Search"
   
   # Good
   llm_hint="Use when user explicitly asks to search for products. Do NOT use for browsing or recommendations."
   ```

2. **Use rule-based for clear actions**
   ```python
   # If the action is explicit, use rules instead of LLM
   when={"request.action": "search"}  # Clear intent
   ```

3. **Increase priority for critical paths**
   ```python
   priority=100  # Force selection before LLM decides
   ```

---

## Execution Issues

### "Infinite loop / Max iterations reached"

**Cause**: Nodes keep routing back without reaching END.

**Solutions**:

1. **Check terminal states**
   ```python
   # Make sure your response types are in terminal_states
   terminal_response_types={"interview", "results", "error"}
   
   # And your node outputs matching types
   return NodeOutputs(response={"response_type": "results", ...})
   ```

2. **Set is_terminal on appropriate nodes**
   ```python
   CONTRACT = NodeContract(
       is_terminal=True,  # Force END after this node
   )
   ```

3. **Increase max_iterations during debugging**
   ```python
   supervisor = GenericSupervisor(
       max_iterations=50,  # Increase to find the issue
   )
   ```

---

### "State updates not persisting"

**Cause**: Node outputs don't match contract writes.

**Solution**:
```python
# Contract declares
writes=["shopping"]

# Execute must return matching slice
return NodeOutputs(
    shopping={"cart": [...]},  # ✅ Correct
    # Not: response={"cart": [...]}  # ❌ Wrong slice
)
```

---

### "NodeInputs missing expected data"

**Cause**: Contract reads don't include the needed slice.

**Solution**:
```python
# If you need data from 'context' slice
CONTRACT = NodeContract(
    reads=["request", "context"],  # Include 'context'
)

async def execute(self, inputs, config=None):
    context = inputs.get_slice("context")  # Now available
```

---

## Configuration Issues

### "Config not loading"

**Check file path**:
```python
from agent_contracts.config import load_config, set_config

# Absolute path
config = load_config("/path/to/agent_config.yaml")

# Or relative to your working directory
config = load_config("./config/agent_config.yaml")

set_config(config)
```

**Check YAML syntax**:
```yaml
# Valid YAML
supervisor:
  max_iterations: 10

response_types:
  terminal_states:
    - interview
    - results
```

---

### "Terminal states not working"

**Check configuration**:
```yaml
# In agent_config.yaml
response_types:
  terminal_states:
    - interview    # Must match response_type exactly
    - results
    - error
```

**Check response_type formatting**:
```python
# Must match exactly
return NodeOutputs(
    response={
        "response_type": "interview",  # Exact match
        # Not "Interview" or "INTERVIEW"
    }
)
```

---

## Testing Issues

### "Async tests failing"

**Use pytest-asyncio**:
```python
import pytest

@pytest.mark.asyncio
async def test_node_execution():
    node = MyNode(llm=mock_llm)
    inputs = NodeInputs(request={"action": "test"})
    
    result = await node.execute(inputs)
    
    assert result.response is not None
```

**Configure pytest**:
```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
```

---

### "Registry state leaking between tests"

**Reset registry in fixtures**:
```python
import pytest
from agent_contracts import reset_registry


@pytest.fixture(autouse=True)
def clean_registry():
    reset_registry()
    yield
    reset_registry()
```

---

## Performance Issues

### "LLM calls are slow"

**Solutions**:

1. **Use lighter models for routing**
   ```python
   # Use GPT-3.5 for supervisor, GPT-4 for nodes
   routing_llm = ChatOpenAI(model="gpt-3.5-turbo")
   execution_llm = ChatOpenAI(model="gpt-4")
   
   supervisor = GenericSupervisor(llm=routing_llm)
   ```

2. **Rely more on rule-based routing**
   ```python
   # If action is explicit, don't need LLM
   when={"request.action": "search"}
   ```

3. **Remove LLM from simple graphs**
   ```python
   # Pure rule-based, no LLM overhead
   supervisor = GenericSupervisor(
       llm=None,  # Rule-based only
   )
   ```

---

## Getting Help

If you're stuck:

1. **Check the examples**: `examples/` directory
2. **Use validation**: `ContractValidator.validate()`
3. **Use tracing**: `decide_with_trace()`
4. **Enable debug logging**:
   ```python
   import logging
   logging.getLogger("agent_contracts").setLevel(logging.DEBUG)
   ```

---

## Related Docs

- 📚 [Core Concepts](core_concepts.md) - Understanding the architecture
- 🎯 [Best Practices](best_practices.md) - Design patterns
