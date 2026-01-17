# CLI

The CLI expects your modules or files to register nodes (typically via `get_node_registry()`).

If a module defines `register_all_nodes(registry=None)` but does not register nodes at import time, the CLI calls it automatically after importing the module.

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
- If your app already has a compiled LangGraph, pass it to the visualizer via `--graph-module` (recommended for app-specific entrypoints/state):

```bash
agent-contracts visualize --module myapp.nodes --graph-module myapp.graph --graph-func get_graph --output -
```

- Otherwise, when possible, the CLI compiles a best-effort LangGraph from the registry to include the `LangGraph Node Flow` section.

## Diff

```bash
agent-contracts diff --from-module myapp.v1.nodes --to-module myapp.v2.nodes
agent-contracts diff --from-file ./old_nodes.py --to-file ./new_nodes.py
```

Exit code: `2` when breaking changes are detected, otherwise `0`.
