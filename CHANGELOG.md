# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-01-09

### Improved

- **GenericSupervisor match reason display**
  - LLM context now includes WHY each rule candidate matched
  - Format: `- node_name (P95): matched because request.field=value`
  - Enables LLM to make more informed routing decisions
  - No API changes required

## [0.2.0] - 2026-01-08

### Added

- **StateAccessor pattern** for type-safe, immutable state access
  - `StateAccessor[T]` generic class with `get()`, `set()`, and `update()` methods
  - Standard accessors: `Internal`, `Request`, `Response`
  - Convenience functions: `reset_response()`, `increment_turn()`, `set_error()`, `clear_error()`
  - All operations are immutable (return new state, never mutate)
  - Full test coverage (26 tests)

- **Runtime layer** for agent execution
  - `AgentRuntime`: Unified execution engine with lifecycle hooks
  - `RequestContext` / `ExecutionResult`: Typed I/O containers
  - `RuntimeHooks` Protocol: Customization points for app-specific logic
  - `SessionStore` Protocol + `InMemorySessionStore`: Session persistence abstraction
  - Full test coverage (23 tests)

- **State operations helpers**
  - `ensure_slices()`: Ensure slices exist in state
  - `merge_session()`: Merge session data into state
  - `reset_internal_flags()`: Reset internal flags with keyword args
  - `create_base_state()`: Create minimal initial state
  - `update_slice()`, `copy_slice()`, `get_nested()`: Utility functions
  - Full test coverage (28 tests)

- **Streaming execution**
  - `StreamingRuntime`: Node-by-node streaming execution for SSE
  - `StreamEvent` / `StreamEventType`: Typed streaming events
  - `NodeExecutor`: Node wrapper for streaming pipelines
  - LangGraph `astream()` integration via `stream_with_graph()`
  - Helper functions: `create_status_event()`, `create_progress_event()`, `create_data_event()`
  - Full test coverage (16 tests)

### Migration Guide (Phase 5)

Applications can adopt the new runtime layer by:

1. Implement `SessionStore` protocol for your database (e.g., `PostgresSessionStore`)
2. Implement `RuntimeHooks` protocol for app-specific state processing
3. Use `AgentRuntime` or `StreamingRuntime` instead of direct graph execution
4. Replace direct state manipulation with `StateAccessor` pattern

## [0.1.0] - 2026-01-06

### Added

- Initial release
- `NodeContract` for declarative node I/O contracts
- `ModularNode` and `InteractiveNode` base classes
- `NodeRegistry` for node registration and discovery
- `GenericSupervisor` for LLM-driven routing with rule hints
- `GraphBuilder` for automatic LangGraph construction
- `BaseAgentState` and slice definitions
- `ContractVisualizer` for architecture documentation
- `ContractValidator` for static contract validation
- LangSmith observability integration
