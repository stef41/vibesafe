"""Tests for the CLI."""

import json
import pytest
from vibesafe.cli import main


class TestCLIScan:
    def test_scan_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = eval('1+1')\n")
        exit_code = main(["scan", str(f)])
        assert exit_code == 1  # eval is an error

    def test_scan_clean_file(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("x = 1 + 2\nprint(x)\n")
        exit_code = main(["scan", str(f)])
        assert exit_code == 0

    def test_scan_directory(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        exit_code = main(["scan", str(tmp_path)])
        assert exit_code == 0

    def test_json_output(self, tmp_path, capsys):
        f = tmp_path / "t.py"
        f.write_text("eval('x')\n")
        main(["scan", str(f), "--format", "json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "issues" in data
        assert data["error_count"] >= 1

    def test_severity_filter(self, tmp_path):
        f = tmp_path / "t.py"
        f.write_text("# TODO: fix\n")
        exit_code = main(["scan", str(f), "--severity", "error"])
        assert exit_code == 0  # TODOs are info-level

    def test_fail_on_warning(self, tmp_path):
        f = tmp_path / "t.py"
        f.write_text("def f():\n    pass\n")
        exit_code = main(["scan", str(f), "--fail-on", "warning"])
        assert exit_code == 1  # empty function is a warning

    def test_nonexistent_path(self, tmp_path, capsys):
        exit_code = main(["scan", str(tmp_path / "nope")])
        assert exit_code == 0  # warns but doesn't fail


class TestCLICheck:
    def test_check_stdin(self, tmp_path, monkeypatch):
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO("x = eval('bad')"))
        exit_code = main(["check"])
        assert exit_code == 1

    def test_check_clean(self, monkeypatch):
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO("x = 1 + 2"))
        exit_code = main(["check"])
        assert exit_code == 0

    def test_check_json(self, monkeypatch, capsys):
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO("exec('bad')"))
        main(["check", "--format", "json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) > 0


class TestCLINoCommand:
    def test_no_args(self):
        exit_code = main([])
        assert exit_code == 0

    def test_version(self):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
