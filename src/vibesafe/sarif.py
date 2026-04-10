"""SARIF 2.1.0 output format for vibesafe scan results."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json"
SARIF_VERSION = "2.1.0"

_SEVERITY_TO_SARIF = {
    "error": "error",
    "critical": "error",
    "warning": "warning",
    "info": "note",
    "note": "note",
    "none": "none",
}


def sarif_level(severity: str) -> str:
    """Map vibesafe severity string to a SARIF level."""
    return _SEVERITY_TO_SARIF.get(severity.lower(), "warning")


@dataclass
class SarifResult:
    """A single SARIF result entry."""

    rule_id: str
    message: str
    level: str = "warning"
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    snippet: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to SARIF result dict."""
        d: dict = {
            "ruleId": self.rule_id,
            "level": self.level,
            "message": {"text": self.message},
        }
        if self.file_path is not None:
            location: dict = {
                "physicalLocation": {
                    "artifactLocation": {"uri": self.file_path},
                }
            }
            region: dict = {}
            if self.start_line is not None:
                region["startLine"] = self.start_line
            if self.end_line is not None:
                region["endLine"] = self.end_line
            if self.snippet is not None:
                region["snippet"] = {"text": self.snippet}
            if region:
                location["physicalLocation"]["region"] = region
            d["locations"] = [location]
        return d


class SarifReport:
    """Build a SARIF 2.1.0 report."""

    def __init__(self, tool_name: str = "vibesafe", tool_version: str = "0.2.0") -> None:
        self.tool_name = tool_name
        self.tool_version = tool_version
        self._results: list[SarifResult] = []

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def add_result(self, result: SarifResult) -> None:
        self._results.append(result)

    def add_results(self, results: list[SarifResult]) -> None:
        self._results.extend(results)

    # ------------------------------------------------------------------
    # Properties / queries
    # ------------------------------------------------------------------

    @property
    def result_count(self) -> int:
        return len(self._results)

    def by_level(self) -> dict[str, list[SarifResult]]:
        """Group results by their SARIF level."""
        groups: dict[str, list[SarifResult]] = defaultdict(list)
        for r in self._results:
            groups[r.level].append(r)
        return dict(groups)

    def by_rule(self) -> dict[str, list[SarifResult]]:
        """Group results by rule ID."""
        groups: dict[str, list[SarifResult]] = defaultdict(list)
        for r in self._results:
            groups[r.rule_id].append(r)
        return dict(groups)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def _collect_rules(self) -> list[dict]:
        seen: dict[str, dict] = {}
        for r in self._results:
            if r.rule_id not in seen:
                seen[r.rule_id] = {"id": r.rule_id, "shortDescription": {"text": r.rule_id}}
        return list(seen.values())

    def to_dict(self) -> dict:
        """Return a full SARIF 2.1.0 schema-compliant dict."""
        return {
            "$schema": SARIF_SCHEMA,
            "version": SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": self.tool_name,
                            "version": self.tool_version,
                            "rules": self._collect_rules(),
                        }
                    },
                    "results": [r.to_dict() for r in self._results],
                }
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Return the SARIF report as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_file(self, path: str) -> None:
        """Write the SARIF report to *path*."""
        with open(path, "w") as fh:
            fh.write(self.to_json())


# ------------------------------------------------------------------
# Convenience converters
# ------------------------------------------------------------------


def from_scan_results(results: list[dict], tool_name: str = "vibesafe", tool_version: str = "0.2.0") -> SarifReport:
    """Convert a list of vibesafe scan result dicts to a :class:`SarifReport`.

    Each dict is expected to have keys matching
    :class:`vibesafe.scanner.Issue` attributes: ``code``, ``message``,
    ``severity``, and optionally ``path``, ``line``, ``column``.
    """
    report = SarifReport(tool_name=tool_name, tool_version=tool_version)
    for item in results:
        report.add_result(SarifResult(
            rule_id=item.get("code", "unknown"),
            message=item.get("message", ""),
            level=sarif_level(item.get("severity", "warning")),
            file_path=item.get("path"),
            start_line=item.get("line"),
            end_line=item.get("line"),
            snippet=item.get("snippet"),
        ))
    return report
