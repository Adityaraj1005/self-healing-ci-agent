# Autonomous Self-Healing CI Agent 🤖🛡️

An autonomous, closed-loop CI repair system that detects failing unit test suites, diagnoses errors, generates targeted code patches, and verifies fixes inside disposable, isolated Docker execution sandboxes.

---

## 🎯 Architecture & Design Overview

Rather than relying on ungrounded code generation or running untrusted AI-generated patches directly on the host machine, this system operates under a **Verify-in-Sandbox** loop:

```text
        [ Failing Test Suite Detected ]
                       │
                       ▼
        ┌─────────────────────────────┐
        │   Traceback Regex Parser    │
        │ (Extract File, Line, Error) │
        └──────────────┬──────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │       Gemini AI Agent       │◄─────────────┐
        │  (Reasoning & Tool Calling) │              │
        └──────────────┬──────────────┘              │
                       │                             │
          Inspect Code / Write Patch                │
                       │                             │
                       ▼                             │
        ┌─────────────────────────────┐              │
        │    Docker Linux Sandbox    │              │
        │    (python:3.10-slim)      │──────────────┘
        │   [Isolated Bind Mount]    │
        └──────────────┬──────────────┘
                       │
              All Tests Pass (Exit 0)
                       ▼
                [ Fix Verified ]
```

### Key Engineering Principles

* **No Host Execution:** Untrusted code and tests never execute directly on the host environment. All executions run inside an isolated Linux container.
* **Ephemeral Sandbox Lifecycle:** Containers are created per test run and guaranteed to terminate and remove cleanly via deterministic cleanup (`container.remove(force=True)`), preventing container leaks and race conditions.
* **Bidirectional Volume Bind Mounts:** Target repositories are mounted into `/workspace` using Docker bind mounts, enabling the agent to write patches to disk while evaluating execution purely inside Linux.
* **Structured Token Optimization:** Raw terminal noise is filtered through an automated traceback parser, providing the LLM with structured diagnostics such as file path, line number, exception type, and assertion message. This reduces context usage and helps focus the agent on the relevant failure.

---

## 🚀 Completed Milestones

### 1. Autonomous ReAct Agent Loop — Phase 1

* Configured the Google GenAI SDK with structured tool calling.
* Implemented the following agent tools:

  * `run_tests()` — Executes the test suite and captures exit codes along with diagnostic logs.
  * `read_file(file_path)` — Inspects buggy source code.
  * `write_file(file_path, new_content)` — Writes targeted patches to the repository.
* Successfully verified:

  * Autonomous bug reproduction
  * Root-cause diagnosis
  * Code rewriting
  * Test re-execution
  * Self-termination after tests pass

### 2. Isolated Docker Sandboxing Engine — Phase 2

* Integrated the Python Docker SDK using `docker.from_env()`.
* Replaced host-level `subprocess` execution with containerized environments.
* **Base Image:** `python:3.10-slim`
* **Mount Point:** Host repository mapped to `/workspace` using a read-write bind mount.
* **Log Extraction:** Detached container execution captures unified `stdout` and `stderr`, allowing full pytest assertion tracebacks to be extracted before teardown.
* **Graceful Lifecycle Management:** Explicit container teardown inside `finally` blocks prevents resource leaks and avoids `404 Not Found` race conditions during container termination.

### 3. Multi-File Testbed & Automated Traceback Parser — Phase 3 Progress

* **Multi-File Architecture:** Scaled the target testbed from single flat files into a modular Python package layout using `src/` and `tests/`.
* **Cross-Module Imports:** Configured `PYTHONPATH=/workspace` for repository-wide module resolution.
* **Deterministic Traceback Parsing:** Implemented regex-based parsing in `traceback_parser.py`.
* The parser targets:

  * Standard pytest traceback frames such as `path/to/file.py:LINE: ErrorType`
  * Pytest short summary lines such as `FAILED file.py::function - ErrorType: message`
* Converts unstructured pytest CLI logs into normalized JSON records containing:

  * Target file paths
  * Exact line numbers
  * Exception types
  * Assertion messages

