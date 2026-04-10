"""Tests for dead code detection."""

import pytest
from vibesafe.scanner import scan_code


class TestUnusedImports:
    def test_unused_import(self):
        code = "import os\nx = 1"
        assert any(i.code == "VS400" for i in scan_code(code))

    def test_used_import_ok(self):
        code = "import os\npath = os.getcwd()"
        assert not any(i.code == "VS400" for i in scan_code(code))

    def test_underscore_ok(self):
        code = "from x import _ as _\n"
        # underscore imports should not be flagged
        issues = [i for i in scan_code(code) if i.code == "VS400"]
        # _ is a convention for unused
        assert not any(i.message == "Unused import: '_'" for i in issues)

    def test_export_in_all(self):
        code = 'import os\n__all__ = ["os"]'
        assert not any(i.code == "VS400" for i in scan_code(code))

    def test_from_import_unused(self):
        code = "from os.path import join\nx = 1"
        assert any(i.code == "VS400" for i in scan_code(code))

    def test_from_import_used(self):
        code = "from os.path import join\npath = join('a', 'b')"
        assert not any(i.code == "VS400" for i in scan_code(code))


class TestUnreachableCode:
    def test_after_return(self):
        code = "def f():\n    return 1\n    x = 2\n"
        assert any(i.code == "VS401" for i in scan_code(code))

    def test_after_raise(self):
        code = "def f():\n    raise ValueError()\n    x = 2\n"
        assert any(i.code == "VS401" for i in scan_code(code))

    def test_no_unreachable(self):
        code = "def f():\n    x = 1\n    return x\n"
        assert not any(i.code == "VS401" for i in scan_code(code))


class TestEmptyExcept:
    def test_pass_except(self):
        code = "try:\n    x = 1\nexcept Exception:\n    pass\n"
        assert any(i.code == "VS402" for i in scan_code(code))

    def test_except_with_logging_ok(self):
        code = "try:\n    x = 1\nexcept Exception as e:\n    log(e)\n"
        assert not any(i.code == "VS402" for i in scan_code(code))


class TestBareExcept:
    def test_bare_except(self):
        code = "try:\n    x = 1\nexcept:\n    pass\n"
        assert any(i.code == "VS403" for i in scan_code(code))

    def test_typed_except_ok(self):
        code = "try:\n    x = 1\nexcept ValueError:\n    pass\n"
        assert not any(i.code == "VS403" for i in scan_code(code))
