"""Tests for CLI helpers."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

from agent_contracts import reset_registry
from agent_contracts.cli import (
    _ensure_sources,
    _handle_diff,
    _handle_validate,
    _handle_visualize,
    _import_module,
    _try_compile_langgraph,
    build_parser,
)


NODE_TEMPLATE = """from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    get_node_registry,
)


class SampleNode(ModularNode):
    CONTRACT = NodeContract(
        name="{node_name}",
        description="sample node",
        reads=["request"],
        writes=["response"],
        services={services},
        supervisor="{supervisor}",
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={{"ok": True}})


registry = get_node_registry()
{extra}
registry.register(SampleNode)
"""


def _write_module(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _node_module_content(
    *,
    node_name: str = "sample",
    services: list[str] | None = None,
    supervisor: str = "main",
    extra: str = "",
) -> str:
    return NODE_TEMPLATE.format(
        node_name=node_name,
        services=services or [],
        supervisor=supervisor,
        extra=extra,
    )


def test_ensure_sources_requires_input():
    with pytest.raises(SystemExit):
        _ensure_sources([], [])


def test_import_module_reload(tmp_path: Path):
    module_path = tmp_path / "dummy_mod.py"
    module_path.write_text("VALUE = 1\n", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        _import_module("dummy_mod")
        import dummy_mod  # noqa: F401
        assert dummy_mod.VALUE == 1
        _import_module("dummy_mod")
        assert "dummy_mod" in sys.modules
    finally:
        sys.path = [p for p in sys.path if p != str(tmp_path)]
        sys.modules.pop("dummy_mod", None)


def test_validate_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    reset_registry()
    module_path = tmp_path / "nodes_ok.py"
    _write_module(module_path, _node_module_content())

    args = type("Args", (), {
        "module": [],
        "file": [str(module_path)],
        "known_services": [],
        "strict": False,
    })()

    exit_code = _handle_validate(args)
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "All validations passed" in output


def test_validate_strict_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    reset_registry()
    module_path = tmp_path / "nodes_strict.py"
    _write_module(
        module_path,
        _node_module_content(services=["cache_service"]),
    )

    args = type("Args", (), {
        "module": [],
        "file": [str(module_path)],
        "known_services": ["db_service"],
        "strict": True,
    })()

    exit_code = _handle_validate(args)
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "STRICT:" in output


def test_visualize_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    reset_registry()
    module_path = tmp_path / "nodes_vis.py"
    _write_module(module_path, _node_module_content())

    args = type("Args", (), {
        "module": [],
        "file": [str(module_path)],
        "output": "-",
    })()

    exit_code = _handle_visualize(args)
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Agent Architecture" in output


def test_visualize_file_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    reset_registry()
    module_path = tmp_path / "nodes_vis_file.py"
    _write_module(module_path, _node_module_content())
    output_path = tmp_path / "ARCH.md"

    args = type("Args", (), {
        "module": [],
        "file": [str(module_path)],
        "output": str(output_path),
    })()

    exit_code = _handle_visualize(args)
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Wrote" in output
    doc = output_path.read_text(encoding="utf-8")
    assert doc.startswith("# ")
    assert "Agent Architecture" in doc


def test_visualize_uses_graph_module_for_langgraph_flow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    reset_registry()
    module_path = tmp_path / "nodes_vis_with_graph.py"
    _write_module(module_path, _node_module_content())

    graph_module_path = tmp_path / "graph_provider.py"
    graph_module_path.write_text(
        """
class GraphObj:
    def draw_mermaid(self):
        return "flowchart TD\\n  A --> B"


class Compiled:
    def get_graph(self):
        return GraphObj()


def get_graph():
    return Compiled()
""".lstrip(),
        encoding="utf-8",
    )

    sys.path.insert(0, str(tmp_path))
    try:
        args = type("Args", (), {
            "module": [],
            "file": [str(module_path)],
            "graph_module": "graph_provider",
            "graph_func": "get_graph",
            "output": "-",
        })()

        exit_code = _handle_visualize(args)
        output = capsys.readouterr().out
        assert exit_code == 0
        assert "LangGraph Node Flow" in output
        assert "A --> B" in output
    finally:
        sys.path = [p for p in sys.path if p != str(tmp_path)]
        sys.modules.pop("graph_provider", None)


def test_visualize_module_calls_register_all_nodes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    reset_registry()
    pkg = tmp_path / "app" / "agents" / "impl"
    pkg.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "agents" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "agents" / "impl" / "__init__.py").write_text(
        """
from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    get_node_registry,
)


