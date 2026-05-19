
# MCP STDIO Command Execution PoC (Defensive Demo)

![PoC](https://img.shields.io/badge/PoC-Defensive%20Demo-orange)
![MCP](https://img.shields.io/badge/MCP-STDIO-blue)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Go](https://img.shields.io/badge/Go-1.x-00ADD8?logo=go&logoColor=white)
![UI](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![SLM](https://img.shields.io/badge/SLM-Local%20GGUF-green)
![Launcher](https://img.shields.io/badge/Run%20Mode-launch__demo.sh-black)

**Educational Purpose Disclaimer:**

This repository is for educational and defensive demonstration only. It shows how applications using Anthropic MCP SDK patterns can be vulnerable to OS command execution if developer guardrails are not implemented, and how validation can prevent this risk. Do not use the unsafe pattern in production.

## Tested Environment

The demo and validation steps in this README were executed on:

- OS: Ubuntu 24.04.4 LTS
- Kernel: 6.17.0-23-generic
- Python: 3.12.3
- Go: go1.26.2 linux/amd64

Notes:
- Streamlit UI target port: `8501`
- MCP server ports: Python (`5005`/`5006`), Go (`6005`/`6006`)

## Demo Video

- [Screencast from 2026-05-19 16-41-18.webm](Screencast%20from%202026-05-19%2016-41-18.webm)


## Structure

### Python PoC (Python_SDK_POC)
- `Python_SDK_POC/unsafe_mcp_server.py` — Minimal Flask server, **no guardrails**. Forwards any `command`/`args` to MCP SDK, allowing OS command execution.
- `Python_SDK_POC/safe_mcp_server.py` — Same server, but with strict allowlisting. Only allows a specific safe command/script.

### Go PoC (Go_SDK_POC)
- `Go_SDK_POC/unsafe_mcp_server.go` — Minimal HTTP server, no guardrails. Forwards any `command`/`args` to process execution.
- `Go_SDK_POC/safe_mcp_server.go` — Same server with strict allowlisting.
## Guardrails: Unsafe vs Safe Server (Code Comparison)

### Python Unsafe Server (No Guardrails)
```python
# Accepts any command/args from user input and executes them:
params = StdioServerParameters(command=command, args=args)
# This allows arbitrary OS command execution if user input is not validated.
```

### Python Safe Server (With Guardrails)
```python
# Only allows a fixed set of safe commands and arguments:
ALLOWED_COMMAND = "ls"
ALLOWED_ARGS = ["-lrth", "/"]
if command != ALLOWED_COMMAND or args != ALLOWED_ARGS:
	return jsonify({'status': 'rejected', 'reason': 'Command or args not allowed'}), 403
params = StdioServerParameters(command=command, args=args)
# This prevents arbitrary OS command execution by rejecting unapproved input.
```

### Go Unsafe Server (No Guardrails)
```go
// Accepts any command/args from user input and executes them:
cmd := exec.Command(req.Command, req.Args...)
cmd.Run()
// This allows arbitrary OS command execution if user input is not validated.
```

### Go Safe Server (With Guardrails)
```go
// Only allows a fixed set of safe commands and arguments:
if req.Command != allowedCommand || len(req.Args) != 2 || req.Args[0] != allowedArgs[0] || req.Args[1] != allowedArgs[1] {
	// reject
}
cmd := exec.Command(req.Command, req.Args...)
cmd.Run()
// This prevents arbitrary OS command execution by rejecting unapproved input.
```

**Summary:**
- The unsafe servers demonstrate the risk of forwarding user input directly to process execution.
- The safe servers demonstrate how simple allowlisting of commands and arguments can block this risk.

## Database Architecture

Both Python and Go servers use SQLite for the employee database (`demo_employees.db`):

### Database Setup

- **Location**: `Python_SDK_POC/demo_employees.db` and `Go_SDK_POC/demo_employees.db`
- **Auto-creation**: Tables and schema are created automatically on first server startup via `ensure_employee_db()` function.
- **Pre-seeding**: Seeded with 3 sample employees on first run:
	- Asha Rao, Finance
	- Rohan Mehta, Engineering
	- Mira Sen, HR
- **Endpoint**: `/tool/employees` (both safe and unsafe servers) returns the employee list as JSON.
- **Python**: Uses stdlib `sqlite3`; no separate package needed.
- **Go**: Uses `github.com/mattn/go-sqlite3`; included in Go module dependencies.

### Why Database is Committed to Git

The `demo_employees.db` files are committed to the repository to ensure:
- Immediate reproducibility without manual DB setup steps
- Consistent seeded data across clones
- Faster demo startup validation
- No "missing file" errors on first run

If you want a fresh database, simply delete it; both Python and Go servers will recreate it on next startup.

## Streamlit Chat UI Architecture

The `Python_SDK_POC/streamlit_mcp_chat.py` file provides an interactive chat interface that demonstrates both safe and unsafe MCP server behavior.

### UI Features

- **Local SLM**: Uses Qwen2.5-0.5B (tiny model via llama-cpp-python) running locally for inference.
- **Chat Memory**: Maintains a session history of user messages and MCP responses.
- **Business Scenario**: Trained to respond to "show employees" requests by:
	1. Querying `/tool/employees` endpoint to fetch employee records
	2. For unsafe mode: Also fetching `/unsafe/os-listing` endpoint to demonstrate side effects
	3. For safe mode: Only fetching `/tool/employees`, no unsafe side effects
- **Port**: Streamlit runs on `http://localhost:8501`
- **MCP Target**: Connects to either unsafe (`5005`/`6005`) or safe (`5006`/`6006`) server depending on launcher argument.
- **Configuration**: MCP server URL is passed via environment variable `MCP_TARGET_URL` from `launch_demo.sh`.

### Streamlit UI Flow

1. User types a message (e.g., "show employees")
2. Message is sent to local SLM for inference
3. SLM generates tool calls to `/run` endpoint with appropriate command/args
4. Streamlit fetches `/tool/employees` to display employee rows
5. For unsafe mode, Streamlit also fetches `/unsafe/os-listing` if marker file exists
6. UI renders both employee data and side effects (or lack thereof)

## Quickstart

## Python Demo (Authoritative Reproduction Path)

Use this section for reproducible Python demo execution with validation after every step.

### A) One-time setup

1. Go to repo root
```bash
cd /home/siddhartha/MCP-Disclosures
```
2. Validate you are in the correct folder
```bash
pwd
ls -l launch_demo.sh Python_SDK_POC/streamlit_mcp_chat.py Python_SDK_POC/unsafe_mcp_server.py Python_SDK_POC/safe_mcp_server.py
```
Expected: `pwd` ends with `MCP-Disclosures`, and all listed files exist.

3. Create virtual environment and install dependencies
```bash
python3 -m venv Python_SDK_POC/.venv
source Python_SDK_POC/.venv/bin/activate
pip install -r Python_SDK_POC/requirements_streamlit_demo.txt
chmod +x launch_demo.sh
```
4. Validate environment and launcher are ready
```bash
Python_SDK_POC/.venv/bin/python --version
Python_SDK_POC/.venv/bin/pip show streamlit llama-cpp-python requests flask
test -x launch_demo.sh && echo "launch script executable"
```
Expected: Python prints a version, all listed packages show installed metadata, and `launch script executable` is printed.

5. Download local model (one time - ~469MB, ~2-5 minutes on typical internet)
```bash
Python_SDK_POC/.venv/bin/python Python_SDK_POC/download_slm.py
```
**Model Details:**
- **Name**: Qwen2.5-0.5B-Instruct (GGUF quantized)
- **Size**: 469 MB (compressed, Q4_K_M quantization)
- **Purpose**: Local inference engine for chat demo (no external API calls)
- **Location**: `Python_SDK_POC/models/qwen2.5-0.5b-instruct-q4_k_m.gguf`
- **Download Source**: HuggingFace (via `llama-cpp-python` auto-downloader)
- **Why not in GitHub**: Model files are too large for typical Git repositories (GitHub recommends <100MB per file). Downloaded once and cached locally.
- **Reuse**: Model is cached after first download; subsequent runs reuse the file (no re-download).

6. Validate model file exists
```bash
ls -lh Python_SDK_POC/models/qwen2.5-0.5b-instruct-q4_k_m.gguf
```
Expected: model file is present with non-zero size (should be ~469MB).

### B) Unsafe Python demo via launcher

1. Stop old processes and free demo ports
```bash
pkill -f unsafe_mcp_server.py || true
pkill -f safe_mcp_server.py || true
fuser -k 5005/tcp 5006/tcp 8501/tcp || true
```
2. Validate ports are free
```bash
ss -tulnp | grep -E ':5005|:5006|:8501' || echo "ports free"
```
Expected: either no output from `ss` or `ports free` printed.

3. Run Python unsafe demo (from repo root)
```bash
./launch_demo.sh python unsafe
```
4. Validate server and UI startup logs
Expected terminal lines include:
- `Starting MCP server: /home/siddhartha/MCP-Disclosures/Python_SDK_POC/.venv/bin/python /home/siddhartha/MCP-Disclosures/Python_SDK_POC/unsafe_mcp_server.py`
- `Launching Streamlit chat UI (target MCP: http://127.0.0.1:5005/run)`
- `Local URL: http://localhost:8501`

5. Validate unsafe tool endpoint in another terminal
```bash
curl -i http://127.0.0.1:5005/tool/employees
```
6. Validate endpoint response
Expected:
- HTTP status `200 OK`
- JSON with `"status":"ok"`
- `employees` array with seeded rows.

7. In Streamlit UI (`http://localhost:8501`), enter:
```text
show employees
```
8. Validate unsafe behavior in UI
Expected:
- employee records are shown
- unsafe OS listing side effect section appears.

9. Validate marker file exists (another terminal)
```bash
ls -l /tmp/mcp_unsafe_os_listing.txt
head -n 5 /tmp/mcp_unsafe_os_listing.txt
```
Expected: file exists and contains directory listing output.

10. Stop unsafe run
Action: press `Ctrl+C` in the terminal running `launch_demo.sh`.
11. Validate unsafe services stopped
```bash
ss -tulnp | grep -E ':5005|:8501' || echo "unsafe stack stopped"
```
Expected: no listeners on `5005`/`8501`, or `unsafe stack stopped` printed.

### C) Safe Python demo via launcher

1. Remove unsafe marker before safe run
```bash
rm -f /tmp/mcp_unsafe_os_listing.txt
```
2. Validate marker is absent
```bash
test ! -f /tmp/mcp_unsafe_os_listing.txt && echo "marker removed"
```
Expected: `marker removed`.

3. Run Python safe demo (from repo root)
```bash
./launch_demo.sh python safe
```
4. Validate server and UI startup logs
Expected terminal lines include:
- `Starting MCP server: /home/siddhartha/MCP-Disclosures/Python_SDK_POC/.venv/bin/python /home/siddhartha/MCP-Disclosures/Python_SDK_POC/safe_mcp_server.py`
- `Launching Streamlit chat UI (target MCP: http://127.0.0.1:5006/run)`
- `Local URL: http://localhost:8501`

5. Validate safe tool endpoint in another terminal
```bash
curl -i http://127.0.0.1:5006/tool/employees
```
6. Validate endpoint response
Expected:
- HTTP status `200 OK`
- JSON with `"status":"ok"`
- `employees` array present.

7. Validate `/run` guardrail is enforced
```bash
curl -i -X POST http://127.0.0.1:5006/run \
	-H 'Content-Type: application/json' \
	-d '{"command":"touch","args":["/tmp/should_not_create"]}'
```
8. Validate guardrail response
Expected:
- HTTP status `403 Forbidden`
- JSON/body indicates command rejection.

9. In Streamlit UI (`http://localhost:8501`), enter:
```text
show employees
```
10. Validate safe behavior in UI and filesystem
Expected:
- employee records are shown
- no unsafe listing section is shown
- unsafe marker remains absent:
```bash
test ! -f /tmp/mcp_unsafe_os_listing.txt && echo "no unsafe side effect"
```

### D) Python demo notes

- SQLite is provided by Python stdlib (`sqlite3`); no separate Ubuntu SQLite package is required for this repo flow.
- Unsafe targets are for controlled defensive lab demos only.
- `llama-cpp-python` install/build time can vary by machine.

## Go Demo (Authoritative Reproduction Path)

Use this section for reproducible Go demo execution with validation after every step.

### A) One-time setup and build

1. Go to repo root
	```bash
	cd /home/siddhartha/MCP-Disclosures
	```
2. Validate you are in the correct folder
	```bash
	pwd
	ls -l launch_demo.sh Go_SDK_POC/unsafe_mcp_server.go Go_SDK_POC/safe_mcp_server.go
	```
	Expected: `pwd` ends with `MCP-Disclosures`, and all listed files exist.

3. Build Go binaries
	```bash
	cd Go_SDK_POC
	go mod tidy
	go build -o unsafe_mcp_server unsafe_mcp_server.go
	go build -o safe_mcp_server safe_mcp_server.go
	cd ..
	```
4. Validate binaries were created
	```bash
	ls -l Go_SDK_POC/unsafe_mcp_server Go_SDK_POC/safe_mcp_server
	```
	Expected: both binaries exist and are executable.

### B) Unsafe Go demo via launcher

1. Stop old processes and free demo ports
	```bash
	pkill -f unsafe_mcp_server || true
	pkill -f safe_mcp_server || true
	fuser -k 6005/tcp 6006/tcp 8501/tcp || true
	```
2. Validate ports are free
	```bash
	ss -tulnp | grep -E ':6005|:6006|:8501' || echo "ports free"
	```
	Expected: either no output from `ss` or `ports free` printed.

3. Run Go unsafe demo (from repo root)
	```bash
	./launch_demo.sh go unsafe
	```
4. Validate server and UI startup logs
	Expected terminal lines include:
	- `Starting MCP server: /home/siddhartha/MCP-Disclosures/Go_SDK_POC/unsafe_mcp_server`
	- `Launching Streamlit chat UI (target MCP: http://127.0.0.1:6005/run)`
	- `Local URL: http://localhost:8501`

5. Validate unsafe tool endpoint in another terminal
	```bash
	curl -i http://127.0.0.1:6005/tool/employees
	```
6. Validate endpoint response
	Expected:
	- HTTP status `200 OK`
	- JSON with `"status":"ok"`
	- `employees` array with seeded rows.

7. In Streamlit UI (`http://localhost:8501`), enter:
	```text
	show employees
	```
8. Validate unsafe behavior in UI
	Expected:
	- employee records are shown
	- unsafe OS listing side effect section appears.

9. Validate marker file exists (another terminal)
	```bash
	ls -l /tmp/mcp_unsafe_os_listing.txt
	head -n 5 /tmp/mcp_unsafe_os_listing.txt
	```
	Expected: file exists and contains directory listing output.

10. Stop unsafe run
	Action: press `Ctrl+C` in the terminal running `launch_demo.sh`.
11. Validate unsafe services stopped
	```bash
	ss -tulnp | grep -E ':6005|:8501' || echo "unsafe stack stopped"
	```
	Expected: no listeners on `6005`/`8501`, or `unsafe stack stopped` printed.

### C) Safe Go demo via launcher

1. Remove unsafe marker before safe run
	```bash
	rm -f /tmp/mcp_unsafe_os_listing.txt
	```
2. Validate marker is absent
	```bash
	test ! -f /tmp/mcp_unsafe_os_listing.txt && echo "marker removed"
	```
	Expected: `marker removed`.

3. Run Go safe demo (from repo root)
	```bash
	./launch_demo.sh go safe
	```
4. Validate server and UI startup logs
	Expected terminal lines include:
	- `Starting MCP server: /home/siddhartha/MCP-Disclosures/Go_SDK_POC/safe_mcp_server`
	- `SAFE Go MCP server running on http://127.0.0.1:6006`
	- `Launching Streamlit chat UI (target MCP: http://127.0.0.1:6006/run)`
	- `Local URL: http://localhost:8501`

5. Validate safe tool endpoint in another terminal
	```bash
	curl -i http://127.0.0.1:6006/tool/employees
	```
6. Validate endpoint response
	Expected:
	- HTTP status `200 OK`
	- JSON with `"status":"ok"`
	- `employees` array present.

7. Validate `/run` guardrail is enforced
	```bash
	curl -i -X POST http://127.0.0.1:6006/run \
	  -H 'Content-Type: application/json' \
	  -d '{"command":"touch","args":["/tmp/should_not_create"]}'
	```
8. Validate guardrail response
	Expected:
	- HTTP status `403 Forbidden`
	- JSON/body indicates command rejection.

9. In Streamlit UI (`http://localhost:8501`), enter:
	```text
	show employees
	```
10. Validate safe behavior in UI and filesystem
	Expected:
	- employee records are shown
	- no unsafe listing section is shown
	- unsafe marker remains absent:
	```bash
	test ! -f /tmp/mcp_unsafe_os_listing.txt && echo "no unsafe side effect"
	```

## Repository File Tracking

### Database Files (`.db` files)

The `demo_employees.db` files in both `Python_SDK_POC/` and `Go_SDK_POC/` are committed to Git. This ensures:
- New clones include pre-seeded demo data
- No wait for DB creation on first run
- Faster validation and reproducibility

If you need a fresh database, simply delete the `.db` file; the server will recreate it on startup.

## What to Observe

- Python realistic Streamlit path:
	- `python unsafe` + `show employees`: OS listing marker `/tmp/mcp_unsafe_os_listing.txt` is produced and displayed, then employee rows are shown.
	- `python safe` + `show employees`: employee rows are shown with no unsafe OS listing side effect.
- Safe server `/run` allowlist remains `ls -lrth /`; other `command`/`args` are rejected.

## References

- [OX Security: The Mother of All AI Supply Chains](https://www.ox.security/blog/the-mother-of-all-ai-supply-chains-critical-systemic-vulnerability-at-the-core-of-the-mcp/)

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.