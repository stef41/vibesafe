"""Tests for AI pattern detection."""

import pytest
from vibesafe.scanner import scan_code


class TestTodoMarkers:
    def test_todo(self):
        code = "x = 1\n# TODO: implement this\n"
        assert any(i.code == "VS500" for i in scan_code(code))

    def test_fixme(self):
        code = "# FIXME: broken\nx = 1"
        assert any(i.code == "VS500" for i in scan_code(code))

    def test_hack(self):
        code = "# HACK: workaround\nx = 1"
        assert any(i.code == "VS500" for i in scan_code(code))

    def test_normal_comment_ok(self):
        code = "# This is a regular comment\nx = 1"
        assert not any(i.code == "VS500" for i in scan_code(code))


class TestPlaceholderFunctions:
    def test_pass_body(self):
        code = "def foo():\n    pass\n"
        assert any(i.code == "VS501" for i in scan_code(code))

    def test_ellipsis_body(self):
        code = "def foo():\n    ...\n"
        assert any(i.code == "VS501" for i in scan_code(code))

    def test_real_body_ok(self):
        code = "def foo():\n    return 42\n"
        assert not any(i.code == "VS501" for i in scan_code(code))

    def test_not_implemented(self):
        code = "def foo():\n    raise NotImplementedError()\n"
        assert any(i.code == "VS502" for i in scan_code(code))


class TestExcessiveAny:
    def test_many_any(self):
        code = "from typing import Any\n" + "\n".join(
            f"def f{i}(x: Any) -> Any: return x" for i in range(4)
        )
        # 8 Any uses (4 param + 4 return)
        issues = scan_code(code)
        assert any(i.code == "VS503" for i in issues)

    def test_few_any_ok(self):
        code = "from typing import Any\ndef f(x: Any) -> int: return x"
        assert not any(i.code == "VS503" for i in scan_code(code))


class TestHardcodedLocalhost:
    def test_localhost_url(self):
        code = 'url = "http://localhost:8080/api"'
        assert any(i.code == "VS504" for i in scan_code(code))

    def test_127_url(self):
        code = 'url = "http://127.0.0.1:3000"'
        assert any(i.code == "VS504" for i in scan_code(code))

    def test_comment_localhost_ok(self):
        code = '# http://localhost:8080 is the dev server'
        assert not any(i.code == "VS504" for i in scan_code(code))


class TestStarImport:
    def test_star_import(self):
        code = "from os import *"
        assert any(i.code == "VS506" for i in scan_code(code))


class TestMutableDefaults:
    def test_list_default(self):
        code = "def f(x=[]):\n    return x"
        assert any(i.code == "VS507" for i in scan_code(code))

    def test_dict_default(self):
        code = "def f(x={}):\n    return x"
        assert any(i.code == "VS507" for i in scan_code(code))

    def test_none_default_ok(self):
        code = "def f(x=None):\n    return x or []"
        assert not any(i.code == "VS507" for i in scan_code(code))

    def test_tuple_default_ok(self):
        code = "def f(x=(1, 2)):\n    return x"
        assert not any(i.code == "VS507" for i in scan_code(code))
