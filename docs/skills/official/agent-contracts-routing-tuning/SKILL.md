---
name: agent-contracts-routing-tuning
description: Tune routing with TriggerCondition priorities, LLM hints, context_builder, and traceable decisions.
metadata:
  short-description: Routing design and debugging
---

# agent-contracts Routing Tuning

Use this skill when you are designing or debugging routing behavior (rule matches vs LLM selection).

## Routing Model (what to optimize)

1. Rule filtering via `TriggerCondition` (`when` / `when_not`, priority)
2. Candidate selection (top matches + ties)
3. Optional LLM decision among candidates (with `llm_hint`)
4. Fallbacks and terminal states (`response.response_type`)

## Practical Tuning Steps

1. Make rule-based selection deterministic first (LLM off).
2. Use priorities to express business rules (100+ = critical, 50-99 = main, 1-49 = fallback).
3. Add `llm_hint` only where ambiguity remains after rules.
4. Use `context_builder` only when needed; keep default minimal slices.
5. Debug with `decide_with_trace()` and inspect matched rules.

## Guardrails

- Prefer rules for safety/constraints; use LLM for ambiguous intent.
- Keep candidate sets small and explainable.
- Treat `response.response_type` terminal values as part of routing design.

## References (load only when needed)

- `docs/core_concepts.md` (Traceable Routing / Context Builder)
- `examples/02_routing_explain.py`
- `docs/skills/official/agent-contracts-routing-tuning/references/debug_playbook.md`
