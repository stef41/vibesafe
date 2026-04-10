"""Detect hardcoded secrets, API keys, and credentials."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibesafe.scanner import Issue

SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', "VS200", "Possible OpenAI API key"),
    (r'AKIA[A-Z0-9]{16}', "VS201", "Possible AWS Access Key ID"),
    (r'ghp_[a-zA-Z0-9]{36}', "VS202", "Possible GitHub personal access token"),
    (r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}', "VS202", "Possible GitHub fine-grained token"),
    (r'xox[baprs]-[a-zA-Z0-9\-]{10,}', "VS203", "Possible Slack token"),
    (r'sk-ant-[a-zA-Z0-9\-]{20,}', "VS204", "Possible Anthropic API key"),
    (r'AIza[a-zA-Z0-9\-_]{35}', "VS205", "Possible Google API key"),
    (r'(?:api_key|apikey|secret_key|password|auth_token)\s*=\s*["\'][a-zA-Z0-9+/=]{20,}["\']',
     "VS206", "Possible hardcoded credential"),
    (r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----', "VS207", "Private key in source code"),
    (r'eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}', "VS208", "Possible JWT token"),
    (r'sk_(?:live|test)_[a-zA-Z0-9]{24,}', "VS209", "Possible Stripe secret key"),
    (r'SG\.[a-zA-Z0-9\-_]{22,}\.[a-zA-Z0-9\-_]{22,}', "VS210", "Possible SendGrid API key"),
]

_FALSE_POS = ("example", "xxx", "placeholder", "your_", "test_", "<your", "fake", "dummy")


def check_secrets(path: str, tree, source: str) -> list[Issue]:
    """Detect hardcoded secrets and API keys."""
    from vibesafe.scanner import Issue

    issues: list[Issue] = []

    for i, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        for pattern, code, message in SECRET_PATTERNS:
            case_flag = re.IGNORECASE if "api_key" in pattern else 0
            if re.search(pattern, line, case_flag):
                if any(fp in line.lower() for fp in _FALSE_POS):
                    continue
                issues.append(Issue(
                    path=path, line=i, column=0,
                    severity="error", code=code,
                    message=message,
                    category="secret",
                ))

    return issues
