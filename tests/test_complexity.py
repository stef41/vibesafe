"""Tests for vibesafe.complexity module."""

import pytest

from vibesafe.complexity import (
    ComplexityAnalyzer,
    ComplexityConfig,
    ComplexityIssue,
    format_complexity_report,
)


# --- Simple helpers ---

SIMPLE_FUNC = '''\
def hello():
    return "hi"
'''

COMPLEX_FUNC = '''\
def complex(a, b, c, d, e, f):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 1
    elif f:
        for i in range(10):
            while True:
                break
    return 0
'''

LONG_FUNC = "def long_fn():\n" + "\n".join(f"    x = {i}" for i in range(60))

MANY_PARAMS = '''\
def too_many(a, b, c, d, e, f, g, h):
    pass
'''

BOOL_OPS = '''\
def decide(a, b, c, d):
    if a and b or c and d:
        return True
    return False
'''


class TestCyclomaticComplexity:
    def test_simple_function(self):
        analyzer = ComplexityAnalyzer()
        cc = analyzer.cyclomatic_complexity(SIMPLE_FUNC)
        assert cc == 1

    def test_if_adds_complexity(self):
        src = "if True:\n    pass\n"
        analyzer = ComplexityAnalyzer()
        assert analyzer.cyclomatic_complexity(src) == 2

    def test_bool_ops_count(self):
        analyzer = ComplexityAnalyzer()
        cc = analyzer.cyclomatic_complexity(BOOL_OPS)
        # if + (a and b) + (or) + (c and d) = 1 + 1 + 3 = 5
        assert cc >= 4

    def test_for_while_except(self):
        src = '''\
for x in []:
    pass
while False:
    pass
try:
    pass
except:
    pass
'''
        analyzer = ComplexityAnalyzer()
        assert analyzer.cyclomatic_complexity(src) >= 4


class TestNestingDepth:
    def test_flat_code(self):
        analyzer = ComplexityAnalyzer()
        assert analyzer.nesting_depth(SIMPLE_FUNC) == 0

    def test_deep_nesting(self):
        analyzer = ComplexityAnalyzer()
        depth = analyzer.nesting_depth(COMPLEX_FUNC)
        assert depth >= 5

    def test_single_if(self):
        analyzer = ComplexityAnalyzer()
        assert analyzer.nesting_depth("if True:\n    pass\n") == 1


class TestFunctionMetrics:
    def test_returns_list(self):
        analyzer = ComplexityAnalyzer()
        metrics = analyzer.function_metrics(SIMPLE_FUNC)
        assert isinstance(metrics, list)
        assert len(metrics) == 1
        assert metrics[0]["name"] == "hello"

    def test_param_count(self):
        analyzer = ComplexityAnalyzer()
        metrics = analyzer.function_metrics(MANY_PARAMS)
        assert metrics[0]["params"] == 8

    def test_self_excluded(self):
        src = '''\
class Foo:
    def bar(self, x, y):
        pass
'''
        analyzer = ComplexityAnalyzer()
        metrics = analyzer.function_metrics(src)
        bar = [m for m in metrics if m["name"] == "bar"][0]
        assert bar["params"] == 2

    def test_multiple_functions(self):
        src = '''\
def a():
    pass

def b(x):
    if x:
        pass
'''
        analyzer = ComplexityAnalyzer()
        metrics = analyzer.function_metrics(src)
        assert len(metrics) == 2


class TestAnalyze:
    def test_no_issues_simple(self):
        analyzer = ComplexityAnalyzer()
        assert analyzer.analyze(SIMPLE_FUNC) == []

    def test_vs600_high_complexity(self):
        analyzer = ComplexityAnalyzer(ComplexityConfig(max_cyclomatic=2))
        issues = analyzer.analyze(COMPLEX_FUNC)
        codes = [i.code for i in issues]
        assert "VS600" in codes

    def test_vs601_deep_nesting(self):
        analyzer = ComplexityAnalyzer(ComplexityConfig(max_nesting=2))
        issues = analyzer.analyze(COMPLEX_FUNC)
        codes = [i.code for i in issues]
        assert "VS601" in codes

    def test_vs602_long_function(self):
        analyzer = ComplexityAnalyzer(ComplexityConfig(max_function_length=10))
        issues = analyzer.analyze(LONG_FUNC)
        codes = [i.code for i in issues]
        assert "VS602" in codes

    def test_vs603_too_many_params(self):
        analyzer = ComplexityAnalyzer(ComplexityConfig(max_parameters=3))
        issues = analyzer.analyze(MANY_PARAMS)
        codes = [i.code for i in issues]
        assert "VS603" in codes

    def test_syntax_error_returns_empty(self):
        analyzer = ComplexityAnalyzer()
        assert analyzer.analyze("def (broken:") == []

    def test_issue_has_function_name(self):
        analyzer = ComplexityAnalyzer(ComplexityConfig(max_parameters=1))
        issues = analyzer.analyze(MANY_PARAMS)
        assert issues[0].function_name == "too_many"

    def test_default_config_values(self):
        cfg = ComplexityConfig()
        assert cfg.max_cyclomatic == 10
        assert cfg.max_nesting == 4
        assert cfg.max_function_length == 50
        assert cfg.max_parameters == 5


class TestFormatReport:
    def test_empty_issues(self):
        assert "No complexity issues" in format_complexity_report([])

    def test_non_empty(self):
        issues = [
            ComplexityIssue(code="VS600", message="High", line=1, function_name="foo", value=15),
        ]
        report = format_complexity_report(issues)
        assert "1 complexity issue" in report
        assert "VS600" in report


class TestComplexityIssueStr:
    def test_str_with_function(self):
        issue = ComplexityIssue(code="VS600", message="High", line=5, function_name="foo", value=15)
        s = str(issue)
        assert "foo" in s and "VS600" in s

    def test_str_without_function(self):
        issue = ComplexityIssue(code="VS601", message="Deep", line=3, function_name=None, value=6)
        s = str(issue)
        assert "line 3" in s
