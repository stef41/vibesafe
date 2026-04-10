"""Tests for the vibesafe MCP server."""

import json

import pytest

from vibesafe.mcp import MCPServer, TOOLS, run_server


@pytest.fixture
def server():
    return MCPServer()


# --- tools/list ---

def test_tools_list(server):
    resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert resp["id"] == 1
    assert "error" not in resp
    tools = resp["result"]["tools"]
    assert len(tools) == 3
    names = {t["name"] for t in tools}
    assert names == {"vibesafe_scan", "vibesafe_scan_file", "vibesafe_fix"}


def test_tools_list_has_schemas(server):
    resp = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    for tool in resp["result"]["tools"]:
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


# --- initialize ---

def test_initialize(server):
    resp = server.handle_request({"jsonrpc": "2.0", "id": 0, "method": "initialize"})
    assert resp["result"]["serverInfo"]["name"] == "vibesafe"
    assert "tools" in resp["result"]["capabilities"]


# --- unknown method ---

def test_unknown_method(server):
    resp = server.handle_request({"jsonrpc": "2.0", "id": 3, "method": "foo/bar"})
    assert "error" in resp
    assert resp["error"]["code"] == -32601


# --- vibesafe_scan ---

def test_scan_clean_code(server):
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 10, "method": "tools/call",
        "params": {"name": "vibesafe_scan", "arguments": {"code": "x = 1\n"}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["issue_count"] == 0
    assert content["issues"] == []


def test_scan_detects_eval(server):
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 11, "method": "tools/call",
        "params": {"name": "vibesafe_scan", "arguments": {"code": "eval(input())\n"}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["issue_count"] > 0
    assert any("eval" in i["message"].lower() or "VS" in i["code"] for i in content["issues"])


def test_scan_empty_code(server):
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 12, "method": "tools/call",
        "params": {"name": "vibesafe_scan", "arguments": {"code": ""}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["issue_count"] == 0


# --- vibesafe_scan_file ---

def test_scan_file_missing_path(server):
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 20, "method": "tools/call",
        "params": {"name": "vibesafe_scan_file", "arguments": {"path": ""}},
    })
    assert "error" in resp


def test_scan_file_nonexistent(server):
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 21, "method": "tools/call",
        "params": {"name": "vibesafe_scan_file", "arguments": {"path": "/tmp/does_not_exist_abc.py"}},
    })
    # Scanner may return empty issues or an error for missing files
    assert "result" in resp


def test_scan_file_real(server, tmp_path):
    f = tmp_path / "safe.py"
    f.write_text("x = 1\n")
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 22, "method": "tools/call",
        "params": {"name": "vibesafe_scan_file", "arguments": {"path": str(f)}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["issue_count"] == 0


# --- vibesafe_fix ---

def test_fix_clean_code(server):
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 30, "method": "tools/call",
        "params": {"name": "vibesafe_fix", "arguments": {"code": "x = 1\n"}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["changed"] is False
    assert content["fixes_applied"] == []


def test_fix_returns_fixed_source(server):
    code = "import os\nimport sys\nx = 1\n"
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 31, "method": "tools/call",
        "params": {"name": "vibesafe_fix", "arguments": {"code": code}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert "fixed_source" in content


# --- unknown tool ---

def test_unknown_tool(server):
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 40, "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
    })
    assert "error" in resp
    assert resp["error"]["code"] == -32602


# --- JSON-RPC structure ---

def test_response_has_jsonrpc_field(server):
    resp = server.handle_request({"jsonrpc": "2.0", "id": 50, "method": "tools/list"})
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 50


def test_missing_params_defaults(server):
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 60, "method": "tools/call",
        "params": {"name": "vibesafe_scan", "arguments": {}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["issue_count"] == 0
