# CLI

The CLI expects your modules or files to register nodes (typically via `get_node_registry()`).

If a module defines `register_all_nodes(registry=None)` but does not register nodes at import time, the CLI calls it automatically after importing the module.

Set `AGENT_CONTRACTS_DEBUG=1` to print debug logs to stderr (module loading, graph loading/compilation, Mermaid rendering).

## Validate

```bash
agent-contracts validate --module myapp.nodes --strict
agent-contracts validate --file ./nodes.py --known-service db_service
```

- `--module` (repeatable): Python module path to import (e.g. `myapp.nodes`). The CLI imports (or reloads) the module and expects it to register nodes.
- `--file` (repeatable): Python file path to execute (via `runpy.run_path`) that registers nodes.
- `--strict`: Treat warnings as errors (CI-friendly)
- `--known-service` (repeatable): Declares allowed service names and validates `NodeContract.services` against them.

Exit code: `0` on success, `1` when errors exist.

## Visualize

```bash
agent-contracts visualize --module myapp.nodes --output ARCHITECTURE.md
agent-contracts visualize --file ./nodes.py --output -
```

- `--module` / `--file`: Same loading behavior as `validate` (repeatable).
- `--output` (default: `ARCHITECTURE.md`): Output file path. Use `-` to print to stdout.
- If your app already has a compiled LangGraph, pass it to the visualizer via `--graph-module` (recommended for app-specific entrypoints/state):

```bash
agent-contracts visualize --module myapp.nodes --graph-module myapp.graph --graph-func get_graph --output -
```

- `--graph-module`: Python module path to import (e.g. `myapp.graph`). The CLI loads the callable defined by `--graph-func` from that module.
- `--graph-func` (default: `get_graph`): Function name that returns either a compiled graph, or a graph object with `.compile()`.
- Otherwise, the CLI may compile a best-effort LangGraph from the registry to include the `LangGraph Node Flow` section (this can differ from your app’s real graph).

## Diff

```bash
agent-contracts diff --from-module myapp.v1.nodes --to-module myapp.v2.nodes
agent-contracts diff --from-file ./old_nodes.py --to-file ./new_nodes.py
```

- `--from-module/--to-module` (repeatable): Source modules for “before” and “after”.
- `--from-file/--to-file` (repeatable): Source files for “before” and “after”.

Exit code: `2` when breaking changes are detected, otherwise `0`.
