"""Security vulnerability detection for AI-generated code."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibesafe.scanner import Issue


def check_security(path: str, tree: ast.AST, source: str) -> list[Issue]:
    """Detect security anti-patterns commonly produced by AI coding agents."""
    from vibesafe.scanner import Issue

    issues: list[Issue] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func

            # VS100: eval()
            if isinstance(func, ast.Name) and func.id == "eval":
                issues.append(Issue(
                    path=path, line=node.lineno, column=node.col_offset,
                    severity="error", code="VS100",
                    message="Use of eval() - potential code injection vulnerability",
                    category="security",
                ))

            # VS101: exec()
            if isinstance(func, ast.Name) and func.id == "exec":
                issues.append(Issue(
                    path=path, line=node.lineno, column=node.col_offset,
                    severity="error", code="VS101",
                    message="Use of exec() - potential code injection vulnerability",
                    category="security",
                ))

            # VS102: subprocess with shell=True
            if isinstance(func, ast.Attribute) and func.attr in (
                "call", "run", "Popen", "check_output", "check_call",
            ):
                for kw in node.keywords:
                    if (
                        kw.arg == "shell"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                    ):
                        issues.append(Issue(
                            path=path, line=node.lineno, column=node.col_offset,
                            severity="error", code="VS102",
                            message=f"subprocess.{func.attr}() with shell=True - command injection risk",
                            category="security",
                        ))

            # VS103: pickle.loads / pickle.load
            if (
                isinstance(func, ast.Attribute)
                and func.attr in ("loads", "load")
                and isinstance(func.value, ast.Name)
                and func.value.id == "pickle"
            ):
                issues.append(Issue(
                    path=path, line=node.lineno, column=node.col_offset,
                    severity="warning", code="VS103",
                    message="pickle.load(s)() - deserializing untrusted data can execute arbitrary code",
                    category="security",
                ))

            # VS104: yaml.load without SafeLoader
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "load"
                and isinstance(func.value, ast.Name)
                and func.value.id == "yaml"
            ):
                has_loader_kw = any(kw.arg == "Loader" for kw in node.keywords)
                if len(node.args) <= 1 and not has_loader_kw:
                    issues.append(Issue(
                        path=path, line=node.lineno, column=node.col_offset,
                        severity="error", code="VS104",
                        message="yaml.load() without Loader - use yaml.safe_load() instead",
                        category="security",
                    ))

            # VS105: os.system()
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "system"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            ):
                issues.append(Issue(
                    path=path, line=node.lineno, column=node.col_offset,
                    severity="error", code="VS105",
                    message="os.system() - use subprocess.run() with shell=False instead",
                    category="security",
                ))

            # VS106: tempfile.mktemp (insecure)
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "mktemp"
                and isinstance(func.value, ast.Name)
                and func.value.id == "tempfile"
            ):
                issues.append(Issue(
                    path=path, line=node.lineno, column=node.col_offset,
                    severity="warning", code="VS106",
                    message="tempfile.mktemp() is insecure - use tempfile.mkstemp() instead",
                    category="security",
                ))

            # VS108: hashlib.md5 / hashlib.sha1
            if (
                isinstance(func, ast.Attribute)
                and func.attr in ("md5", "sha1")
                and isinstance(func.value, ast.Name)
                and func.value.id == "hashlib"
            ):
                issues.append(Issue(
                    path=path, line=node.lineno, column=node.col_offset,
                    severity="warning", code="VS108",
                    message=f"hashlib.{func.attr}() is cryptographically weak - use sha256 or better",
                    category="security",
                ))

        # VS109: assert for validation
        if isinstance(node, ast.Assert):
            issues.append(Issue(
                path=path, line=node.lineno, column=node.col_offset,
                severity="info", code="VS109",
                message="assert used for validation - stripped with python -O",
                category="security",
            ))

    # VS110: SQL string formatting
    for i, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        upper = stripped.upper()
        sql_kws = ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "DROP ", "WHERE ")
        if ('f"' in stripped or "f'" in stripped) and any(kw in upper for kw in sql_kws):
            issues.append(Issue(
                path=path, line=i, column=0,
                severity="error", code="VS110",
                message="SQL query built with f-string - use parameterized queries",
                category="security",
            ))
        elif ".format(" in stripped and any(kw in upper for kw in sql_kws):
            issues.append(Issue(
                path=path, line=i, column=0,
                severity="error", code="VS110",
                message="SQL query built with .format() - use parameterized queries",
                category="security",
            ))

    return issues
