"""Detect hallucinated imports - packages that don't exist."""

from __future__ import annotations

import ast
import importlib.util
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibesafe.scanner import Issue

_STDLIB_MODULES: set | None = None


def _get_stdlib_modules() -> set:
    global _STDLIB_MODULES
    if _STDLIB_MODULES is None:
        if hasattr(sys, "stdlib_module_names"):
            _STDLIB_MODULES = set(sys.stdlib_module_names)
        else:
            _STDLIB_MODULES = {
                "abc", "argparse", "array", "ast", "asyncio", "atexit", "base64",
                "binascii", "bisect", "builtins", "bz2", "calendar", "cmath", "cmd",
                "code", "codecs", "collections", "colorsys", "compileall", "concurrent",
                "configparser", "contextlib", "contextvars", "copy", "csv", "ctypes",
                "curses", "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis",
                "distutils", "doctest", "email", "encodings", "enum", "errno",
                "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch", "fractions",
                "ftplib", "functools", "gc", "getopt", "getpass", "gettext", "glob",
                "gzip", "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib",
                "importlib", "inspect", "io", "ipaddress", "itertools", "json", "keyword",
                "linecache", "locale", "logging", "lzma", "mailbox", "marshal", "math",
                "mimetypes", "mmap", "multiprocessing", "netrc", "numbers", "operator",
                "optparse", "os", "pathlib", "pdb", "pickle", "pickletools", "pkgutil",
                "platform", "plistlib", "poplib", "posixpath", "pprint", "profile",
                "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue",
                "quopri", "random", "re", "readline", "reprlib", "resource", "runpy",
                "sched", "secrets", "select", "selectors", "shelve", "shlex", "shutil",
                "signal", "site", "smtplib", "socket", "socketserver", "sqlite3", "ssl",
                "stat", "statistics", "string", "struct", "subprocess", "symtable", "sys",
                "sysconfig", "syslog", "tabnanny", "tarfile", "tempfile", "termios",
                "test", "textwrap", "threading", "time", "timeit", "tkinter", "token",
                "tokenize", "trace", "traceback", "tracemalloc", "tty", "types", "typing",
                "unicodedata", "unittest", "urllib", "uuid", "venv", "warnings", "wave",
                "weakref", "webbrowser", "wsgiref", "xml", "xmlrpc", "zipapp", "zipfile",
                "zipimport", "zlib", "_thread", "__future__", "typing_extensions",
                "grp", "posix",
            }
    return _STDLIB_MODULES


KNOWN_PACKAGES = {
    "numpy", "pandas", "scipy", "matplotlib", "sklearn", "scikit_learn",
    "torch", "tensorflow", "keras", "jax", "flax",
    "requests", "httpx", "aiohttp", "flask", "django", "fastapi", "starlette",
    "pydantic", "attrs", "click", "typer", "rich", "tqdm",
    "pytest", "hypothesis", "mock", "coverage",
    "celery", "redis", "pymongo", "sqlalchemy", "psycopg2",
    "boto3", "botocore", "google", "azure",
    "PIL", "pillow", "cv2",
    "transformers", "tokenizers", "datasets", "huggingface_hub",
    "openai", "anthropic", "langchain", "litellm",
    "yaml", "toml", "tomllib", "tomli",
    "dotenv", "decouple",
    "setuptools", "pip", "wheel", "build", "hatchling",
    "black", "ruff", "isort", "mypy", "pylint", "flake8",
    "docker", "paramiko", "fabric",
    "networkx", "sympy", "numba",
    "dask", "ray", "prefect", "airflow",
    "streamlit", "gradio", "dash", "plotly", "seaborn", "bokeh",
    "bs4", "beautifulsoup4", "scrapy", "lxml",
    "cryptography", "jwt", "bcrypt", "passlib",
    "loguru", "structlog",
    "arrow", "pendulum", "dateutil",
    "orjson", "ujson", "msgpack",
    "tenacity", "backoff",
    "sentry_sdk", "prometheus_client",
    "mcp", "vibesafe", "injectionguard",
    "six", "certifi", "charset_normalizer", "idna", "urllib3",
    "packaging", "pyparsing", "pygments", "markupsafe", "jinja2",
    "werkzeug", "itsdangerous",
}


def check_imports(path: str, tree: ast.AST, source: str) -> list[Issue]:
    """Detect potentially hallucinated imports."""
    from vibesafe.scanner import Issue

    issues: list[Issue] = []
    stdlib = _get_stdlib_modules()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if not _is_known_module(top, stdlib):
                    issues.append(Issue(
                        path=path, line=node.lineno, column=node.col_offset,
                        severity="warning", code="VS300",
                        message=f"Import '{alias.name}' - package '{top}' not found (hallucinated import?)",
                        category="import",
                    ))

        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                top = node.module.split(".")[0]
                if not _is_known_module(top, stdlib):
                    issues.append(Issue(
                        path=path, line=node.lineno, column=node.col_offset,
                        severity="warning", code="VS300",
                        message=f"Import from '{node.module}' - package '{top}' not found (hallucinated import?)",
                        category="import",
                    ))

    return issues


def _is_known_module(name: str, stdlib: set) -> bool:
    """Check if a module is known (stdlib, installed, or popular)."""
    if name in stdlib:
        return True
    try:
        if importlib.util.find_spec(name) is not None:
            return True
    except (ModuleNotFoundError, ValueError):
        pass
    if name in KNOWN_PACKAGES:
        return True
    return False
