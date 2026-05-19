#!/usr/bin/env python3
"""UNSAFE MCP server demo (Python).

Accepts arbitrary command/args from JSON and forwards them to MCP stdio launch
without validation. This is intentionally unsafe for educational demonstration.
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

app = Flask(__name__)

DB_PATH = Path(__file__).resolve().parent / "demo_employees.db"
UNSAFE_OS_MARKER = Path("/tmp/mcp_unsafe_os_listing.txt")


async def trigger_stdio(command: str, args: list[str]) -> str:
	params = StdioServerParameters(command=command, args=args)
	try:
		async with stdio_client(params) as (read, write):
			async with ClientSession(read, write) as session:
				await session.initialize()
		return "mcp_initialized"
	except Exception as exc:
		# Expected when command is not a real MCP server; side effects may still happen.
		return f"spawned_with_handshake_error: {type(exc).__name__}: {exc}"


def ensure_employee_db() -> None:
	with sqlite3.connect(DB_PATH) as conn:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS employees (
				id INTEGER PRIMARY KEY,
				name TEXT NOT NULL,
				department TEXT NOT NULL,
				email TEXT NOT NULL
			)
			"""
		)
		count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
		if count == 0:
			conn.executemany(
				"INSERT INTO employees (name, department, email) VALUES (?, ?, ?)",
				[
					("Asha Rao", "Finance", "asha.rao@example.com"),
					("Rohan Mehta", "Engineering", "rohan.mehta@example.com"),
					("Mira Sen", "HR", "mira.sen@example.com"),
				],
			)
			conn.commit()


def fetch_employees() -> list[dict[str, str | int]]:
	with sqlite3.connect(DB_PATH) as conn:
		rows = conn.execute(
			"SELECT id, name, department, email FROM employees ORDER BY id"
		).fetchall()
	return [
		{"id": row[0], "name": row[1], "department": row[2], "email": row[3]}
		for row in rows
	]


@app.post("/run")
def run() -> tuple[str, int] | tuple[dict, int] | dict:
	data = request.get_json(force=True)
	command = str(data.get("command", ""))
	args = [str(x) for x in data.get("args", [])]

	result = asyncio.run(trigger_stdio(command, args))
	return jsonify({"status": "executed", "command": command, "args": args, "detail": result})


@app.get("/tool/employees")
def employees() -> dict:
	ensure_employee_db()
	return jsonify({"status": "ok", "employees": fetch_employees()})


@app.get("/unsafe/os-listing")
def unsafe_os_listing() -> tuple[dict, int] | dict:
	if not UNSAFE_OS_MARKER.exists():
		return jsonify({"status": "missing", "detail": "No marker file yet"}), 404

	content = UNSAFE_OS_MARKER.read_text(encoding="utf-8", errors="replace")
	return jsonify({"status": "ok", "path": str(UNSAFE_OS_MARKER), "listing": content})


if __name__ == "__main__":
	ensure_employee_db()
	app.run(host="127.0.0.1", port=5005)