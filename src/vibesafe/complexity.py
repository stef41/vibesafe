"""Complexity analysis for AI-generated Python code."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ComplexityConfig:
    """Configuration for complexity thresholds."""

    max_cyclomatic: int = 10
    max_nesting: int = 4
    max_function_length: int = 50
    max_parameters: int = 5


@dataclass
class ComplexityIssue:
    """A single complexity issue found during analysis."""

    code: str
    message: str
    line: int
    function_name: Optional[str]
    value: int

    def __str__(self) -> str:
        loc = f"line {self.line}"
        if self.function_name:
            loc = f"{self.function_name} (line {self.line})"
        return f"{self.code}: {self.message} [{loc}, value={self.value}]"


class _NestingVisitor(ast.NodeVisitor):
    """Compute maximum nesting depth in an AST subtree."""

    NESTING_NODES = (
        ast.If, ast.For, ast.While, ast.With,
        ast.Try, ast.ExceptHandler,
        ast.AsyncFor, ast.AsyncWith,
    )

    def __init__(self) -> None:
        self.max_depth = 0
        self._current = 0

    def _visit_nesting(self, node: ast.AST) -> None:
        self._current += 1
        if self._current > self.max_depth:
            self.max_depth = self._current
        self.generic_visit(node)
        self._current -= 1

    def visit_If(self, node: ast.If) -> None:
        self._visit_nesting(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_nesting(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_nesting(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_nesting(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_nesting(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._visit_nesting(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_nesting(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_nesting(node)


class _CyclomaticVisitor(ast.NodeVisitor):
    """Count decision points in an AST subtree."""

    def __init__(self) -> None:
        self.complexity = 1  # base path

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each 'and' / 'or' adds (len(values) - 1) decision points
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


def _function_end_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return the last line number of a function body."""
    return max(getattr(n, "end_lineno", None) or getattr(n, "lineno", node.lineno) for n in ast.walk(node))


def _count_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count parameters excluding 'self' and 'cls'."""
    args = node.args
    all_args = args.posonlyargs + args.args + args.kwonlyargs
    names = [a.arg for a in all_args]
    count = len(names)
    if names and names[0] in ("self", "cls"):
        count -= 1
    if args.vararg:
        count += 1
    if args.kwarg:
        count += 1
    return count


class ComplexityAnalyzer:
    """Analyze Python source code for complexity issues."""

    def __init__(self, config: Optional[ComplexityConfig] = None) -> None:
        self.config = config or ComplexityConfig()

    def analyze(self, source: str) -> list[ComplexityIssue]:
        """Parse Python source and find complexity issues."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        issues: list[ComplexityIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            name = node.name
            line = node.lineno

            # Cyclomatic complexity
            cv = _CyclomaticVisitor()
            cv.visit(node)
            cc = cv.complexity
            if cc > self.config.max_cyclomatic:
                issues.append(ComplexityIssue(
                    code="VS600",
                    message=f"Cyclomatic complexity {cc} exceeds maximum {self.config.max_cyclomatic}",
                    line=line,
                    function_name=name,
                    value=cc,
                ))

            # Nesting depth
            nv = _NestingVisitor()
            nv.visit(node)
            depth = nv.max_depth
            if depth > self.config.max_nesting:
                issues.append(ComplexityIssue(
                    code="VS601",
                    message=f"Nesting depth {depth} exceeds maximum {self.config.max_nesting}",
                    line=line,
                    function_name=name,
                    value=depth,
                ))

            # Function length
            end = _function_end_line(node)
            length = end - line + 1
            if length > self.config.max_function_length:
                issues.append(ComplexityIssue(
                    code="VS602",
                    message=f"Function length {length} lines exceeds maximum {self.config.max_function_length}",
                    line=line,
                    function_name=name,
                    value=length,
                ))

            # Parameter count
            params = _count_params(node)
            if params > self.config.max_parameters:
                issues.append(ComplexityIssue(
                    code="VS603",
                    message=f"Parameter count {params} exceeds maximum {self.config.max_parameters}",
                    line=line,
                    function_name=name,
                    value=params,
                ))

        return issues

    def cyclomatic_complexity(self, source: str) -> int:
        """Count the overall cyclomatic complexity of the source."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return 1
        cv = _CyclomaticVisitor()
        cv.visit(tree)
        return cv.complexity

    def nesting_depth(self, source: str) -> int:
        """Return the maximum nesting level in the source."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return 0
        nv = _NestingVisitor()
        nv.visit(tree)
        return nv.max_depth

    def function_metrics(self, source: str) -> list[dict]:
        """Return per-function metrics: name, lines, params, complexity, nesting."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        results: list[dict] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            cv = _CyclomaticVisitor()
            cv.visit(node)
            nv = _NestingVisitor()
            nv.visit(node)
            end = _function_end_line(node)
            results.append({
                "name": node.name,
                "lines": end - node.lineno + 1,
                "params": _count_params(node),
                "complexity": cv.complexity,
                "nesting": nv.max_depth,
            })
        return results


def format_complexity_report(issues: list[ComplexityIssue]) -> str:
    """Format a list of complexity issues into a human-readable report."""
    if not issues:
        return "No complexity issues found."

    lines = [f"Found {len(issues)} complexity issue(s):", ""]
    for issue in issues:
        lines.append(f"  {issue}")
    return "\n".join(lines)
