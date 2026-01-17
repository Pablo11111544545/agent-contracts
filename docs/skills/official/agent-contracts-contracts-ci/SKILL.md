---
name: agent-contracts-contracts-ci
description: Make contract-driven agents safe to change with strict validation, architecture docs, and contract diffs in CI.
metadata:
  short-description: Contracts in CI
---

# agent-contracts Contracts in CI

Use this skill when you want a stable workflow for changing agents safely (team + CI).

## Goals

- Catch contract mistakes early (`strict=True`)
- Keep architecture up to date (`visualize`)
- Review breaking contract changes (`diff`)

## Recommended CI Checks

1. Run tests: `pytest`
2. Validate contracts (strict): `agent-contracts validate --strict --module <your.nodes>`
3. Generate docs (optional): `agent-contracts visualize --module <your.nodes> --output ARCHITECTURE.md`
4. Review breaking changes:
   - Use `agent-contracts diff` between two versions/modules
   - If breaking changes are expected, document them in release notes

## How to Use `diff` Practically

Pick one pattern:

- **Versioned module**: keep `myapp/agents/v1.py` and `myapp/agents/v2.py` as sources for `--from-module/--to-module`
- **Repo tags**: run `agent-contracts diff` in two checkouts (CI jobs) and compare outputs

## Guardrails

- Treat state as loggable; avoid secrets in slices.
- Prefer adding new slices/fields over mutating existing meanings.

## References (load only when needed)

- `docs/cli.md`
- `docs/roadmap.md`
- `docs/skills/official/agent-contracts-contracts-ci/references/checklist.md`
