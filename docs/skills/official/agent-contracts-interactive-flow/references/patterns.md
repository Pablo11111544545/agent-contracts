# Interactive Flow Patterns

## Response Types

Common response types:

- `question`: the client should ask the user
- `done`: the flow is complete
- `error`: user-visible failure

Keep `terminal_response_types` consistent with your chosen “done” types.

## Explicit Routing (optional)

When answers must route back to the question owner:

- Store the question owner in a domain slice (e.g., `interview.last_question.node_id`)
- Provide `explicit_routing_handler` in `GenericSupervisor` to return that node name

This avoids encoding routing logic into every node.
