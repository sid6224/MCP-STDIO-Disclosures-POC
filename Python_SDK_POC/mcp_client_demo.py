#!/usr/bin/env python3
"""Python client demo for unsafe vs safe MCP server behavior."""

from __future__ import annotations

import time
from pathlib import Path

import requests

UNSAFE_URL = "http://127.0.0.1:5005/run"
SAFE_URL = "http://127.0.0.1:5006/run"
MARKER = Path("/tmp/mcp_poc_ls.txt")

attack_payload = {
	"command": "/bin/sh",
	"args": ["-c", f"ls -lrth / > {MARKER}"],
}

allowed_payload = {
	"command": "ls",
	"args": ["-lrth", "/"],
}


def test_server(url: str, payload: dict, marker_expected: bool) -> None:
	if MARKER.exists():
		MARKER.unlink()

	print(f"POST {url} with payload: {payload}")
	r = requests.post(url, json=payload, timeout=15)
	print("Response:", r.status_code, r.text)

	time.sleep(1)
	exists = MARKER.exists()
	if marker_expected and exists:
		print(f"OK marker created: {MARKER}")
	elif marker_expected and not exists:
		print(f"FAIL marker not created: {MARKER}")
	elif not marker_expected and exists:
		print(f"FAIL marker should not exist but does: {MARKER}")
	else:
		print("OK marker not created as expected")


if __name__ == "__main__":
	print("--- Testing UNSAFE Python MCP server ---")
	test_server(UNSAFE_URL, attack_payload, marker_expected=True)

	print("\n--- Testing SAFE Python MCP server (attack payload) ---")
	test_server(SAFE_URL, attack_payload, marker_expected=False)

	print("\n--- Testing SAFE Python MCP server (allowed payload) ---")
	test_server(SAFE_URL, allowed_payload, marker_expected=False)