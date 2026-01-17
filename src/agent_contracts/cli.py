"""Command-line interface for agent-contracts."""
from __future__ import annotations

import argparse
import importlib
import inspect
import os
import runpy
import sys
from pathlib import Path
from typing import Annotated, Any, Iterable, TypedDict

from agent_contracts import (
    ContractValidator,
    ContractVisualizer,
    get_node_registry,
    reset_registry,
)
from agent_contracts.contract_diff import diff_contracts


def _debug_enabled() -> bool:
    return os.getenv("AGENT_CONTRACTS_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug(message: str) -> None:
    if _debug_enabled():
        print(f"[agent-contracts][debug] {message}", file=sys.stderr)


def _load_sources(modules: Iterable[str], files: Iterable[str]) -> None:
    """Load modules and files that register nodes."""
    for module_name in modules:
        _import_module(module_name)
    for file_path in files:
        _run_file(file_path)


def _import_module(module_name: str) -> None:
    registry = get_node_registry()
    before_count = len(registry.get_all_nodes())
    _debug(f"Importing module: {module_name} (nodes_before={before_count})")
    if module_name in sys.modules:
        module = importlib.reload(sys.modules[module_name])
    else:
        module = importlib.import_module(module_name)

    after_count = len(registry.get_all_nodes())
    _debug(f"Imported module: {module_name} (nodes_after={after_count})")
    if after_count == before_count:
        _maybe_call_register_all_nodes(module)
        _debug(
            f"After register_all_nodes probe: {module_name} "
            f"(nodes_now={len(registry.get_all_nodes())})"
        )


def _maybe_call_register_all_nodes(module: object) -> None:
    register = getattr(module, "register_all_nodes", None)
    if not callable(register):
        _debug(f"No register_all_nodes() in module: {getattr(module, '__name__', module)}")
        return

    try:
        signature = inspect.signature(register)
        required = [
            p
            for p in signature.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(required) == 0:
            _debug("Calling register_all_nodes() with no args")
            register()
            return
        if len(required) == 1:
            _debug("Calling register_all_nodes(registry)")
            register(get_node_registry())
            return
    except (TypeError, ValueError):
        pass

    try:
        _debug("Calling register_all_nodes() (fallback)")
        register()
    except TypeError:
        _debug("Calling register_all_nodes(registry) (fallback)")
        register(get_node_registry())


def _run_file(file_path: str) -> None:
    path = Path(file_path).resolve()
    parent = str(path.parent)
    sys.path.insert(0, parent)
    try:
        runpy.run_path(str(path), run_name="__main__")
    finally:
        if sys.path and sys.path[0] == parent:
            sys.path.pop(0)


def _load_registry_snapshot(modules: Iterable[str], files: Iterable[str]) -> dict:
    reset_registry()
    _load_sources(modules, files)
    registry = get_node_registry()
    return registry.export_contracts()


def _ensure_sources(modules: list[str], files: list[str]) -> None:
    if not modules and not files:
        raise SystemExit("Specify at least one --module or --file.")


def _add_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--module",
        action="append",
        default=[],
        help="Python module path that registers nodes (repeatable).",
    )
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Python file that registers nodes (repeatable).",
    )


def _handle_validate(args: argparse.Namespace) -> int:
    _ensure_sources(args.module, args.file)
    reset_registry()
    _load_sources(args.module, args.file)
    registry = get_node_registry()
    known_services = set(args.known_services) if args.known_services else None
    validator = ContractValidator(
        registry,
        known_services=known_services,
        strict=args.strict,
    )
    result = validator.validate()
    print(result)
    return 1 if result.has_errors else 0


def _handle_visualize(args: argparse.Namespace) -> int:
    _ensure_sources(args.module, args.file)
    reset_registry()
    _load_sources(args.module, args.file)
    registry = get_node_registry()
    _debug(f"Visualize: registry_nodes={len(registry.get_all_nodes())}")
    compiled = _load_compiled_graph_from_module(args) or _try_compile_langgraph(registry)
    visualizer = ContractVisualizer(registry, graph=compiled)
    doc = visualizer.generate_architecture_doc()
    output = Path(args.output)
    if args.output == "-":
        print(doc)
    else:
        output.write_text(doc, encoding="utf-8")
        print(f"Wrote {output}")
    return 0


