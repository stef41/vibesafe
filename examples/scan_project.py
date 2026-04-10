"""Scan a project directory for AI-generated code issues.

Demonstrates: Scanner().scan_directory(), printing results.
"""

import tempfile
from pathlib import Path

from vibesafe import Scanner

if __name__ == "__main__":
    # Create a sample project with some intentional issues
    tmpdir = Path(tempfile.mkdtemp(prefix="vibesafe_demo_"))
    (tmpdir / "app.py").write_text("""\
import os
import sys
import json  # unused import

password = "hunter2"  # hardcoded secret

def run_query(user_input):
    os.system(f"echo {user_input}")  # shell injection risk

def unused_helper():
    pass
""")

    (tmpdir / "utils.py").write_text("""\
from os import *  # star import

def fetch_data(url):
    import subprocess
    subprocess.call(url, shell=True)  # shell=True with dynamic input
""")

    # Scan the project
    scanner = Scanner()
    result = scanner.scan_directory(tmpdir)

    print(f"Scanned {result.files_scanned} files")
    print(f"Found: {result.error_count} errors, {result.warning_count} warnings, {result.info_count} info\n")

    # Print each issue grouped by file
    current_file = ""
    for issue in sorted(result.issues, key=lambda i: (i.path, i.line)):
        if issue.path != current_file:
            current_file = issue.path
            print(f"--- {Path(current_file).name} ---")
        print(f"  L{issue.line} [{issue.severity:7s}] {issue.code}: {issue.message}")

    # Check exit status (useful for CI)
    print(f"\n{'FAIL' if result.has_errors else 'PASS'}: ", end="")
    print(f"{result.error_count} errors, {result.warning_count} warnings")

    # Cleanup
    for f in tmpdir.iterdir():
        f.unlink()
    tmpdir.rmdir()
