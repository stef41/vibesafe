"""Tests for vibesafe.sarif — SARIF 2.1.0 output format."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from vibesafe.sarif import (
    SARIF_SCHEMA,
    SARIF_VERSION,
    SarifReport,
    SarifResult,
    from_scan_results,
    sarif_level,
)


# ------------------------------------------------------------------
# sarif_level mapping
# ------------------------------------------------------------------

def test_sarif_level_error():
    assert sarif_level("error") == "error"


def test_sarif_level_critical():
    assert sarif_level("critical") == "error"


def test_sarif_level_warning():
    assert sarif_level("warning") == "warning"


def test_sarif_level_info():
    assert sarif_level("info") == "note"


def test_sarif_level_unknown_defaults_to_warning():
    assert sarif_level("banana") == "warning"


def test_sarif_level_case_insensitive():
    assert sarif_level("WARNING") == "warning"
    assert sarif_level("Error") == "error"


# ------------------------------------------------------------------
# SarifResult
# ------------------------------------------------------------------

def test_sarif_result_to_dict_minimal():
    r = SarifResult(rule_id="VS001", message="bad code")
    d = r.to_dict()
    assert d["ruleId"] == "VS001"
    assert d["message"]["text"] == "bad code"
    assert "locations" not in d


def test_sarif_result_to_dict_with_location():
    r = SarifResult(
        rule_id="VS002", message="issue", level="error",
        file_path="src/app.py", start_line=10, end_line=12, snippet="x = eval(y)",
    )
    d = r.to_dict()
    loc = d["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == "src/app.py"
    assert loc["region"]["startLine"] == 10
    assert loc["region"]["endLine"] == 12
    assert loc["region"]["snippet"]["text"] == "x = eval(y)"


# ------------------------------------------------------------------
# SarifReport
# ------------------------------------------------------------------

def test_empty_report_structure():
    report = SarifReport()
    d = report.to_dict()
    assert d["$schema"] == SARIF_SCHEMA
    assert d["version"] == SARIF_VERSION
    assert len(d["runs"]) == 1
    assert d["runs"][0]["results"] == []


def test_add_result_increments_count():
    report = SarifReport()
    assert report.result_count == 0
    report.add_result(SarifResult(rule_id="R1", message="m"))
    assert report.result_count == 1


def test_add_results_bulk():
    report = SarifReport()
    report.add_results([
        SarifResult(rule_id="R1", message="m1"),
        SarifResult(rule_id="R2", message="m2"),
    ])
    assert report.result_count == 2


def test_tool_metadata():
    report = SarifReport(tool_name="mytool", tool_version="1.0.0")
    driver = report.to_dict()["runs"][0]["tool"]["driver"]
    assert driver["name"] == "mytool"
    assert driver["version"] == "1.0.0"


def test_by_level():
    report = SarifReport()
    report.add_results([
        SarifResult(rule_id="R1", message="a", level="error"),
        SarifResult(rule_id="R2", message="b", level="warning"),
        SarifResult(rule_id="R3", message="c", level="error"),
    ])
    groups = report.by_level()
    assert len(groups["error"]) == 2
    assert len(groups["warning"]) == 1


def test_by_rule():
    report = SarifReport()
    report.add_results([
        SarifResult(rule_id="R1", message="a"),
        SarifResult(rule_id="R1", message="b"),
        SarifResult(rule_id="R2", message="c"),
    ])
    groups = report.by_rule()
    assert len(groups["R1"]) == 2
    assert len(groups["R2"]) == 1


def test_to_json_is_valid():
    report = SarifReport()
    report.add_result(SarifResult(rule_id="R1", message="m"))
    data = json.loads(report.to_json())
    assert data["version"] == SARIF_VERSION


def test_to_file(tmp_path):
    report = SarifReport()
    report.add_result(SarifResult(rule_id="R1", message="m"))
    path = str(tmp_path / "out.sarif.json")
    report.to_file(path)
    with open(path) as fh:
        data = json.load(fh)
    assert data["version"] == SARIF_VERSION
    assert len(data["runs"][0]["results"]) == 1


def test_rules_collected_from_results():
    report = SarifReport()
    report.add_results([
        SarifResult(rule_id="VS001", message="a"),
        SarifResult(rule_id="VS001", message="b"),
        SarifResult(rule_id="VS002", message="c"),
    ])
    rules = report.to_dict()["runs"][0]["tool"]["driver"]["rules"]
    rule_ids = {r["id"] for r in rules}
    assert rule_ids == {"VS001", "VS002"}


# ------------------------------------------------------------------
# from_scan_results converter
# ------------------------------------------------------------------

def test_from_scan_results_basic():
    items = [
        {"code": "VS001", "message": "eval usage", "severity": "error", "path": "a.py", "line": 5},
        {"code": "VS002", "message": "hardcoded secret", "severity": "warning"},
    ]
    report = from_scan_results(items)
    assert report.result_count == 2
    d = report.to_dict()
    assert d["runs"][0]["results"][0]["level"] == "error"
    assert d["runs"][0]["results"][1]["level"] == "warning"


def test_from_scan_results_missing_keys():
    items = [{"code": "X", "message": "m"}]
    report = from_scan_results(items)
    assert report.result_count == 1
    r = report.to_dict()["runs"][0]["results"][0]
    assert r["level"] == "warning"


def test_from_scan_results_empty():
    report = from_scan_results([])
    assert report.result_count == 0
