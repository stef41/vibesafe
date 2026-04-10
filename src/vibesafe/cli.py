"""Command-line interface for vibesafe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vibesafe import __version__
from vibesafe.scanner import Scanner, ScanResult


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vibesafe",
        description="AI-generated code safety scanner for the vibe coding era",
    )
    parser.add_argument("--version", action="version", version=f"vibesafe {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    scan_p = subparsers.add_parser("scan", help="Scan files or directories")
    scan_p.add_argument("paths", nargs="+", help="Files or directories to scan")
    scan_p.add_argument(
        "--severity", choices=["error", "warning", "info"], default="info",
        help="Minimum severity to report",
    )
    scan_p.add_argument("--format", choices=["text", "json"], default="text")
    scan_p.add_argument(
        "--fail-on", choices=["error", "warning", "info"], default="error",
        help="Exit 1 if issues at this level or above are found",
    )

    check_p = subparsers.add_parser("check", help="Check code from stdin")
    check_p.add_argument("--severity", choices=["error", "warning", "info"], default="info")
    check_p.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "scan":
        return _cmd_scan(args)
    elif args.command == "check":
        return _cmd_check(args)

    return 0


def _cmd_scan(args) -> int:
    scanner = Scanner(severity_threshold=args.severity)
    result = ScanResult()

    for p in args.paths:
        path = Path(p)
        if path.is_file():
            issues = scanner.scan_file(path)
            result.issues.extend(issues)
            result.files_scanned += 1
        elif path.is_dir():
            dr = scanner.scan_directory(path)
            result.issues.extend(dr.issues)
            result.files_scanned += dr.files_scanned
        else:
            print(f"Warning: {p} not found", file=sys.stderr)

    if args.format == "json":
        _print_json(result)
    else:
        _print_text(result)

    severity_order = {"error": 0, "warning": 1, "info": 2}
    threshold = severity_order.get(args.fail_on, 0)
    for issue in result.issues:
        if severity_order.get(issue.severity, 2) <= threshold:
            return 1
    return 0


def _cmd_check(args) -> int:
    scanner = Scanner(severity_threshold=args.severity)
    code = sys.stdin.read()
    issues = scanner.scan_code(code)

    if args.format == "json":
        data = [
            {"line": i.line, "column": i.column, "severity": i.severity,
             "code": i.code, "message": i.message, "category": i.category}
            for i in issues
        ]
        print(json.dumps(data, indent=2))
    else:
        for issue in issues:
            print(f"  {_icon(issue.severity)} {issue}")

    return 1 if any(i.severity == "error" for i in issues) else 0


def _icon(severity: str) -> str:
    return {"error": "\u2717", "warning": "\u26a0", "info": "\u2139"}.get(severity, "?")


def _print_text(result: ScanResult) -> None:
    if not result.issues:
        print(f"\u2713 {result.files_scanned} files scanned - no issues found")
        return

    for issue in sorted(result.issues, key=lambda i: (i.path, i.line)):
        print(f"  {_icon(issue.severity)} {issue}")

    print(
        f"\n{result.files_scanned} files scanned: "
        f"{result.error_count} errors, {result.warning_count} warnings, "
        f"{result.info_count} info"
    )


def _print_json(result: ScanResult) -> None:
    data = {
        "files_scanned": result.files_scanned,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "info_count": result.info_count,
        "issues": [
            {"path": i.path, "line": i.line, "column": i.column,
             "severity": i.severity, "code": i.code, "message": i.message,
             "category": i.category}
            for i in sorted(result.issues, key=lambda i: (i.path, i.line))
        ],
    }
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    sys.exit(main())
