"""Edge case and integration tests."""

import pytest
from vibesafe.scanner import Scanner, scan_code


class TestEdgeCases:
    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        issues = Scanner().scan_file(f)
        assert isinstance(issues, list)

    def test_binary_looking_file(self, tmp_path):
        f = tmp_path / "binary.py"
        f.write_bytes(b"\x00\x01\x02\x03")
        issues = Scanner().scan_file(f)
        # Should handle gracefully (syntax error or empty)
        assert isinstance(issues, list)

    def test_unicode_source(self, tmp_path):
        f = tmp_path / "unicode.py"
        f.write_text("# Héllo wörld 🌍\nx = '日本語'\n", encoding="utf-8")
        issues = Scanner().scan_file(f)
        assert isinstance(issues, list)

    def test_very_long_file(self, tmp_path):
        f = tmp_path / "long.py"
        lines = ["x_{0} = {0}".format(i) for i in range(1000)]
        f.write_text("\n".join(lines))
        issues = Scanner().scan_file(f)
        assert isinstance(issues, list)

    def test_nested_eval(self):
        code = "eval(eval('1+1'))"
        issues = scan_code(code)
        eval_issues = [i for i in issues if i.code == "VS100"]
        assert len(eval_issues) == 2  # Two eval calls

    def test_multiple_issues_same_line(self):
        code = 'x = eval(f"SELECT * FROM users WHERE id = {uid}")'
        issues = scan_code(code)
        codes = {i.code for i in issues}
        assert "VS100" in codes  # eval
        assert "VS110" in codes  # SQL injection

    def test_only_comments(self):
        code = "# Just a comment\n# Another comment\n"
        issues = scan_code(code)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0


class TestIntegration:
    def test_realistic_bad_code(self):
        code = '''
import os
import json
import requests
import nonexistent_ai_lib

API_KEY = "sk-abc123def456ghi789jkl012mno345pqr"

def process_data(data=[]):
    query = f"SELECT * FROM users WHERE name = '{data}'"
    result = eval(query)
    # TODO: handle errors
    os.system(f"echo {result}")
    return result

def unused_func():
    pass
'''
        issues = scan_code(code)
        codes = {i.code for i in issues}
        assert "VS100" in codes   # eval
        assert "VS105" in codes   # os.system
        assert "VS110" in codes   # SQL f-string
        assert "VS200" in codes   # OpenAI key
        assert "VS300" in codes   # hallucinated import
        assert "VS400" in codes   # unused import (json)
        assert "VS500" in codes   # TODO
        assert "VS501" in codes   # empty function
        assert "VS507" in codes   # mutable default

    def test_realistic_clean_code(self):
        code = '''
import os
from pathlib import Path

def get_config(path: str) -> dict:
    """Load config from file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return {}

result = get_config(os.environ.get("CONFIG_PATH", "config.yml"))
'''
        issues = scan_code(code)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_scan_result_str(self):
        code = "x = eval('1')"
        from vibesafe.scanner import Scanner, ScanResult
        s = Scanner()
        result = ScanResult()
        result.issues = s.scan_code(code)
        result.files_scanned = 1
        output = str(result)
        assert "VS100" in output
