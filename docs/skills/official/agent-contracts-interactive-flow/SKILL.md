---
name: agent-contracts-interactive-flow
description: Build question/answer style agents using InteractiveNode, explicit routing, and workflow slices.
metadata:
  short-description: Interactive Q/A flows
---

# agent-contracts Interactive Flow

Use this skill when your agent needs multi-turn interaction (ask a question, receive an answer, continue).

## Recommended Building Blocks

- `InteractiveNode` for standard ask/process/check lifecycle
- A domain slice (e.g., `workflow` or `interview`) to store progress
- Optional `explicit_routing_handler` when answers must return to the node that asked

## Workflow

1. Pick a domain slice (`workflow`/`interview`) and define the minimal fields you need.
2. Implement an `InteractiveNode`:
   - `prepare_context()` reads domain slice
   - `process_answer()` updates domain slice from `request`
   - `check_completion()` decides when to stop
   - `generate_question()` writes `response` (e.g., `response_type="question"`)
3. Add routing:
   - Use rule triggers (priority 50-100) for “continue the flow”
   - Use terminal response types for “done”
4. Debug with `decide_with_trace()` when the flow loops or stalls.

## Guardrails

- Keep conversation history out of state unless it is needed for routing; prefer `context_builder` summary when necessary.
- Don’t store large payloads in domain slices (token/cost risk).

## References (load only when needed)

- `docs/core_concepts.md` (InteractiveNode / Explicit routing)
- `docs/skills/official/agent-contracts-interactive-flow/references/patterns.md`
