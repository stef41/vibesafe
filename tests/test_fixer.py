"""Tests for the auto-fixer."""

import pytest
from vibesafe.fixer import fix_source, fix_file, can_fix, FIXABLE_CODES, FixResult
from vibesafe.scanner import Issue


class TestCanFix:
    def test_fixable_vs400(self):
        issue = Issue(
            path="t.py", line=1, column=0,
            severity="warning", code="VS400",
            message="Unused import: 'os'", category="dead-code",
        )
        assert can_fix(issue)

    def test_fixable_vs506(self):
        issue = Issue(
            path="t.py", line=1, column=0,
            severity="warning", code="VS506",
            message="Star import from 'os'", category="pattern",
        )
        assert can_fix(issue)

    def test_not_fixable_vs100(self):
        issue = Issue(
            path="t.py", line=1, column=0,
            severity="error", code="VS100",
            message="Use of eval()", category="security",
        )
        assert not can_fix(issue)

    def test_fixable_codes_set(self):
        assert "VS400" in FIXABLE_CODES
        assert "VS506" in FIXABLE_CODES


class TestFixUnusedImports:
    def test_remove_single_unused_import(self):
        code = "import os\nx = 1\n"
        result = fix_source(code)
        assert result.changed
        assert "import os" not in result.fixed_source
        assert "x = 1" in result.fixed_source
        assert len(result.fixes_applied) == 1

    def test_remove_unused_from_import(self):
        code = "from os.path import join\nx = 1\n"
        result = fix_source(code)
        assert result.changed
        assert "from os.path import join" not in result.fixed_source

    def test_keep_used_import(self):
        code = "import os\npath = os.getcwd()\n"
        result = fix_source(code)
        assert not result.changed

    def test_partial_import_removal(self):
        code = "from os.path import join, exists\npath = join('a', 'b')\n"
        result = fix_source(code)
        assert result.changed
        assert "join" in result.fixed_source
        assert "exists" not in result.fixed_source

    def test_multiple_unused_imports(self):
        code = "import os\nimport sys\nx = 1\n"
        result = fix_source(code)
        assert result.changed
        assert "import os" not in result.fixed_source
        assert "import sys" not in result.fixed_source
        assert len(result.fixes_applied) == 2

    def test_import_with_alias_unused(self):
        code = "import numpy as np\nx = 1\n"
        result = fix_source(code)
        assert result.changed
        assert "numpy" not in result.fixed_source

    def test_import_with_alias_used(self):
        code = "import numpy as np\ny = np.array([1])\n"
        result = fix_source(code)
        assert not result.changed

    def test_preserves_used_imports(self):
        code = "import os\nimport sys\nprint(os.getcwd())\n"
        result = fix_source(code)
        assert result.changed
        assert "import os" in result.fixed_source
        assert "import sys" not in result.fixed_source

    def test_no_issues_no_change(self):
        code = "x = 1\nprint(x)\n"
        result = fix_source(code)
        assert not result.changed
        assert result.fixes_applied == []

    def test_underscore_import_kept(self):
        code = "from gettext import gettext as _\nprint(_('hi'))\n"
        result = fix_source(code)
        assert not result.changed

    def test_all_export_not_removed(self):
        code = 'import os\n__all__ = ["os"]\n'
        result = fix_source(code)
        assert not result.changed


class TestFixStarImports:
    def test_marks_star_import(self):
        code = "from os import *\npath = getcwd()\n"
        result = fix_source(code)
        assert result.changed
        assert "vibesafe: fix-manually" in result.fixed_source

    def test_no_star_import(self):
        code = "from os import getcwd\npath = getcwd()\n"
        result = fix_source(code)
        # No star import, may or may not change depending on other issues
        assert "vibesafe: fix-manually" not in result.fixed_source


class TestFixFile:
    def test_fix_file_removes_unused(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("import os\nimport sys\nx = 1\n")
        result = fix_file(f)
        assert result.changed
        assert len(result.fixes_applied) == 2

    def test_fix_file_no_change(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("x = 1\nprint(x)\n")
        result = fix_file(f)
        assert not result.changed

    def test_fix_file_path_in_result(self, tmp_path):
        f = tmp_path / "t.py"
        f.write_text("import os\nx = 1\n")
        result = fix_file(f)
        assert str(f) in result.path


class TestFixResult:
    def test_changed_property(self):
        r = FixResult(path="t.py", fixes_applied=["fix1"],
                      original_source="a", fixed_source="b")
        assert r.changed

    def test_not_changed(self):
        r = FixResult(path="t.py", fixes_applied=[],
                      original_source="a", fixed_source="a")
        assert not r.changed


class TestCLIFix:
    def test_fix_command(self, tmp_path):
        from vibesafe.cli import main
        f = tmp_path / "bad.py"
        f.write_text("import os\nimport sys\nx = 1\n")
        exit_code = main(["fix", str(f)])
        assert exit_code == 0
        content = f.read_text()
        assert "import os" not in content
        assert "import sys" not in content

    def test_fix_dry_run(self, tmp_path):
        from vibesafe.cli import main
        f = tmp_path / "bad.py"
        original = "import os\nx = 1\n"
        f.write_text(original)
        exit_code = main(["fix", "--dry-run", str(f)])
        assert exit_code == 0
        # File should NOT be modified
        assert f.read_text() == original

    def test_fix_directory(self, tmp_path):
        from vibesafe.cli import main
        (tmp_path / "a.py").write_text("import os\nx = 1\n")
        (tmp_path / "b.py").write_text("import sys\ny = 2\n")
        exit_code = main(["fix", str(tmp_path)])
        assert exit_code == 0
        assert "import os" not in (tmp_path / "a.py").read_text()
        assert "import sys" not in (tmp_path / "b.py").read_text()

    def test_fix_json_output(self, tmp_path, capsys):
        import json
        from vibesafe.cli import main
        f = tmp_path / "t.py"
        f.write_text("import os\nx = 1\n")
        main(["fix", str(f), "--format", "json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["files_fixed"] == 1
        assert data["total_fixes"] >= 1

    def test_fix_clean_file(self, tmp_path, capsys):
        from vibesafe.cli import main
        f = tmp_path / "clean.py"
        f.write_text("x = 1\nprint(x)\n")
        exit_code = main(["fix", str(f)])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No fixable issues" in captured.out
