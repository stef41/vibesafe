"""Auto-fix common vibesafe issues and show before/after.

Demonstrates: fix_file(), fix_source() with before/after comparison.
"""

import tempfile
from pathlib import Path

from vibesafe import fix_file, fix_source, can_fix, Scanner

if __name__ == "__main__":
    # --- 1. Fix source code in memory ---
    bad_code = """\
import os
import sys
import json
from pathlib import *

def main():
    print(os.getcwd())

main()
"""

    result = fix_source(bad_code)
    print("=== fix_source() — In-Memory Fix ===")
    print(f"Changed: {result.changed}")
    print(f"Fixes applied: {result.fixes_applied}")
    if result.changed:
        print(f"\nBefore:\n{result.original_source}")
        print(f"After:\n{result.fixed_source}")

    # --- 2. Fix a file on disk ---
    tmpfile = Path(tempfile.mktemp(suffix=".py", prefix="vibesafe_fix_"))
    tmpfile.write_text("""\
import os
import sys
import re
import json

def greet(name):
    print(f"Hello, {name}")

greet("world")
""")

    print(f"\n{'='*50}")
    print("=== fix_file() — On-Disk Fix ===")

    # Show issues before fixing
    scanner = Scanner()
    issues = scanner.scan_file(tmpfile)
    fixable = [i for i in issues if can_fix(i)]
    print(f"Issues found: {len(issues)}, fixable: {len(fixable)}")
    for issue in fixable:
        print(f"  {issue.code}: {issue.message}")

    # Apply fixes
    fix_result = fix_file(tmpfile)
    print(f"\nFixes applied: {fix_result.fixes_applied}")
    if fix_result.changed:
        print(f"\nFixed source:\n{fix_result.fixed_source}")

    # Cleanup
    tmpfile.unlink(missing_ok=True)
