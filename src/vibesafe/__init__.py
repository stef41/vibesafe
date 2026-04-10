"""vibesafe - AI-generated code safety scanner for the vibe coding era."""

__version__ = "0.3.0"

from vibesafe.scanner import Scanner, ScanResult, Issue
from vibesafe.scanner import scan_file, scan_directory, scan_code
from vibesafe.fixer import fix_file, fix_source, FixResult, can_fix, FIXABLE_CODES
from vibesafe.complexity import (
    ComplexityAnalyzer, ComplexityConfig, ComplexityIssue, format_complexity_report,
)
from vibesafe.sarif import (
    SarifReport, SarifResult, from_scan_results, sarif_level,
)

__all__ = [
    "Scanner", "ScanResult", "Issue",
    "scan_file", "scan_directory", "scan_code",
    "fix_file", "fix_source", "FixResult", "can_fix", "FIXABLE_CODES",
    "ComplexityAnalyzer", "ComplexityConfig", "ComplexityIssue", "format_complexity_report",
    "SarifReport", "SarifResult", "from_scan_results", "sarif_level",
]
