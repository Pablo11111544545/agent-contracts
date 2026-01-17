---
name: agent-contracts-contributor
description: Workflow and guardrails for making changes to the agent-contracts OSS (tests, docs, CLI, strict validation).
metadata:
  short-description: Contribute to agent-contracts
---

# agent-contracts Contributor Skill (Template)

Use this skill when implementing or changing `agent-contracts` itself (not when using it as a library).

## Project Goals (keep in mind)

- Contract-driven nodes for LangGraph with strong DX.
- CI-friendly validation (`strict`), and tooling (`validate/visualize/diff`).
- Minimal surface area and consistent patterns.

## Local Setup

Preferred flow (venv):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

Run tests and coverage:

```bash
pytest
pytest --cov=agent_contracts --cov-report=term-missing
```

## Change Checklist (do this every PR)

- Small, focused change (avoid unrelated refactors).
- Tests added/updated for new behavior.
- Docs updated if public API/behavior changed:
  - `README.md` / `README.ja.md`
  - `docs/*` (core concepts, getting started, CLI)
- Examples updated if you changed recommended usage patterns (`examples/*`).

## Common Tasks

### Add / Change Contract Validation

- File: `src/agent_contracts/validator.py`
- Add tests in: `tests/test_validator.py`
- If adding new warnings/errors:
  - Decide whether it’s a warning vs error.
  - Ensure `strict=True` behaves as intended.

### Add / Change CLI

- File: `src/agent_contracts/cli.py`
- Entry point: `pyproject.toml` (`[project.scripts]`)
- Add tests in: `tests/test_cli.py`
- Keep exit codes stable:
  - `validate`: `0` ok, `1` errors
  - `diff`: `0` ok, `2` breaking changes

### Add / Change Contract Diff

- File: `src/agent_contracts/contract_diff.py`
- Keep output readable and stable (`ContractDiffReport.to_text()`).
- Add tests in: `tests/test_contract_diff.py`

### Add / Update Examples

- Put runnable scripts in `examples/`
- Avoid external services by default; keep examples runnable without network where possible.

## Guardrails

- Prefer existing patterns (`NodeRegistry`, `GraphBuilder`, `GenericSupervisor`, `AgentRuntime`).
- Keep new features behind a minimal API; don’t over-generalize early.
- If behavior is ambiguous, add a test that documents the intended behavior.

## Definition of Done

- `pytest` passes
- Coverage doesn’t regress materially (or justify exceptions)
- Docs/examples reflect reality
