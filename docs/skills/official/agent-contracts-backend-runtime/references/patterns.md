# Backend Runtime Patterns

## Minimal Slice Setup

- Always keep `request`, `response`, `_internal`.
- Add small, domain-focused slices (e.g., `ticket`, `orders`) instead of one huge `context`.

## Recommended Response Contract

- `response.response_type`: stable string enum for clients and supervisors
- `response.response_data`: JSON-serializable payload
- `response.response_message`: optional user-facing text

## Session

- Use `RequestContext.resume_session=True` with a `SessionStore` in `AgentRuntime` when you need continuity.
- Keep restored slices explicit via `slices_to_restore` (default is `_internal`).

## Streaming (SSE)

- Use `StreamingRuntime.stream(...)` when you want predictable, node-by-node events.
- Use `StreamingRuntime.stream_with_graph(...)` when you want LangGraph-native streaming.
- Keep SSE payloads small; avoid dumping full state every event.

## Node Design

- Keep `reads`/`writes` minimal and explicit.
- Prefer domain slices over `_internal` for business data.
