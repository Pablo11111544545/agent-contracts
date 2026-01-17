# Official Skills (agent-contracts Users)

These skills are designed for people **building real AI agents with `agent-contracts`**.
They include practical workflows and guardrails that match this repository’s APIs and examples.

## Skill Packs

- `docs/skills/official/agent-contracts-app-builder/` (overview)
- `docs/skills/official/agent-contracts-backend-runtime/` (API/SSE runtime)
- `docs/skills/official/agent-contracts-routing-tuning/` (routing design/debug)
- `docs/skills/official/agent-contracts-interactive-flow/` (multi-turn Q/A)
- `docs/skills/official/agent-contracts-tool-use-rag/` (services/tools/RAG)
- `docs/skills/official/agent-contracts-contracts-ci/` (CI validation/diff/visualize)

## How to Use

Pick your agent tool and copy the files into the location it reads:

- Codex Skills: copy the folder into your skills directory and use its `SKILL.md`.
- Other agents (Claude Code, etc.): copy the content into your project instruction file (e.g., `CLAUDE.md`), and keep the referenced docs/examples nearby.

## Language

Each pack includes:

- `SKILL.md` (English)
- `SKILL.ja.md` (日本語)

Most skill systems expect a single entry file and a unique skill name.
When copying into your agent tool, pick one language variant (typically rename it to `SKILL.md` if required).