---

## 📁 Repository Structure

```text
self-healing-ci-agent/
│
├── docker_sandbox.py          # Docker sandboxing test runner & lifecycle manager
├── repair_agent.py            # Autonomous Gemini agent core & Docker tools
├── test_docker.py             # Docker Engine connectivity health check
├── traceback_parser.py        # Regex-based pytest traceback parser
│
├── sandbox_repo/              # Multi-file target workspace under test
│   ├── src/
│   │   ├── __init__.py
│   │   ├── calculator.py
│   │   └── math_helpers.py
│   │
│   └── tests/
│       ├── __init__.py
│       └── test_calculator.py
│
├── .gitignore                 # Git exclusions (.env, venv, __pycache__, etc.)
├── requirements.txt           # Project dependencies
└── README.md                  # Project documentation
```

---

## 🛠️ Prerequisites & Setup

### 1. Requirements

* Python 3.10+
* Docker Desktop
* Docker Engine running
* Google Gemini API Key

### 2. Create a Virtual Environment

```powershell
python -m venv venv
```

Activate the virtual environment in Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install google-genai docker pytest python-dotenv
```

Alternatively, if dependencies are listed in `requirements.txt`:

```powershell
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

> **Note:** Do not commit your `.env` file or API key to Git. Add `.env` to `.gitignore`.

---

## 🧪 Running the System

### 1. Verify Docker Engine Connection

```powershell
python test_docker.py
```

### 2. Run Sandboxed Test Execution

```powershell
python docker_sandbox.py
```

### 3. Test Traceback Parsing

```powershell
python traceback_parser.py
```

### 4. Run the Autonomous Repair Agent

```powershell
python repair_agent.py
```

---

## 🗺️ Roadmap

* [x] **Phase 1:** Local ReAct baseline with tool calling
* [x] **Phase 2:** Isolated Docker sandboxing with volume bind mounts
* [x] **Phase 3A/3B:** Multi-file repository testbed & automated traceback parsing
* [ ] **Phase 3C:** AST repository mapping for cross-file symbol definition discovery
* [ ] **Phase 4:** StateGraph migration using LangGraph for multi-stage self-healing
* [ ] **Phase 5:** FastAPI webhook listener integrating GitHub PR / GitHub Actions workflows

---

## 🔄 Self-Healing Workflow

The complete repair cycle follows a closed-loop process:

```text
1. Run Tests
      ↓
2. Detect Failure
      ↓
3. Parse Traceback
      ↓
4. Send Structured Diagnostics to Gemini
      ↓
5. Inspect Relevant Source Files
      ↓
6. Generate Targeted Patch
      ↓
7. Write Patch to Repository
      ↓
8. Re-run Tests Inside Docker
      ↓
   ┌───────────────┐
   │ Tests Passing?│
   └───────┬───────┘
       No  │  Yes
           │
     ┌─────┘  └──────────► Fix Verified ✓
     ↓
 Diagnose Again
     │
     └──────────────► Repeat Repair Loop
```

## 🔐 Security Model

The system is designed around the principle that **AI-generated code should be treated as untrusted code**.

Instead of executing generated patches directly on the host machine:

1. The target repository is mounted into a disposable Docker container.
2. Tests execute inside the isolated container.
3. Test output and tracebacks are collected.
4. The AI agent analyzes the failure.
5. The agent modifies the mounted repository.
6. Tests are executed again inside a fresh sandbox.
7. The container is forcibly removed after execution.

This creates a controlled **generate → execute → observe → repair → verify** feedback loop.

---

## 📌 Current Status

The project currently has a working autonomous repair baseline with:

* ✅ Gemini tool-calling agent
* ✅ Automated test execution
* ✅ Docker-based sandboxing
* ✅ Disposable container lifecycle
* ✅ Multi-file Python testbed
* ✅ Automated pytest traceback parsing
* ✅ Autonomous code patching
* ✅ Post-patch test verification

The next major milestone is **AST-based repository mapping**, allowing the agent to identify cross-file symbol definitions and dependencies before generating patches.
