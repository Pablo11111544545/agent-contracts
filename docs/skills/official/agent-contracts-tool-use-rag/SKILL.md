---
name: agent-contracts-tool-use-rag
description: Implement tool-using or retrieval-style nodes with services, dependency injection, and safe LLM context building.
metadata:
  short-description: Tools/RAG patterns
---

# agent-contracts Tool Use / RAG

Use this skill when your nodes call external services (DB, search, HTTP APIs) or do retrieval-style work.

## Core Ideas

- Declare dependencies in `NodeContract.services` (and `requires_llm` when needed).
- Inject dependencies via:
  - direct node construction (`node_cls(llm=..., my_service=...)`), or
  - `dependency_provider` in `build_graph_from_registry(...)`.
- Keep LLM routing context small; rely on sanitization and `context_builder` only when needed.

## Workflow

1. Define service interfaces (thin wrappers) and keep them testable.
2. Add `services=[...]` to `NodeContract` and use those attributes in `execute()`.
3. Validate services with `ContractValidator(known_services=..., strict=True)` in CI.
4. For RAG:
   - store small retrieval results in a domain slice (ids + snippets)
   - avoid storing full documents or large embeddings in state
5. For routing accuracy:
   - use rule triggers for obvious cases
   - use LLM only among a small candidate set

## Guardrails

- Sanitize long strings and binary-like content before LLM routing (supervisor does this).
- Avoid leaking secrets into state; treat state as loggable.

## References (load only when needed)

- `docs/core_concepts.md` (Context Builder / Sanitization)
- `docs/skills/official/agent-contracts-tool-use-rag/references/di_and_testing.md`
