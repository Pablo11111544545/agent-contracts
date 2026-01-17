# CLI

The CLI expects your modules or files to register nodes (typically via `get_node_registry()`).

## Validate

```bash
agent-contracts validate --module myapp.nodes --strict
agent-contracts validate --file ./nodes.py --known-service db_service
```

- `--strict`: Treat warnings as errors (CI-friendly)
- `--known-service`: Repeatable; validates `Contract.services`

Exit code: `0` on success, `1` when errors exist.

## Visualize

```bash
agent-contracts visualize --module myapp.nodes --output ARCHITECTURE.md
agent-contracts visualize --file ./nodes.py --output -
```

- `--output -` prints to stdout.

## Diff

```bash
agent-contracts diff --from-module myapp.v1.nodes --to-module myapp.v2.nodes
agent-contracts diff --from-file ./old_nodes.py --to-file ./new_nodes.py
```

Exit code: `2` when breaking changes are detected, otherwise `0`.
