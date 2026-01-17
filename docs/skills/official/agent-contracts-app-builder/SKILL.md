---
name: agent-contracts-app-builder
description: Build a production-minded AI agent using agent-contracts (contracts, slices, validation, graph, runtime, CLI tooling).
metadata:
  short-description: Build agents with agent-contracts
---

# agent-contracts App Builder

Use this skill when you are implementing an AI agent **using `agent-contracts`** (not modifying the library itself).

## Outcomes

- A working agent with well-defined state slices and node contracts
- CI-friendly validation (`ContractValidator(strict=True)` + `agent-contracts validate --strict`)
- Architecture docs (`agent-contracts visualize`) and contract change review (`agent-contracts diff`)

## Workflow (recommended)

1. **Start from a runnable baseline**
   - Use `examples/05_backend_runtime.py` as the default backend-shaped reference.
2. **Design your state slices**
   - Keep `request`, `response`, `_internal` as the core.
   - Add domain slices (e.g., `ticket`, `orders`, `workflow`) and register them via `NodeRegistry.add_valid_slice(...)`.
3. **Implement nodes contract-first**
   - Each node: `NodeContract(name, description, reads, writes, supervisor, trigger_conditions, requires_llm, services, is_terminal)`.
   - Keep `writes=["request"]` out of your design (discouraged).
4. **Wire via registry + GraphBuilder**
   - Register nodes into a `NodeRegistry`.
   - Build with `build_graph_from_registry(...)`, set entry point, compile.
5. **Add runtime wrapper**
   - Use `AgentRuntime` (or `StreamingRuntime` when you need SSE-style progress events).
6. **Make it safe to change**
   - Run `ContractValidator(strict=True)` in tests/CI.
   - Use `agent-contracts diff` to review breaking contract changes across versions.
   - Generate architecture docs with `agent-contracts visualize`.

## Quick Checks

- Tests: `pytest`
- Coverage: `pytest --cov=agent_contracts --cov-report=term-missing`
- Contracts: `agent-contracts validate --strict --module <your.nodes.module>`
- Docs: `agent-contracts visualize --module <your.nodes.module> --output ARCHITECTURE.md`

## Common Patterns

### Backend request/response agent

- Use `RequestContext` + `AgentRuntime` for API handlers.
- Treat `response.response_type` as your API “type”, and keep payload in `response.response_data`.

### Multi-step workflow

- Use a domain slice (e.g., `workflow`) + `_internal` flags to drive steps (see `examples/04_multi_step_workflow.py`).

### Interactive (question/answer) flow

- Use `InteractiveNode` for ask/process/check loops (see `docs/core_concepts.md`).

## References (load only when needed)

- `docs/getting_started.md`
- `docs/core_concepts.md`
- `docs/best_practices.md`
- `docs/cli.md`
- `examples/`
