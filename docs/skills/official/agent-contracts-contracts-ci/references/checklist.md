# Contracts CI Checklist

## Before Merge

- `pytest`
- `agent-contracts validate --strict --module ...`
- If you changed routing:
  - add/adjust a test that asserts `decide_with_trace()` behavior
  - consider adding/adjusting `terminal_response_types`
- If you changed slices:
  - ensure `NodeRegistry.add_valid_slice(...)` exists for new slices
  - avoid writing to `request`

## When Releasing

- Generate/refresh `ARCHITECTURE.md` (or equivalent) via `agent-contracts visualize`
- Run `agent-contracts diff` against the previous version and summarize breaking changes