class SampleNode(ModularNode):
    CONTRACT = NodeContract(
        name="sample",
        description="sample node",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(response={"ok": True})


def register_all_nodes(registry=None) -> None:
    (registry or get_node_registry()).register(SampleNode)
""".lstrip(),
        encoding="utf-8",
    )

    sys.path.insert(0, str(tmp_path))
    try:
        args = type("Args", (), {
            "module": ["app.agents.impl"],
            "file": [],
            "output": "-",
        })()

        exit_code = _handle_visualize(args)
        output = capsys.readouterr().out
        assert exit_code == 0
        assert "`sample`" in output
    finally:
        sys.path = [p for p in sys.path if p != str(tmp_path)]
        sys.modules.pop("app.agents.impl", None)


def test_build_langgraph_state_schema_includes_registered_slices(tmp_path: Path):
    from agent_contracts.cli import _build_langgraph_state_schema
    from agent_contracts import get_node_registry

    reset_registry()
    module_path = tmp_path / "nodes_schema.py"
    _write_module(
        module_path,
        _node_module_content(
            extra="""
registry.add_valid_slice("shopping")


class ExtraSliceNode(ModularNode):
    CONTRACT = NodeContract(
        name="extra_slice",
        description="extra",
        reads=["shopping"],
        writes=["shopping"],
        supervisor="main",
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(shopping={})


registry.register(ExtraSliceNode)
""".strip(),
        ),
    )

    args = type("Args", (), {
        "module": [],
        "file": [str(module_path)],
        "known_services": [],
        "strict": False,
    })()
    _handle_validate(args)

    schema = _build_langgraph_state_schema(get_node_registry())
    assert "request" in schema.__annotations__
    assert "response" in schema.__annotations__
    assert "_internal" in schema.__annotations__
    assert "shopping" in schema.__annotations__


def test_try_compile_langgraph_uses_entrypoint_for_all_supervisors(monkeypatch: pytest.MonkeyPatch):
    from agent_contracts import NodeRegistry, ModularNode, NodeContract, TriggerCondition

    class NodeA(ModularNode):
        CONTRACT = NodeContract(
            name="a",
            description="a",
            reads=["request"],
            writes=["response"],
            supervisor="card",
            trigger_conditions=[TriggerCondition(priority=1)],
        )

        async def execute(self, inputs, config=None):
            raise NotImplementedError

    class NodeB(ModularNode):
        CONTRACT = NodeContract(
            name="b",
            description="b",
            reads=["request"],
            writes=["response"],
            supervisor="shopping",
            trigger_conditions=[TriggerCondition(priority=1)],
        )

        async def execute(self, inputs, config=None):
            raise NotImplementedError

    reg = NodeRegistry()
    reg.register(NodeA)
    reg.register(NodeB)

    called: dict = {}

    class FakeCompiled:
        pass

    class FakeGraph:
        def compile(self):
            return FakeCompiled()

    def fake_build_graph_from_registry(**kwargs):
        called.update(kwargs)
        return FakeGraph()

    import agent_contracts

    monkeypatch.setattr(agent_contracts, "build_graph_from_registry", fake_build_graph_from_registry)

    compiled = _try_compile_langgraph(reg)
    assert compiled is not None
    assert called["supervisors"] == ["card", "shopping"]
    assert called["entrypoint"][0] == "entry"


def test_diff_breaking(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    reset_registry()
    before_path = tmp_path / "nodes_before.py"
    after_path = tmp_path / "nodes_after.py"
    _write_module(before_path, _node_module_content(supervisor="main"))
    _write_module(after_path, _node_module_content(supervisor="secondary"))

    args = type("Args", (), {
        "from_module": [],
        "from_file": [str(before_path)],
        "to_module": [],
        "to_file": [str(after_path)],
    })()

    exit_code = _handle_diff(args)
    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Breaking changes" in output


def test_diff_no_changes(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    reset_registry()
    before_path = tmp_path / "nodes_before_same.py"
    after_path = tmp_path / "nodes_after_same.py"
    content = _node_module_content()
    _write_module(before_path, content)
    _write_module(after_path, content)

    args = type("Args", (), {
        "from_module": [],
        "from_file": [str(before_path)],
        "to_module": [],
        "to_file": [str(after_path)],
    })()

    exit_code = _handle_diff(args)
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "No changes detected" in output


def test_main_entrypoint(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    reset_registry()
    module_path = tmp_path / "nodes_main.py"
    _write_module(module_path, _node_module_content())

    parser = build_parser()
    args = parser.parse_args(["validate", "--file", str(module_path)])
    exit_code = args.func(args)
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "All validations passed" in output

    monkeypatch.setattr(sys, "argv", ["agent-contracts", "validate", "--file", str(module_path)])
    from agent_contracts import cli
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
