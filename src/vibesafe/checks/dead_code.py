"""Detect dead code patterns common in AI-generated code."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibesafe.scanner import Issue


def check_dead_code(path: str, tree: ast.AST, source: str) -> list[Issue]:
    """Detect dead code, unused imports, and unreachable code."""
    from vibesafe.scanner import Issue

    issues: list[Issue] = []

    # Collect imported names
    imported: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imported[name] = node
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                imported[name] = node

    # Collect used names
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                used.add(root.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    used.add(dec.id)
        elif isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name):
                    used.add(base.id)
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    used.add(dec.id)

    # Check for __all__ exports
    exported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                exported.add(elt.value)

    # VS400: Unused imports
    for name, node in imported.items():
        if name not in used and name != "_" and name not in exported:
            issues.append(Issue(
                path=path, line=node.lineno, column=node.col_offset,
                severity="warning", code="VS400",
                message=f"Unused import: '{name}'",
                category="dead-code",
            ))

    # VS401: Unreachable code
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _check_unreachable(path, node.body, issues)
        elif isinstance(node, (ast.For, ast.While)):
            _check_unreachable(path, node.body, issues)
        elif isinstance(node, ast.If):
            _check_unreachable(path, node.body, issues)
            _check_unreachable(path, node.orelse, issues)

    # VS402: Empty except with pass
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                issues.append(Issue(
                    path=path, line=node.lineno, column=node.col_offset,
                    severity="warning", code="VS402",
                    message="Empty except block - errors silently swallowed",
                    category="dead-code",
                ))

    # VS403: Bare except
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(Issue(
                path=path, line=node.lineno, column=node.col_offset,
                severity="warning", code="VS403",
                message="Bare except - catches SystemExit and KeyboardInterrupt",
                category="dead-code",
            ))

    return issues


def _check_unreachable(path: str, body: list, issues: list) -> None:
    """Check for statements after return/raise/break/continue."""
    from vibesafe.scanner import Issue

    for i, stmt in enumerate(body):
        if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            if i + 1 < len(body):
                next_stmt = body[i + 1]
                issues.append(Issue(
                    path=path, line=next_stmt.lineno, column=next_stmt.col_offset,
                    severity="warning", code="VS401",
                    message="Unreachable code after return/raise/break/continue",
                    category="dead-code",
                ))
                break