def _handle_diff(args: argparse.Namespace) -> int:
    _ensure_sources(args.from_module, args.from_file)
    _ensure_sources(args.to_module, args.to_file)

    before = _load_registry_snapshot(args.from_module, args.from_file)
    after = _load_registry_snapshot(args.to_module, args.to_file)

    report = diff_contracts(before, after)
    print(report.to_text())
    return 2 if report.has_breaking() else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-contracts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate node contracts")
    _add_source_args(validate)
    validate.add_argument(
        "--known-service",
        dest="known_services",
        action="append",
        default=[],
        help="Known service name (repeatable).",
    )
    validate.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors.",
    )
    validate.set_defaults(func=_handle_validate)

    visualize = subparsers.add_parser("visualize", help="Generate architecture docs")
    _add_source_args(visualize)
    visualize.add_argument(
        "--graph-module",
        default=None,
        help="Python module path that provides a compiled graph (e.g. 'app.agents.graph').",
    )
    visualize.add_argument(
        "--graph-func",
        default="get_graph",
        help="Callable in --graph-module that returns a compiled graph (default: get_graph).",
    )
    visualize.add_argument(
        "--output",
        default="ARCHITECTURE.md",
        help="Output file path, or '-' for stdout.",
    )
    visualize.set_defaults(func=_handle_visualize)

    diff = subparsers.add_parser("diff", help="Diff two contract sets")
    diff.add_argument(
        "--from-module",
        action="append",
        default=[],
        help="Source module for 'before' contracts (repeatable).",
    )
    diff.add_argument(
        "--from-file",
        action="append",
        default=[],
        help="Source file for 'before' contracts (repeatable).",
    )
    diff.add_argument(
        "--to-module",
        action="append",
        default=[],
        help="Source module for 'after' contracts (repeatable).",
    )
    diff.add_argument(
        "--to-file",
        action="append",
        default=[],
        help="Source file for 'after' contracts (repeatable).",
    )
    diff.set_defaults(func=_handle_diff)

    return parser


def _try_compile_langgraph(registry) -> object | None:
    supervisors = sorted(
        {
            registry.get_contract(name).supervisor
            for name in registry.get_all_nodes()
            if registry.get_contract(name)
        }
    )
    if not supervisors:
        _debug("LangGraph compile skipped: no supervisors found")
        return None

    try:
        from agent_contracts import build_graph_from_registry
    except Exception:
        _debug("LangGraph compile skipped: failed to import build_graph_from_registry")
        return None

    try:
        state_schema = _build_langgraph_state_schema(registry)
        _debug(
            f"LangGraph state schema: keys={len(getattr(state_schema, '__annotations__', {}))}"
        )
        _debug(f"LangGraph compile: supervisors={supervisors}")

        async def entry_node(_: dict) -> dict:
            return {}

        def entry_route(_: dict) -> str:
            return f"{supervisors[0]}_supervisor"

        graph = build_graph_from_registry(
            registry=registry,
            supervisors=supervisors,
            state_class=state_schema,
            entrypoint=("entry", entry_node, entry_route),
        )
        compiled = graph.compile()
        _debug("LangGraph compile: ok")
        return compiled
    except Exception:
        _debug("LangGraph compile failed (exception suppressed)")
        return None


def _load_compiled_graph_from_module(args: argparse.Namespace) -> object | None:
    module_name = getattr(args, "graph_module", None)
    if not module_name:
        return None

    func_name = getattr(args, "graph_func", "get_graph") or "get_graph"
    _debug(f"Loading compiled graph from module: {module_name}.{func_name}()")
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        _debug(f"Failed to import graph module: {type(e).__name__}: {e}")
        return None

    fn = getattr(module, func_name, None)
    if not callable(fn):
        _debug("Graph loader: target is not callable")
        return None

    try:
        graph_obj = fn()
    except Exception as e:
        _debug(f"Graph loader: callable raised: {type(e).__name__}: {e}")
        return None

    if graph_obj is None:
        _debug("Graph loader: callable returned None")
        return None

    compile_fn = getattr(graph_obj, "compile", None)
    if callable(compile_fn):
        try:
            compiled = compile_fn()
            _debug("Graph loader: compiled via .compile()")
            return compiled
        except Exception as e:
            _debug(f"Graph loader: .compile() failed: {type(e).__name__}: {e}")
            return None

    _debug("Graph loader: using returned object as compiled graph")
    return graph_obj


def _merge_state_value(a: Any, b: Any) -> Any:
    if a is None:
        return b
    if b is None:
        return a
    if isinstance(a, dict) and isinstance(b, dict):
        merged = dict(a)
        merged.update(b)
        return merged
    return b


def _build_langgraph_state_schema(registry) -> type[TypedDict]:
    slices: set[str] = {"request", "response", "_internal"}
    for name in registry.get_all_nodes():
        contract = registry.get_contract(name)
        if contract:
            slices.update(contract.reads)
            slices.update(contract.writes)

    annotations = {slice_name: Annotated[dict, _merge_state_value] for slice_name in sorted(slices)}
    return TypedDict("AgentContractsState", annotations, total=False)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    exit_code = args.func(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
