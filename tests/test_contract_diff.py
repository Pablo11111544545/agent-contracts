"""Tests for contract diff utilities."""
from agent_contracts.contract_diff import ContractDiffReport, NodeChange, diff_contracts


def test_diff_contracts_detects_changes():
    before = {
        "alpha": {
            "name": "alpha",
            "description": "Alpha",
            "reads": ["request"],
            "writes": ["response"],
            "services": [],
            "requires_llm": False,
            "supervisor": "main",
            "trigger_conditions": [{"priority": 10}],
            "is_terminal": False,
            "icon": None,
        }
    }
    after = {
        "alpha": {
            "name": "alpha",
            "description": "Alpha v2",
            "reads": ["request", "context"],
            "writes": ["response"],
            "services": [],
            "requires_llm": True,
            "supervisor": "main",
            "trigger_conditions": [{"priority": 10}, {"priority": 5}],
            "is_terminal": False,
            "icon": None,
        },
        "beta": {
            "name": "beta",
            "description": "Beta",
            "reads": ["request"],
            "writes": ["response"],
            "services": [],
            "requires_llm": False,
            "supervisor": "main",
            "trigger_conditions": [{"priority": 1}],
            "is_terminal": True,
            "icon": None,
        },
    }

    report = diff_contracts(before, after)

    assert report.added == ["beta"]
    assert report.removed == []
    assert report.changes
    assert report.has_breaking()

    change = report.changes[0]
    assert change.node == "alpha"
    assert change.severity == "breaking"
    assert any("requires_llm" in detail for detail in change.details)


def test_diff_contracts_removed_node_is_breaking():
    before = {
        "alpha": {
            "name": "alpha",
            "description": "Alpha",
            "reads": ["request"],
            "writes": ["response"],
            "services": [],
            "requires_llm": False,
            "supervisor": "main",
            "trigger_conditions": [{"priority": 10}],
            "is_terminal": False,
            "icon": None,
        }
    }
    after = {}

    report = diff_contracts(before, after)
    assert report.removed == ["alpha"]
    assert report.has_breaking()


def test_diff_contracts_nonbreaking_description_change():
    before = {
        "alpha": {
            "name": "alpha",
            "description": "Alpha",
            "reads": ["request"],
            "writes": ["response"],
            "services": [],
            "requires_llm": False,
            "supervisor": "main",
            "trigger_conditions": [{"priority": 10}],
            "is_terminal": False,
            "icon": None,
        }
    }
    after = {
        "alpha": {
            "name": "alpha",
            "description": "Alpha v2",
            "reads": ["request"],
            "writes": ["response"],
            "services": [],
            "requires_llm": False,
            "supervisor": "main",
            "trigger_conditions": [{"priority": 10}],
            "is_terminal": False,
            "icon": None,
        }
    }

    report = diff_contracts(before, after)
    assert report.changes
    assert report.changes[0].severity == "nonbreaking"
    assert not report.has_breaking()
    assert "Nonbreaking changes" in report.to_text()


def test_report_to_text_no_changes():
    report = ContractDiffReport(added=[], removed=[], changes=[])
    assert report.to_text() == "No changes detected."


def test_report_to_text_grouping():
    report = ContractDiffReport(
        added=["beta"],
        removed=["alpha"],
        changes=[
            NodeChange(node="gamma", severity="behavioral", details=["writes: +audit"]),
            NodeChange(node="delta", severity="breaking", details=["supervisor: a -> b"]),
        ],
    )
    text = report.to_text()
    assert "Added nodes" in text
    assert "Removed nodes" in text
    assert "Breaking changes" in text
    assert "Behavioral changes" in text
