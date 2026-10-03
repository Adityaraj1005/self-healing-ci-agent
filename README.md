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
    │       Gemini AI Agent       │◄─────────────┐
    │  (Reasoning & Tool Calling) │              │
    └──────────────┬──────────────┘              │
                   │                             │
       Inspect Code / Write Patch                │
                   │                             │ Test Traceback /
                   ▼                             │ Diagnostic Logs
    ┌─────────────────────────────┐              │
    │    Docker Linux Sandbox     │──────────────┘
    │    (python:3.10-slim)       │
    │   [Isolated Bind Mount]     │
    └──────────────┬──────────────┘
                   │
        All Tests Pass (Exit 0)
                   ▼
             [ Fix Verified ]
```

### Key Engineering Principles

* **No Host Execution:** Untrusted code and tests never execute directly on the host environment. All executions run inside an isolated Linux container.
* **Ephemeral Sandbox Lifecycle:** Containers are created per test run and guaranteed to terminate and remove cleanly via deterministic cleanup (`container.remove(force=True)`), preventing container leaks and race conditions.
* **Bidirectional Volume Bind Mounts:** Target repositories are mounted into `/workspace` using Docker bind mounts, enabling the agent to write patches to disk while evaluating execution purely in Linux.

---

## 🚀 What Has Been Built (Milestones 1 & 2)

### 1. Autonomous ReAct Agent Loop

* Configured Google GenAI SDK tool calling with structured tools:

  * `run_tests()`: Executes the test suite and captures exit codes along with full diagnostic logs.
  * `read_file(file_path)`: Inspects buggy source code.
  * `write_file(file_path, new_content)`: Writes targeted patches to the repository.
* Successfully verified autonomous bug reproduction, root-cause diagnosis, code rewriting, and self-termination upon passing tests.

### 2. Isolated Docker Sandboxing Engine (`docker_sandbox.py`)

* Integrated the Python Docker SDK (`docker.from_env()`).
* Replaced host-level `subprocess` execution with containerized environments:

  * **Base Image:** `python:3.10-slim`
  * **Mount Point:** Host repository path mapped to `/workspace` (`rw` mode).
  * **Log Extraction:** Detached container execution capturing unified `stdout` and `stderr` to extract full pytest assertion tracebacks before teardown.
  * **Graceful Lifecycle Management:** Explicit container teardown inside `finally` blocks to eliminate `404 Not Found` race conditions during container exit.

---

## 📁 Repository Structure

```text
self-healing-ci-agent/
├── docker_sandbox.py     # Standalone Docker sandboxing test runner & lifecycle manager
├── repair_agent.py       # Autonomous agent core utilizing Gemini model & Docker tools
├── test_docker.py        # Health-check script validating Docker Engine connectivity
├── sandbox_repo/         # Target isolated code workspace for testing
│   ├── math_ops.py       # Target source code under repair
│   └── test_math.py      # Pytest validation suite
├── .gitignore            # Git exclusion rules (.env, venv, pycache, etc.)
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation and architecture guide
```

---

## 🛠️ Prerequisites & Setup

### 1. Requirements

* Python 3.10+
* Docker Desktop (active and running)
* Google Gemini API Key

### 2. Virtual Environment Setup

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install google-genai docker pytest python-dotenv
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 🧪 Running the System

### 1. Verify Docker Engine Connection

PowerShell:

```powershell
python test_docker.py
```

### 2. Test Sandboxed Execution

PowerShell:

```powershell
python docker_sandbox.py
```

### 3. Run the Autonomous Repair Agent

PowerShell:

```powershell
python repair_agent.py
```

---

## 🗺️ Next Steps & Roadmap

* [x] **Phase 1:** Local ReAct baseline with tool calling.
* [x] **Phase 2:** Isolated Docker sandboxing with volume bind mounts.
* [ ] **Phase 3:** Multi-file repository mapping and AST-driven traceback parsing.
* [ ] **Phase 4:** StateGraph migration using LangGraph for multi-stage self-healing.
* [ ] **Phase 5:** FastAPI webhook listener integrating GitHub PR / Actions workflows.
