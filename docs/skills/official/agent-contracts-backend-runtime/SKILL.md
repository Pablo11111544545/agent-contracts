---
name: agent-contracts-backend-runtime
description: Build an API-oriented agent using AgentRuntime/StreamingRuntime with predictable request/response slices and session support.
metadata:
  short-description: Backend runtime patterns
---

# agent-contracts Backend Runtime

Use this skill when you are implementing an AI agent as a backend service (HTTP API, jobs, or SSE streaming).

## Target Shape

- Input: `RequestContext(session_id, action, params, message, image, resume_session)`
- Output: `response.response_type` + `response.response_data` (+ optional `response.response_message`)
- State slices: `request`, `response`, `_internal` + domain slices (e.g., `ticket`, `orders`, `workflow`)

## Recommended Workflow

1. Start from `examples/05_backend_runtime.py`.
2. Define your domain slices and register them: `NodeRegistry.add_valid_slice("your_slice")`.
3. Implement nodes with `NodeContract` (keep `reads/writes` minimal).
4. Build graph with `build_graph_from_registry(...)` and compile.
5. Wrap with `AgentRuntime` for request/response execution.
6. If you need progressive updates, use `StreamingRuntime` and emit SSE via `StreamEvent.to_sse()`.

## Guardrails

- Prefer `response.response_type` for flow termination and client branching.
- Avoid writing to `request` (discouraged).
- Keep large blobs out of state slices; sanitize before LLM routing (see `GenericSupervisor`).

## References (load only when needed)

- `docs/getting_started.md`
- `docs/core_concepts.md`
- `docs/cli.md`
- `docs/skills/official/agent-contracts-backend-runtime/references/patterns.md`
