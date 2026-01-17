# Skills (Agent Instructions)

This folder contains agent instruction assets (often called “skills”).

There are two audiences:

- **Users of `agent-contracts`**: official skills to help you implement real agents faster.
- **Contributors**: templates/checklists to keep changes consistent.

## Official Skills (for agent-contracts users)

- `docs/skills/official/index.md`

## Contributor Templates

- `docs/skills/contrib/index.md`

## Notes

- These are templates to copy into your agent tool’s expected location (e.g., a `skills/` folder).
- Keep skills short and procedural; move long references into separate files.

## CI / PR Checklist (Optional)

If you maintain this repo with agent assistance, consider adding a PR checklist like:

- Tests: `pytest`
- Coverage: `pytest --cov=agent_contracts`
- Contracts: `agent-contracts validate --strict --file ...`
- Contract change review: `agent-contracts diff --from-... --to-...`
