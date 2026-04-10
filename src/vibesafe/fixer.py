"""Auto-fixer for vibesafe issues."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from vibesafe.scanner import Issue, Scanner


@dataclass
class FixResult:
    """Result of applying fixes to a file."""

    path: str
    fixes_applied: list[str]
    original_source: str
    fixed_source: str

    @property
    def changed(self) -> bool:
        return self.original_source != self.fixed_source


# Codes that can be auto-fixed
FIXABLE_CODES = {"VS400", "VS506"}


def can_fix(issue: Issue) -> bool:
    """Check whether an issue can be auto-fixed."""
    return issue.code in FIXABLE_CODES


def fix_file(path: str | Path) -> FixResult:
    """Scan a file, apply all available fixes, and return the result."""
    path = Path(path)
    source = path.read_text(encoding="utf-8", errors="replace")
    scanner = Scanner()
    issues = scanner.scan_file(path)

    fixable = [i for i in issues if can_fix(i)]
    if not fixable:
        return FixResult(
            path=str(path), fixes_applied=[], original_source=source, fixed_source=source,
        )

    fixed_source = source
    applied: list[str] = []

    # Group by code and apply fixers
    vs400 = [i for i in fixable if i.code == "VS400"]
    if vs400:
        fixed_source, msgs = _fix_unused_imports(fixed_source, vs400)
        applied.extend(msgs)

    vs506 = [i for i in fixable if i.code == "VS506"]
    if vs506:
        fixed_source, msgs = _fix_star_imports(fixed_source, vs506)
        applied.extend(msgs)

    return FixResult(
        path=str(path), fixes_applied=applied,
        original_source=source, fixed_source=fixed_source,
    )


def fix_source(source: str, filename: str = "<string>") -> FixResult:
    """Fix issues in a source string."""
    scanner = Scanner()
    issues = scanner.scan_code(source, filename)

    fixable = [i for i in issues if can_fix(i)]
    if not fixable:
        return FixResult(
            path=filename, fixes_applied=[], original_source=source, fixed_source=source,
        )

    fixed_source = source
    applied: list[str] = []

    vs400 = [i for i in fixable if i.code == "VS400"]
    if vs400:
        fixed_source, msgs = _fix_unused_imports(fixed_source, vs400)
        applied.extend(msgs)

    vs506 = [i for i in fixable if i.code == "VS506"]
    if vs506:
        fixed_source, msgs = _fix_star_imports(fixed_source, vs506)
        applied.extend(msgs)

    return FixResult(
        path=filename, fixes_applied=applied,
        original_source=source, fixed_source=fixed_source,
    )


def _fix_unused_imports(source: str, issues: list[Issue]) -> tuple[str, list[str]]:
    """Remove unused imports from source code."""
    # Extract unused names from issue messages
    unused_names: set[str] = set()
    for issue in issues:
        match = re.search(r"Unused import: '([^']+)'", issue.message)
        if match:
            unused_names.add(match.group(1))

    if not unused_names:
        return source, []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, []

    lines = source.splitlines(keepends=True)
    lines_to_remove: set[int] = set()  # 0-indexed
    edits: list[tuple[int, str, str]] = []  # (line_idx, old_line, new_line)
    applied: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            remaining = []
            removed = []
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if name in unused_names:
                    removed.append(name)
                else:
                    remaining.append(alias)
            if removed:
                if not remaining:
                    # Remove the entire import line
                    lines_to_remove.add(node.lineno - 1)
                else:
                    # Reconstruct import with remaining names
                    parts = []
                    for alias in remaining:
                        if alias.asname:
                            parts.append(f"{alias.name} as {alias.asname}")
                        else:
                            parts.append(alias.name)
                    new_line = f"import {', '.join(parts)}\n"
                    edits.append((node.lineno - 1, lines[node.lineno - 1], new_line))
                for name in removed:
                    applied.append(f"Removed unused import '{name}'")

        elif isinstance(node, ast.ImportFrom):
            remaining = []
            removed = []
            for alias in node.names:
                if alias.name == "*":
                    remaining.append(alias)
                    continue
                name = alias.asname or alias.name
                if name in unused_names:
                    removed.append(name)
                else:
                    remaining.append(alias)
            if removed:
                if not remaining:
                    lines_to_remove.add(node.lineno - 1)
                    # Handle multi-line imports
                    if node.end_lineno and node.end_lineno > node.lineno:
                        for ln in range(node.lineno - 1, node.end_lineno):
                            lines_to_remove.add(ln)
                else:
                    parts = []
                    for alias in remaining:
                        if alias.asname:
                            parts.append(f"{alias.name} as {alias.asname}")
                        else:
                            parts.append(alias.name)
                    module = node.module or ""
                    level = "." * node.level
                    new_line = f"from {level}{module} import {', '.join(parts)}\n"
                    edits.append((node.lineno - 1, lines[node.lineno - 1], new_line))
                    # Remove continuation lines for multi-line imports
                    if node.end_lineno and node.end_lineno > node.lineno:
                        for ln in range(node.lineno, node.end_lineno):
                            lines_to_remove.add(ln)
                for name in removed:
                    applied.append(f"Removed unused import '{name}'")

    # Apply edits (lines to edit, then remove)
    for idx, _old, new in edits:
        if idx not in lines_to_remove:
            lines[idx] = new

    new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
    return "".join(new_lines), applied


def _fix_star_imports(source: str, issues: list[Issue]) -> tuple[str, list[str]]:
    """Replace star imports with explicit import (comment-based)."""
    # Star imports are hard to fix automatically without runtime info,
    # so we add a noqa-style comment suggesting manual fix
    applied: list[str] = []
    lines = source.splitlines(keepends=True)

    for issue in issues:
        idx = issue.line - 1
        if idx < len(lines) and "import *" in lines[idx]:
            if "# vibesafe: fix-manually" not in lines[idx]:
                lines[idx] = lines[idx].rstrip() + "  # vibesafe: fix-manually\n"
                module = re.search(r"from\s+(\S+)\s+import", lines[idx])
                mod_name = module.group(1) if module else "module"
                applied.append(f"Marked star import from '{mod_name}' for manual fix")

    return "".join(lines), applied
