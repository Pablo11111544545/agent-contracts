"""Command-line interface for agent-contracts."""
from __future__ import annotations

import argparse
import importlib
import runpy
import sys
from pathlib import Path
from typing import Iterable

from agent_contracts import (
    ContractValidator,
    ContractVisualizer,
    get_node_registry,
    reset_registry,
)
from agent_contracts.contract_diff import diff_contracts


def _load_sources(modules: Iterable[str], files: Iterable[str]) -> None:
    """Load modules and files that register nodes."""
    for module_name in modules:
        _import_module(module_name)
    for file_path in files:
        _run_file(file_path)


def _import_module(module_name: str) -> None:
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


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
    visualizer = ContractVisualizer(registry)
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


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    exit_code = args.func(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
