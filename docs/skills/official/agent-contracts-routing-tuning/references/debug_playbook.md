# Routing Debug Playbook

## 1) Confirm terminal-state exits

- If `response.response_type` is terminal, supervisors should return `done`.
- Ensure terminal types are configured (framework config / supervisor settings).

## 2) Inspect rule matches

- Call `decide_with_trace()` and print:
  - `decision.selected_node`
  - `decision.reason.decision_type`
  - `decision.reason.matched_rules` (priority + condition)

If expected node is missing:
- Check slice names and paths (`request.action`, `_internal.step`, etc.)
- Check `when_not` conditions
- Check priority ordering

## 3) If LLM is involved

- Ensure candidates include the intended node.
- Keep `llm_hint` short and discriminative.
- If routing is unstable, tighten rules or reduce candidates.

## 4) Context issues

- If you used `context_builder`, ensure it returns `slices` and optional `summary`.
- Keep context small; avoid large strings/images (sanitization will truncate).
