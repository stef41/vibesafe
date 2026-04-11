"""MCP (Model Context Protocol) server exposing vibesafe scanning as tools."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from typing import Any

from vibesafe.scanner import scan_code, scan_file, Issue
from vibesafe.fixer import fix_source


TOOLS = [
    {
        "name": "vibesafe_scan",
        "description": "Scan Python code for security issues",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source code to scan"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "vibesafe_scan_file",
        "description": "Scan a Python file for security issues",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the Python file to scan"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "vibesafe_fix",
        "description": "Auto-fix security issues in Python code",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source code to fix"},
            },
            "required": ["code"],
        },
    },
]


def _issues_to_dicts(issues: list[Issue]) -> list[dict[str, Any]]:
    return [
        {
            "path": i.path,
            "line": i.line,
            "column": i.column,
            "severity": i.severity,
            "code": i.code,
            "message": i.message,
            "category": i.category,
        }
        for i in issues
    ]


def _error_response(id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def _success_response(id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id, "result": result}


class MCPServer:
    """MCP server that exposes vibesafe tools via JSON-RPC."""

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle a single JSON-RPC request and return a response dict."""
        req_id = request.get("id")
        method = request.get("method", "")

        if method == "initialize":
            return _success_response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "vibesafe", "version": "0.1.0"},
            })

        if method == "tools/list":
            return _success_response(req_id, {"tools": TOOLS})

        if method == "tools/call":
            return self._handle_tool_call(request)

        return _error_response(req_id, -32601, f"Method not found: {method}")

    def _handle_tool_call(self, request: dict[str, Any]) -> dict[str, Any]:
        req_id = request.get("id")
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "vibesafe_scan":
                return self._tool_scan(req_id, arguments)
            elif tool_name == "vibesafe_scan_file":
                return self._tool_scan_file(req_id, arguments)
            elif tool_name == "vibesafe_fix":
                return self._tool_fix(req_id, arguments)
            else:
                return _error_response(req_id, -32602, f"Unknown tool: {tool_name}")
        except Exception as exc:
            return _success_response(req_id, {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            })

    def _tool_scan(self, req_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        code = arguments.get("code", "")
        issues = scan_code(code)
        result_data = {
            "issue_count": len(issues),
            "issues": _issues_to_dicts(issues),
        }
        return _success_response(req_id, {
            "content": [{"type": "text", "text": json.dumps(result_data)}],
        })

    def _tool_scan_file(self, req_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        path = arguments.get("path", "")
        if not path:
            return _error_response(req_id, -32602, "Missing required parameter: path")
        # Prevent path traversal via symlinks — resolve to canonical path
        resolved = os.path.realpath(path)
        if os.path.basename(resolved) != os.path.basename(path.rstrip(os.sep)):
            return _error_response(req_id, -32602, "Path traversal not allowed")
        issues = scan_file(resolved)
        result_data = {
            "issue_count": len(issues),
            "issues": _issues_to_dicts(issues),
        }
        return _success_response(req_id, {
            "content": [{"type": "text", "text": json.dumps(result_data)}],
        })

    def _tool_fix(self, req_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        code = arguments.get("code", "")
        result = fix_source(code)
        result_data = {
            "changed": result.changed,
            "fixes_applied": result.fixes_applied,
            "fixed_source": result.fixed_source,
        }
        return _success_response(req_id, {
            "content": [{"type": "text", "text": json.dumps(result_data)}],
        })


def run_server() -> None:
    """Run the MCP server, reading JSON-RPC requests from stdin line by line."""
    server = MCPServer()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = _error_response(None, -32700, "Parse error")
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        response = server.handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    run_server()
