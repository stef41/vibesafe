"""Tests for the core scanner."""

import pytest
from vibesafe.scanner import Scanner, ScanResult, Issue, scan_file, scan_directory, scan_code


class TestIssue:
    def test_str_format(self):
        issue = Issue("test.py", 10, 5, "error", "VS100", "Test message", "security")
        result = str(issue)
        assert "test.py:10:5" in result
        assert "VS100" in result
        assert "Test message" in result

    def test_fields(self):
        issue = Issue("a.py", 1, 0, "warning", "VS200", "msg", "secret")
        assert issue.path == "a.py"
        assert issue.severity == "warning"
        assert issue.category == "secret"


class TestScanResult:
    def test_empty(self):
        r = ScanResult()
        assert r.error_count == 0
        assert r.warning_count == 0
        assert r.info_count == 0
        assert not r.has_errors

    def test_counts(self):
        r = ScanResult(issues=[
            Issue("a.py", 1, 0, "error", "X", "m", "c"),
            Issue("a.py", 2, 0, "warning", "X", "m", "c"),
            Issue("a.py", 3, 0, "info", "X", "m", "c"),
            Issue("a.py", 4, 0, "error", "X", "m", "c"),
        ])
        assert r.error_count == 2
        assert r.warning_count == 1
        assert r.info_count == 1
        assert r.has_errors

    def test_str(self):
        r = ScanResult(issues=[Issue("a.py", 1, 0, "error", "X", "m", "c")])
        r.files_scanned = 1
        s = str(r)
        assert "1 files scanned" in s
        assert "1 errors" in s


class TestScanner:
    def test_nonexistent_file(self):
        assert Scanner().scan_file("/no/such/file.py") == []

    def test_non_python_file(self, tmp_path):
        f = tmp_path / "readme.txt"
        f.write_text("hello")
        assert Scanner().scan_file(f) == []

    def test_syntax_error_file(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def foo(\n")
        issues = Scanner().scan_file(f)
        assert len(issues) == 1
        assert issues[0].code == "VS000"

    def test_clean_file(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("x = 1 + 2\nprint(x)\n")
        issues = Scanner().scan_file(f)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_directory_scan(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("y = 2\n")
        result = Scanner().scan_directory(tmp_path)
        assert result.files_scanned == 2

    def test_excludes_venv(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "b.py").write_text("eval('bad')\n")
        result = Scanner().scan_directory(tmp_path)
        assert result.files_scanned == 1

    def test_scan_code(self):
        issues = Scanner().scan_code("x = eval('1+1')")
        codes = [i.code for i in issues]
        assert "VS100" in codes

    def test_scan_code_syntax_error(self):
        issues = Scanner().scan_code("def (")
        assert issues[0].code == "VS000"

    def test_severity_threshold_error(self, tmp_path):
        f = tmp_path / "t.py"
        f.write_text("x = eval('1')\n# TODO: fix\n")
        issues = Scanner(severity_threshold="error").scan_file(f)
        for i in issues:
            assert i.severity == "error"

    def test_severity_threshold_warning(self, tmp_path):
        f = tmp_path / "t.py"
        f.write_text("x = eval('1')\n# TODO: fix\n")
        issues = Scanner(severity_threshold="warning").scan_file(f)
        for i in issues:
            assert i.severity in ("error", "warning")

    def test_custom_checks(self):
        def my_check(path, tree, source):
            from vibesafe.scanner import Issue
            return [Issue(path, 1, 0, "info", "CUSTOM", "custom check", "custom")]
        s = Scanner(checks=[my_check])
        issues = s.scan_code("x = 1")
        assert issues[0].code == "CUSTOM"


class TestConvenience:
    def test_scan_file(self, tmp_path):
        f = tmp_path / "t.py"
        f.write_text("x = 1\n")
        assert isinstance(scan_file(f), list)

    def test_scan_directory(self, tmp_path):
        (tmp_path / "t.py").write_text("x = 1\n")
        assert isinstance(scan_directory(tmp_path), ScanResult)

    def test_scan_code(self):
        assert isinstance(scan_code("x = 1"), list)
