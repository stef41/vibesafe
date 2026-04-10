"""Tests for import checks."""

import pytest
from vibesafe.scanner import scan_code


class TestHallucinatedImports:
    def test_nonexistent_package(self):
        code = "import zzzfakepackage999"
        issues = scan_code(code)
        assert any(i.code == "VS300" for i in issues)

    def test_nonexistent_from_import(self):
        code = "from zzzfake999 import something"
        issues = scan_code(code)
        assert any(i.code == "VS300" for i in issues)

    def test_stdlib_ok(self):
        code = "import os\nimport sys\nimport json\nimport pathlib"
        issues = scan_code(code)
        assert not any(i.code == "VS300" for i in issues)

    def test_popular_packages_ok(self):
        code = "import numpy\nimport requests\nimport flask"
        issues = scan_code(code)
        assert not any(i.code == "VS300" for i in issues)

    def test_relative_import_ok(self):
        code = "from . import utils\nfrom .models import User"
        issues = scan_code(code)
        assert not any(i.code == "VS300" for i in issues)

    def test_dotted_import(self):
        code = "import zzzfake999.submodule"
        issues = scan_code(code)
        assert any(i.code == "VS300" and "zzzfake999" in i.message for i in issues)

    def test_installed_package_ok(self):
        code = "import pytest"
        issues = scan_code(code)
        assert not any(i.code == "VS300" for i in issues)
