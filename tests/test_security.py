"""Tests for security checks."""

import pytest
from vibesafe.scanner import scan_code


class TestEvalExec:
    def test_eval(self):
        issues = scan_code("x = eval(user_input)")
        assert any(i.code == "VS100" for i in issues)

    def test_exec(self):
        issues = scan_code("exec(user_code)")
        assert any(i.code == "VS101" for i in issues)

    def test_no_false_positive_literal_eval(self):
        issues = scan_code("import ast\nast.literal_eval('1')")
        assert not any(i.code == "VS100" for i in issues)


class TestSubprocess:
    def test_shell_true(self):
        code = "import subprocess\nsubprocess.run(cmd, shell=True)"
        assert any(i.code == "VS102" for i in scan_code(code))

    def test_shell_false_ok(self):
        code = "import subprocess\nsubprocess.run(cmd, shell=False)"
        assert not any(i.code == "VS102" for i in scan_code(code))

    def test_popen_shell(self):
        code = "import subprocess\nsubprocess.Popen(cmd, shell=True)"
        assert any(i.code == "VS102" for i in scan_code(code))

    def test_check_output_shell(self):
        code = "import subprocess\nsubprocess.check_output(cmd, shell=True)"
        assert any(i.code == "VS102" for i in scan_code(code))


class TestPickle:
    def test_loads(self):
        assert any(i.code == "VS103" for i in scan_code("import pickle\npickle.loads(data)"))

    def test_load(self):
        assert any(i.code == "VS103" for i in scan_code("import pickle\npickle.load(f)"))


class TestYaml:
    def test_unsafe_load(self):
        assert any(i.code == "VS104" for i in scan_code("import yaml\nyaml.load(text)"))

    def test_safe_loader_ok(self):
        code = "import yaml\nyaml.load(text, Loader=yaml.SafeLoader)"
        assert not any(i.code == "VS104" for i in scan_code(code))


class TestOsSystem:
    def test_os_system(self):
        assert any(i.code == "VS105" for i in scan_code("import os\nos.system('ls')"))


class TestTempfile:
    def test_mktemp(self):
        assert any(i.code == "VS106" for i in scan_code("import tempfile\ntempfile.mktemp()"))


class TestWeakHash:
    def test_md5(self):
        assert any(i.code == "VS108" for i in scan_code("import hashlib\nhashlib.md5(b'x')"))

    def test_sha1(self):
        assert any(i.code == "VS108" for i in scan_code("import hashlib\nhashlib.sha1(b'x')"))

    def test_sha256_ok(self):
        assert not any(i.code == "VS108" for i in scan_code("import hashlib\nhashlib.sha256(b'x')"))


class TestSqlInjection:
    def test_fstring(self):
        code = 'q = f"SELECT * FROM users WHERE id = {uid}"'
        assert any(i.code == "VS110" for i in scan_code(code))

    def test_format(self):
        code = 'q = "DELETE FROM t WHERE id = {}".format(uid)'
        assert any(i.code == "VS110" for i in scan_code(code))

    def test_parameterized_ok(self):
        code = 'cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))'
        assert not any(i.code == "VS110" for i in scan_code(code))

    def test_comment_not_flagged(self):
        code = '# SELECT * FROM users f"WHERE id = {uid}"'
        assert not any(i.code == "VS110" for i in scan_code(code))


class TestAssert:
    def test_assert_warning(self):
        assert any(i.code == "VS109" for i in scan_code("assert x > 0"))
