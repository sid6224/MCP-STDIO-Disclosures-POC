#!/usr/bin/env python3
"""Streamlit chat interface using a local tiny model + MCP server interaction."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from llama_cpp import Llama

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
DEFAULT_SYSTEM_PROMPT = (
    "You are a local assistant for an MCP security demo. "
    "Answer briefly and clearly. If the user asks to run something, suggest a shell command and args as JSON."
)

MCP_TARGETS = {
    "Python Unsafe (5005)": "http://127.0.0.1:5005/run",
    "Python Safe (5006)": "http://127.0.0.1:5006/run",
    "Go Unsafe (6005)": "http://127.0.0.1:6005/run",
    "Go Safe (6006)": "http://127.0.0.1:6006/run",
}
UNSAFE_MARKER_PATH = "/tmp/mcp_unsafe_os_listing.txt"


def get_default_target_index() -> int:
    env_url = os.getenv("MCP_TARGET_URL", "").strip()
    if not env_url:
        return 0
    options = list(MCP_TARGETS.values())
    try:
        return options.index(env_url)
    except ValueError:
        return 0


def build_prompt(system_prompt: str, history: list[dict[str, str]], user_text: str) -> str:
    lines = [f"System: {system_prompt}"]
    for msg in history[-8:]:
        lines.append(f"{msg['role'].capitalize()}: {msg['content']}")

    lines.append(
        "User: "
        + user_text
        + "\nAssistant: Return JSON only with shape "
        + '{"assistant_response": "...", "mcp_request": {"command": "...", "args": ["..."]}}'
    )
    return "\n".join(lines)


@st.cache_resource(show_spinner=False)
def load_llm(model_path: str) -> Llama:
    return Llama(model_path=model_path, n_ctx=2048, n_threads=4, verbose=False)


def generate_json_response(llm: Llama, prompt: str, max_tokens: int) -> dict[str, Any]:
    result = llm.create_completion(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.2,
        stop=["\nUser:", "\nSystem:"],
    )
    raw = result["choices"][0]["text"].strip()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback if model does not output strict JSON.
        payload = {
            "assistant_response": raw,
            "mcp_request": {"command": "ls", "args": ["-lrth", "/"]},
        }

    if "assistant_response" not in payload:
        payload["assistant_response"] = str(payload)
    if "mcp_request" not in payload or not isinstance(payload["mcp_request"], dict):
        payload["mcp_request"] = {"command": "ls", "args": ["-lrth", "/"]}

    command = str(payload["mcp_request"].get("command", "ls"))
    args = payload["mcp_request"].get("args", ["-lrth", "/"])
    if not isinstance(args, list):
        args = [str(args)]
    payload["mcp_request"] = {"command": command, "args": [str(a) for a in args]}
    return payload


def send_to_mcp(url: str, command: str, args: list[str]) -> tuple[int, str]:
    response = requests.post(url, json={"command": command, "args": args}, timeout=20)
    return response.status_code, response.text


def base_url_from_run_url(run_url: str) -> str:
    return run_url.rsplit("/run", 1)[0]


def fetch_employee_tool(run_url: str) -> tuple[int, Any]:
    response = requests.get(f"{base_url_from_run_url(run_url)}/tool/employees", timeout=20)
    return response.status_code, response.json()


def fetch_unsafe_os_listing(run_url: str) -> tuple[int, Any]:
    response = requests.get(f"{base_url_from_run_url(run_url)}/unsafe/os-listing", timeout=20)
    try:
        payload = response.json()
    except ValueError:
        payload = {"status": "error", "detail": response.text}
    return response.status_code, payload


def init_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def main() -> None:
    st.set_page_config(page_title="SLM + MCP Demo", page_icon="AI", layout="wide")
    init_state()

    st.title("Local SLM Chat + MCP Server Demo")
    st.caption("Uses llama.cpp locally and can forward model-suggested command/args to Python or Go MCP servers.")
    st.warning("Unsafe MCP targets are for controlled lab demos only.")

    with st.sidebar:
        st.header("Settings")
        model_path = st.text_input("GGUF model path", value=str(DEFAULT_MODEL_PATH))
        selected_target = st.selectbox(
            "MCP target",
            options=list(MCP_TARGETS.keys()),
            index=get_default_target_index(),
        )
        auto_send = st.checkbox("Auto-send suggested MCP request", value=False)
        max_tokens = st.slider("Max generation tokens", min_value=64, max_value=512, value=220, step=16)
        system_prompt = st.text_area("System prompt", value=DEFAULT_SYSTEM_PROMPT, height=120)

    try:
        llm = load_llm(model_path)
    except Exception as exc:
        st.error(
            "Model could not be loaded. Download it first with: "
            "python Python_SDK_POC/download_slm.py\n"
            f"Error: {type(exc).__name__}: {exc}"
        )
        st.stop()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_text = st.chat_input("Ask the local model (example: show employees)")
    if not user_text:
        return

    st.session_state.chat_history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    mcp_url = MCP_TARGETS[selected_target]
    is_employee_query = "employee" in user_text.lower()

    if is_employee_query:
        response_lines = [
            "Employee tool call requested.",
            f"Target: {selected_target} -> {mcp_url}",
        ]

        if "Unsafe" in selected_target:
            attack_payload = {
                "command": "/bin/sh",
                "args": ["-c", f"ls -lrth / > {UNSAFE_MARKER_PATH}"],
            }
            attack_status, attack_body = send_to_mcp(
                mcp_url,
                attack_payload["command"],
                attack_payload["args"],
            )
            response_lines.extend(
                [
                    "",
                    "Unsafe path triggered a crafted stdio launch payload.",
                    f"Unsafe MCP /run response [{attack_status}]: {attack_body}",
                ]
            )

            marker_status, marker_payload = fetch_unsafe_os_listing(mcp_url)
            response_lines.extend(
                [
                    f"Unsafe OS listing endpoint response [{marker_status}]",
                    str(marker_payload.get("listing", marker_payload)),
                ]
            )

        emp_status, emp_payload = fetch_employee_tool(mcp_url)
        response_lines.extend(
            [
                "",
                f"Employee tool response [{emp_status}]",
                json.dumps(emp_payload, indent=2),
            ]
        )
        assistant_final = "\n".join(response_lines)
    else:
        prompt = build_prompt(system_prompt, st.session_state.chat_history, user_text)
        payload = generate_json_response(llm, prompt, max_tokens=max_tokens)

        assistant_text = payload["assistant_response"]
        mcp_req = payload["mcp_request"]
        response_lines = [
            assistant_text,
            "",
            f"Suggested MCP payload: {json.dumps(mcp_req)}",
            f"Target: {selected_target} -> {mcp_url}",
        ]

        mcp_status = None
        mcp_body = None
        if auto_send:
            mcp_status, mcp_body = send_to_mcp(mcp_url, mcp_req["command"], mcp_req["args"])
            response_lines.extend(["", f"MCP response [{mcp_status}]: {mcp_body}"])

        assistant_final = "\n".join(response_lines)
    st.session_state.chat_history.append({"role": "assistant", "content": assistant_final})

    with st.chat_message("assistant"):
        st.write(assistant_final)
        if not auto_send and not is_employee_query:
            if st.button("Send suggested payload to MCP now"):
                mcp_status, mcp_body = send_to_mcp(mcp_url, mcp_req["command"], mcp_req["args"])
                st.success(f"MCP response [{mcp_status}]: {mcp_body}")


if __name__ == "__main__":
    main()
