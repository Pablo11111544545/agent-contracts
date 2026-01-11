# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - 2026-01-11

### Changed

- **GenericSupervisor context optimization** (BREAKING BEHAVIOR CHANGE)
  - `_collect_context_slices()` now returns minimal context: `{"request", "response", "_internal"}`
  - Previously included all candidate nodes' `reads` slices
  - **Rationale**: Candidate slices are already evaluated in trigger conditions, passing them to LLM is redundant
  - **Benefits**:
    - Significant token reduction (fewer slices sent to LLM)
    - Clearer responsibility separation: Triggers = rule-based filtering, LLM = final selection
    - Better performance (less data to summarize and transmit)
    - Maintains conversation context via `response` for better LLM understanding
  - **Impact**: LLM routing decisions based on user request, previous response, and internal state
  - Updated 2 test cases to reflect new minimal context behavior
  - No API changes - internal implementation optimization

### Removed

- **StateSummarizer completely removed** (BREAKING API CHANGE)
  - Removed `agent_contracts.utils.summarizer` module entirely
  - Removed `StateSummarizer` class and `summarize_state_slice()` function
  - Removed 22 test cases in `test_summarizer.py`
  - Removed from `agent_contracts.utils.__all__` exports
  - **Rationale**: Not used anywhere in the codebase after supervisor optimization
  - **Migration**: If you were using StateSummarizer, use `json.dumps()` instead:
    ```python
    # Before
    from agent_contracts.utils import StateSummarizer
    summarizer = StateSummarizer()
    summary = summarizer.summarize(data)
    
    # After
    import json
    summary = json.dumps(data, ensure_ascii=False, default=str)
    ```

- **StateSummarizer removed from GenericSupervisor**
  - Removed `_summarize_slice()` method - now uses direct JSON serialization
  - Removed `summarizer` parameter from `__init__()`
  - **Rationale**: `request`, `response`, `_internal` are small slices that don't need summarization
  - **Benefits**:
    - Simpler implementation (no summarization overhead)
    - No information loss (full data preserved)
    - Faster execution (direct JSON serialization)
    - Easier debugging (actual data visible in prompts)
  - Uses `json.dumps()` with `ensure_ascii=False` and `default=str` for robust serialization

### Notes

- This change clarifies the supervisor's role: making routing decisions based on:
  - User intent (`request`)
  - Conversation flow (`response`)
  - Execution state (`_internal`)
- Other state slices (e.g., `interview`, `profile_card`) are already evaluated in trigger conditions and don't need to be re-evaluated by LLM
- If specific state is needed for routing, it should be added to trigger conditions, not passed to LLM

## [0.2.2] - 2026-01-11

### Added

- **StateSummarizer utility class**
  - New `agent_contracts.utils.summarizer` module for intelligent state slice summarization
  - Recursive summarization preserves nested structure while limiting size
  - Configurable depth limiting (default: 2 levels)
  - Configurable item count limiting for dicts and lists
  - Handles complex nested structures (dicts in lists, lists in dicts, etc.)
  - **Cycle detection**: Prevents infinite recursion on circular references using `id()`-based tracking
  - Convenience function `summarize_state_slice()` for quick usage
  - Comprehensive test suite with 22 test cases (including 7 cycle detection tests)

### Improved

- **GenericSupervisor context enrichment**
  - LLM now receives richer context based on candidate nodes' contracts
  - Automatically includes base slices (`request`, `response`, `_internal`)
  - Dynamically adds slices that candidate nodes read from (via `NodeContract.reads`)
  - Improves routing accuracy by providing relevant state information
  - New methods: `_collect_context_slices()`, `_summarize_slice()`
  - **Flexible summarizer configuration**: Accept `StateSummarizer` instance via constructor
  - No breaking changes - internal implementation only
  - Added 5 new test cases for context building verification

- **GenericSupervisor context summarization**
  - Now uses `StateSummarizer` for recursive state slice summarization
  - Better preservation of nested data structure information
  - Previously, nested lists and dicts lost all detail beyond first level
  - Now shows hierarchical structure with controlled depth and item counts
  - Improves LLM context quality without breaking existing functionality
  - No API changes - internal implementation enhancement only

- **Prompt structure improvement**
  - `NodeRegistry.build_llm_prompt()` now accepts optional `context` parameter
  - When context is provided, it's automatically integrated into the prompt template
  - Cleaner separation of concerns: registry handles prompt structure, supervisor provides context
  - Backward compatible: `context=None` by default
  - Simplifies supervisor code by delegating prompt+context merging to registry

- **Flexible StateSummarizer configuration**
  - `GenericSupervisor.__init__()` now accepts optional `summarizer` parameter
  - Pass a custom `StateSummarizer` instance for full control over summarization behavior
  - If omitted, creates a default instance with sensible defaults
  - Most flexible approach: allows complete customization while maintaining simplicity
  - Backward compatible: `summarizer=None` by default

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
