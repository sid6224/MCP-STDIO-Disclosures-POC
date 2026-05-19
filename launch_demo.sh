#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_DIR="$ROOT_DIR/Python_SDK_POC"
GO_DIR="$ROOT_DIR/Go_SDK_POC"
VENV_PY="$PY_DIR/.venv/bin/python"

usage() {
  echo "Usage: $0 [python|go] [safe|unsafe]"
  echo "Example: $0 python safe"
}

STACK="${1:-python}"
MODE="${2:-safe}"

if [[ "$STACK" != "python" && "$STACK" != "go" ]]; then
  usage
  exit 1
fi

if [[ "$MODE" != "safe" && "$MODE" != "unsafe" ]]; then
  usage
  exit 1
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "Python virtual environment not found at $VENV_PY"
  echo "Create it first: python3 -m venv Python_SDK_POC/.venv"
  exit 1
fi

if [[ "$STACK" == "python" ]]; then
  if [[ "$MODE" == "safe" ]]; then
    MCP_CMD=("$VENV_PY" "$PY_DIR/safe_mcp_server.py")
    MCP_URL="http://127.0.0.1:5006/run"
  else
    MCP_CMD=("$VENV_PY" "$PY_DIR/unsafe_mcp_server.py")
    MCP_URL="http://127.0.0.1:5005/run"
  fi
else
  if [[ "$MODE" == "safe" ]]; then
    GO_FILE="$GO_DIR/safe_mcp_server.go"
    GO_BIN="$GO_DIR/safe_mcp_server"
    MCP_URL="http://127.0.0.1:6006/run"
  else
    GO_FILE="$GO_DIR/unsafe_mcp_server.go"
    GO_BIN="$GO_DIR/unsafe_mcp_server"
    MCP_URL="http://127.0.0.1:6005/run"
  fi

  if [[ ! -x "$GO_BIN" ]]; then
    echo "Building $GO_FILE ..."
    (cd "$GO_DIR" && go build "$(basename "$GO_FILE")")
  fi
  MCP_CMD=("$GO_BIN")
fi

cleanup() {
  if [[ -n "${MCP_PID:-}" ]]; then
    kill "$MCP_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting MCP server: ${MCP_CMD[*]}"
"${MCP_CMD[@]}" &
MCP_PID=$!

sleep 1

echo "Launching Streamlit chat UI (target MCP: $MCP_URL)"
export MCP_TARGET_URL="$MCP_URL"
exec "$VENV_PY" -m streamlit run "$PY_DIR/streamlit_mcp_chat.py" --server.headless true
