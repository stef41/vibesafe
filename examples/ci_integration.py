"""Use vibesafe programmatically in a CI pipeline.

Demonstrates: using Scanner for automated quality gates in CI/CD.
"""

import sys
import tempfile
from pathlib import Path

from vibesafe import Scanner, ScanResult


def ci_scan(project_dir: str, fail_on_warnings: bool = False) -> int:
    """Run a CI-style scan and return an exit code (0=pass, 1=fail)."""
    scanner = Scanner(severity_threshold="info")
    result = scanner.scan_directory(project_dir)

    # Print summary header
    print(f"vibesafe CI scan: {result.files_scanned} files")
    print(f"  Errors:   {result.error_count}")
    print(f"  Warnings: {result.warning_count}")
    print(f"  Info:     {result.info_count}")

    # Print issues (CI-friendly format: file:line:col message)
    for issue in sorted(result.issues, key=lambda i: (i.path, i.line)):
        print(f"  {issue}")

    # Determine pass/fail
    if result.error_count > 0:
        return 1
    if fail_on_warnings and result.warning_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    # Create a demo project to scan
    tmpdir = Path(tempfile.mkdtemp(prefix="ci_demo_"))

    (tmpdir / "server.py").write_text("""\
import os

def handle_request(data):
    query = data.get("query", "")
    os.system(f"process {query}")  # unsafe

API_KEY = "sk-1234567890abcdef"
""")

    (tmpdir / "clean_module.py").write_text("""\
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str) -> str:
    return f"Hello, {name}!"
""")

    # Run the CI scan
    print("=" * 60)
    print("CI PIPELINE — vibesafe scan")
    print("=" * 60)

    exit_code = ci_scan(str(tmpdir), fail_on_warnings=False)

    print(f"\n{'='*60}")
    print(f"Exit code: {exit_code} ({'FAIL' if exit_code else 'PASS'})")
    print("=" * 60)

    # Cleanup
    for f in tmpdir.iterdir():
        f.unlink()
    tmpdir.rmdir()

    # In a real CI script, you'd exit with the code:
    # sys.exit(exit_code)
