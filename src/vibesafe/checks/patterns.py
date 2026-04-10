"""Detect AI-specific anti-patterns in generated code."""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibesafe.scanner import Issue


def check_ai_patterns(path: str, tree: ast.AST, source: str) -> list[Issue]:
    """Detect anti-patterns commonly produced by AI code generators."""
    from vibesafe.scanner import Issue

    issues: list[Issue] = []
    lines = source.splitlines()

    # VS500: TODO/FIXME/HACK markers
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            upper = stripped.upper()
            for marker in ("TODO", "FIXME", "HACK", "XXX"):
                if marker in upper:
                    issues.append(Issue(
                        path=path, line=i, column=0,
                        severity="info", code="VS500",
                        message=f"{marker} comment - AI may have left incomplete implementation",
                        category="pattern",
                    ))
                    break

    # VS501: Empty function body (pass or ...)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if len(node.body) == 1:
                stmt = node.body[0]
                if isinstance(stmt, ast.Pass):
                    issues.append(Issue(
                        path=path, line=node.lineno, column=node.col_offset,
                        severity="warning", code="VS501",
                        message=f"Function '{node.name}' has empty body (pass) - placeholder",
                        category="pattern",
                    ))
                elif (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is ...
                ):
                    issues.append(Issue(
                        path=path, line=node.lineno, column=node.col_offset,
                        severity="warning", code="VS501",
                        message=f"Function '{node.name}' has empty body (...) - placeholder",
                        category="pattern",
                    ))

    # VS502: raise NotImplementedError (stub)
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc:
            if isinstance(node.exc, ast.Call):
                if isinstance(node.exc.func, ast.Name) and node.exc.func.id == "NotImplementedError":
                    issues.append(Issue(
                        path=path, line=node.lineno, column=node.col_offset,
                        severity="warning", code="VS502",
                        message="NotImplementedError raised - stub implementation",
                        category="pattern",
                    ))

    # VS503: Excessive Any type hints
    any_count = sum(
        1 for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "Any"
    )
    if any_count > 5:
        issues.append(Issue(
            path=path, line=1, column=0,
            severity="info", code="VS503",
            message=f"Excessive use of 'Any' type hint ({any_count} occurrences)",
            category="pattern",
        ))

    # VS504: Hardcoded localhost
    for i, line in enumerate(lines, 1):
        if not line.strip().startswith("#"):
            if re.search(r'https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?', line):
                issues.append(Issue(
                    path=path, line=i, column=0,
                    severity="info", code="VS504",
                    message="Hardcoded localhost URL - use configuration instead",
                    category="pattern",
                ))

    # VS506: Star import
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    issues.append(Issue(
                        path=path, line=node.lineno, column=node.col_offset,
                        severity="warning", code="VS506",
                        message=f"Star import from '{node.module}' - pollutes namespace",
                        category="pattern",
                    ))

    # VS507: Mutable default arguments
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append(Issue(
                        path=path, line=node.lineno, column=node.col_offset,
                        severity="warning", code="VS507",
                        message=f"Mutable default argument in '{node.name}()' - use None instead",
                        category="pattern",
                    ))

    return issues
