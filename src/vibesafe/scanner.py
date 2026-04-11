"""Core scanner that orchestrates all checks."""

from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger("vibesafe")

from vibesafe.checks.security import check_security
_log = logging.getLogger("vibesafe")

from vibesafe.checks.secrets import check_secrets
_log = logging.getLogger("vibesafe")

from vibesafe.checks.imports import check_imports
_log = logging.getLogger("vibesafe")

from vibesafe.checks.dead_code import check_dead_code
_log = logging.getLogger("vibesafe")

from vibesafe.checks.patterns import check_ai_patterns


@dataclass
class Issue:
    """A single issue found during scanning."""

    path: str
    line: int
    column: int
    severity: str  # "error", "warning", "info"
    code: str
    message: str
    category: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column} [{self.severity}] {self.code}: {self.message}"


@dataclass
class ScanResult:
    """Result of scanning one or more files."""

    issues: list[Issue] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "info")

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0

    def __str__(self) -> str:
        lines = []
        for issue in sorted(self.issues, key=lambda i: (i.path, i.line)):
            lines.append(str(issue))
        lines.append(
            f"\n{self.files_scanned} files scanned: "
            f"{self.error_count} errors, {self.warning_count} warnings, {self.info_count} info"
        )
        return "\n".join(lines)


ALL_CHECKS = [
    check_security,
    check_secrets,
    check_imports,
    check_dead_code,
    check_ai_patterns,
]


class Scanner:
    """Main scanner that runs all checks on Python files."""

    def __init__(
        self,
        checks: Optional[list] = None,
        exclude_dirs: Optional[set] = None,
        severity_threshold: str = "info",
    ):
        self.checks = checks or ALL_CHECKS
        self.exclude_dirs = exclude_dirs or {
            ".git", ".venv", "venv", "node_modules", "__pycache__",
            ".mypy_cache", ".pytest_cache", ".tox", "dist", "build",
            ".eggs",
        }
        self._severity_order = {"error": 0, "warning": 1, "info": 2}
        self.severity_threshold = severity_threshold

    def scan_file(self, path: str | Path) -> list[Issue]:
        """Scan a single Python file."""
        path = Path(path)
        if not path.exists() or path.suffix != ".py":
            return []

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        try:
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, ValueError):
            return [Issue(
                path=str(path), line=1, column=0,
                severity="error", code="VS000",
                message="Syntax error: file could not be parsed",
                category="syntax",
            )]

        issues: list[Issue] = []
        for check in self.checks:
            try:
                found = check(str(path), tree, source)
                issues.extend(found)
            except Exception as exc:
                _log.warning("Check %s failed: %s", getattr(check, '__name__', check), exc)

        threshold = self._severity_order.get(self.severity_threshold, 2)
        issues = [i for i in issues if self._severity_order.get(i.severity, 2) <= threshold]
        return issues

    def scan_directory(self, path: str | Path) -> ScanResult:
        """Scan all Python files in a directory recursively."""
        path = Path(path)
        result = ScanResult()

        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for f in files:
                if f.endswith(".py"):
                    fpath = Path(root) / f
                    issues = self.scan_file(fpath)
                    result.issues.extend(issues)
                    result.files_scanned += 1

        return result

    def scan_code(self, code: str, filename: str = "<string>") -> list[Issue]:
        """Scan a code snippet."""
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError:
            return [Issue(
                path=filename, line=1, column=0,
                severity="error", code="VS000",
                message="Syntax error: code could not be parsed",
                category="syntax",
            )]

        issues: list[Issue] = []
        for check in self.checks:
            try:
                found = check(filename, tree, code)
                issues.extend(found)
            except Exception as exc:
                _log.warning("Check %s failed: %s", getattr(check, '__name__', check), exc)

        threshold = self._severity_order.get(self.severity_threshold, 2)
        issues = [i for i in issues if self._severity_order.get(i.severity, 2) <= threshold]
        return issues


def scan_file(path: str | Path) -> list[Issue]:
    """Convenience function to scan a single file."""
    return Scanner().scan_file(path)


def scan_directory(path: str | Path) -> ScanResult:
    """Convenience function to scan a directory."""
    return Scanner().scan_directory(path)


def scan_code(code: str, filename: str = "<string>") -> list[Issue]:
    """Convenience function to scan a code snippet."""
    return Scanner().scan_code(code, filename)
