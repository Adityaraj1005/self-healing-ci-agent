# Autonomous Self-Healing CI Agent 🤖🛡️

An autonomous, closed-loop CI repair system that detects failing unit test suites, diagnoses multi-file dependencies, locates root causes via AST symbol discovery, generates targeted code patches, and verifies fixes inside disposable, isolated Docker execution sandboxes.

---

## 🎯 Architecture & Design Overview

Rather than relying on ungrounded code generation or running untrusted AI-generated patches directly on the host machine, this system operates under a **Verify-in-Sandbox** loop:

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
     │      AST Repo Mapper        │
     │ (Static Symbol Definition)  │
     └──────────────┬──────────────┘
                    │
                    ▼
     ┌─────────────────────────────┐
     │       AI Repair Agent       │◄─────────────┐
     │  (Reasoning & Tool Calling) │              │
     └──────────────┬──────────────┘              │
                    │                             │
      Locate / Read / Write Patch                │ Test Traceback /
                    │                             │ Diagnostic Logs
                    ▼                             │
     ┌─────────────────────────────┐              │
     │    Docker Linux Sandbox     │              │
     │    (python:3.10-slim)       │──────────────┘
     │   [Isolated Bind Mount]     │
     └──────────────┬──────────────┘
                    │
         All Tests Pass (Exit 0)
                    ▼
              [ Fix Verified ]

### Key Engineering Principles

- **No Host Execution:** Untrusted code and tests never execute on the bare host environment. All executions run inside an isolated Linux container (`python:3.10-slim`).
- **Deterministic Teardown:** Containers are created per test run and guaranteed to terminate and remove cleanly via deterministic cleanup (`container.remove(force=True)`), preventing container leaks and race conditions.
- **Bidirectional Volume Bind Mounts:** Target repositories are mounted into `/workspace` using Docker bind mounts, enabling the agent to write patches to disk while evaluating execution purely in Linux.
- **Structured Token Optimization:** Raw terminal noise is filtered through an automated traceback parser, providing the LLM with structured diagnostics such as file path, line number, exception type, and assertion message.
- **Static AST Symbol Indexing:** Traverses the repository tree using Python's `ast.NodeVisitor` without executing code, allowing fast cross-module symbol lookup without relying entirely on LLM-based code discovery.

---

## 🚀 Completed Milestones

### 1. Autonomous ReAct Agent Loop — Phase 1

- Configured baseline tool calling with structured tools:
  - `run_tests()`: Executes the test suite and captures exit codes along with full diagnostic logs.
  - `read_file(file_path)`: Inspects buggy source code.
  - `write_file(file_path, new_content)`: Writes targeted patches to the repository.
- Successfully verified autonomous bug reproduction, root-cause diagnosis, code rewriting, and self-termination upon passing tests.

### 2. Isolated Docker Sandboxing Engine — Phase 2

- Integrated the Python Docker SDK (`docker.from_env()`).
- Replaced host-level execution with containerized environments:
  - **Base Image:** `python:3.10-slim`
  - **Mount Point:** Host repository path mapped to `/workspace` using a read-write bind mount.
  - **Log Extraction:** Detached container execution captures unified `stdout` and `stderr` to extract full pytest assertion tracebacks before teardown.
  - **Graceful Lifecycle Management:** Explicit container teardown inside `finally` blocks prevents container leaks and lifecycle race conditions.

### 3. Multi-File Testbed & Diagnostic Automation — Phase 3A & 3B

- **Multi-File Architecture:** Scaled the target testbed from single flat files into a modular Python package layout (`src/` and `tests/`) supporting cross-module imports via:

    PYTHONPATH=/workspace

- **Deterministic Traceback Parsing (`traceback_parser.py`):**
  - Implemented regex patterns targeting standard pytest traceback frames such as:

        path/to/file.py:LINE: ErrorType

  - Also processes pytest summary lines such as:

        FAILED file.py::func - ErrorType: message

  - Converts unstructured pytest CLI logs into normalized JSON records containing:
    - Target file paths
    - Exact line numbers
    - Exception types
    - Assertion messages

### 4. AST Symbol Discovery & End-to-End Multi-File Repair Loop — Phase 3C & 3D

#### AST Repository Mapping — `repo_mapper.py`

- Utilizes Python's native `ast` library and `ast.NodeVisitor` to statically inspect the entire repository tree.
- Recursively maps:
  - Functions
  - Classes
  - Parameters
  - Line numbers
- Ignores non-source paths such as:
  - `.git`
  - `venv`
  - `__pycache__`
- Implements `find_symbol_file()` to provide fast lookup for imported functions across files without executing the code.

#### Autonomous Multi-File Tool Orchestration — `repair_agent.py`

- Integrated high-speed LLM inference using the Groq SDK (`openai/gpt-oss-120b`).
- Implemented defensive tool-argument unpacking to eliminate empty argument parsing bugs.
- Complete autonomous cycle verified:

    1. Runs the containerized test suite and captures assertion failures.
    2. Inspects the failing test case and identifies missing or faulty imported symbols.
    3. Invokes `locate_symbol` to discover the exact definition file across packages.
    4. Reads the upstream implementation.
    5. Authors and writes the correct patch.
    6. Re-runs the tests inside Docker.
    7. Terminates automatically once all tests pass.

---

## 📁 Repository Structure

    self-healing-ci-agent/
    │
    ├── docker_sandbox.py
    │   # Standalone Docker sandboxing test runner & lifecycle manager
    │
    ├── repo_mapper.py
    │   # Static AST syntax tree scanner and symbol locator
    │
    ├── repair_agent.py
    │   # Autonomous multi-file agent loop with tool dispatching
    │
    ├── test_docker.py
    │   # Health-check script validating Docker Engine connectivity
    │
    ├── traceback_parser.py
    │   # Regex-based pytest traceback parser and log normalizer
    │
    ├── sandbox_repo/
    │   ├── src/
    │   │   ├── __init__.py
    │   │   ├── calculator.py
    │   │   └── math_helpers.py
    │   │
    │   └── tests/
    │       ├── __init__.py
    │       └── test_calculator.py
    │
    ├── .gitignore
    │   # Git exclusion rules (.env, venv, pycache, etc.)
    │
    ├── requirements.txt
    │   # Project dependencies
    │
    └── README.md
        # Project documentation and architecture guide

---

## 🛠️ Prerequisites & Setup

### 1. Requirements

- Python 3.10+
- Docker Desktop (active and running)
- Docker Engine
- Groq API Key

### 2. Virtual Environment Setup

Create a virtual environment:

    python -m venv venv

Activate it in Windows PowerShell:

    .\venv\Scripts\Activate.ps1

Install dependencies:

    pip install groq docker pytest python-dotenv

### 3. Environment Configuration

Create a `.env` file in the project root:

    GROQ_API_KEY=gsk_your_groq_api_key_here

> **Security:** Never commit your `.env` file or expose your API key publicly.

---

## 🧪 Running the Verification Tools

### 1. Verify Docker Engine Connection

    python test_docker.py

This verifies that the Python Docker SDK can communicate with the local Docker Engine.

### 2. Verify AST Symbol Discovery

    python repo_mapper.py

This scans the repository using Python's AST module and verifies cross-file symbol discovery.

### 3. Test Traceback Parsing

    python traceback_parser.py

This validates the traceback parser against pytest diagnostic output.

### 4. Run the Autonomous Multi-File Repair Agent

    python repair_agent.py

The agent autonomously:

    Run Tests
        ↓
    Parse Failure
        ↓
    Locate Relevant Symbol
        ↓
    Read Source
        ↓
    Generate Patch
        ↓
    Write Patch
        ↓
    Run Tests Again
        ↓
    Verify Fix

---

## 🔐 Security & Isolation Model

The system is designed around a **Verify-in-Sandbox** principle.

Instead of allowing generated patches or test suites to execute directly on the host machine, execution occurs inside a disposable Docker container:

    Host Machine
         │
         │ Bind Mount
         ▼
    ┌─────────────────────┐
    │   Docker Sandbox    │
    │                     │
    │  /workspace         │
    │       │             │
    │       ▼             │
    │  Source Code        │
    │       │             │
    │       ▼             │
    │  Pytest Execution   │
    └─────────┬───────────┘
              │
              ▼
        Test Results
              │
              ▼
         Repair Agent

This provides a controlled execution environment where generated patches can be tested without directly executing them on the host environment.

---

## 🧠 Why AST-Based Symbol Discovery?

A conventional LLM-based repair agent may need to search through an entire repository to determine where a referenced function or class is defined.

This project instead performs static symbol discovery using Python's AST:

    LLM
     │
     │ "Where is calculate_tax() defined?"
     ▼
    AST Repository Mapper
     │
     ├── calculator.py
     ├── math_helpers.py
     └── utils.py
              │
              ▼
       Exact Symbol Location

Because the repository is parsed statically, the system can locate function and class definitions without executing the source code.

This reduces unnecessary LLM tool calls and helps ground the repair agent in the actual repository structure.

---

## ⚡ Diagnostic Optimization

Raw pytest output can contain a large amount of irrelevant terminal information.

Instead of sending the entire output directly to the LLM:

    Raw pytest output
           ↓
    Traceback Parser
           ↓
    Structured Diagnostic
           ↓
           LLM

Example normalized diagnostic:

    {
      "file": "src/calculator.py",
      "line": 18,
      "error_type": "AssertionError",
      "message": "Expected 15 but got 10"
    }

This provides the agent with focused failure information while reducing unnecessary context consumption.

---

## 🔄 End-to-End Workflow

    ┌───────────────────────────┐
    │     Failing Test Suite    │
    └─────────────┬─────────────┘
                  │
                  ▼
    ┌───────────────────────────┐
    │    Docker Test Runner     │
    └─────────────┬─────────────┘
                  │
                  ▼
    ┌───────────────────────────┐
    │   Traceback Extraction    │
    └─────────────┬─────────────┘
                  │
                  ▼
    ┌───────────────────────────┐
    │    AST Symbol Discovery   │
    └─────────────┬─────────────┘
                  │
                  ▼
    ┌───────────────────────────┐
    │      AI Repair Agent      │
    │   Reason + Tool Calling   │
    └─────────────┬─────────────┘
                  │
                  ▼
    ┌───────────────────────────┐
    │      Targeted Patch       │
    └─────────────┬─────────────┘
                  │
                  ▼
    ┌───────────────────────────┐
    │   Re-run Tests in Docker  │
    └─────────────┬─────────────┘
                  │
            ┌─────┴─────┐
            │           │
          Fail         Pass
            │           │
            │           ▼
            │    ┌──────────────┐
            │    │ Fix Verified │
            │    └──────────────┘
            │
            └──────────► Repair Loop

---

## 🗺️ Roadmap

- [x] Phase 1: Local ReAct baseline with tool calling.
- [x] Phase 2: Isolated Docker sandboxing with volume bind mounts.
- [x] Phase 3A/3B: Multi-file repository testbed & automated traceback parsing.
- [x] Phase 3C/3D: AST repository mapping & autonomous multi-file repair loop.
- [ ] Phase 4: StateGraph migration using LangGraph for multi-stage self-healing.
- [ ] Phase 5: FastAPI webhook listener integrating GitHub PR / GitHub Actions workflows.

---

## 🎯 Future Vision

The long-term goal is to evolve this prototype into a production-style **self-healing CI system** capable of:

    GitHub Push / Pull Request
                │
                ▼
           CI Pipeline
                │
                ▼
          Tests Fail ❌
                │
                ▼
       Self-Healing Agent
                │
         ┌──────┴──────┐
         │             │
      Diagnose       Locate
         │             │
         └──────┬──────┘
                ▼
          Generate Patch
                │
                ▼
        Docker Verification
                │
          ┌─────┴─────┐
          │           │
        Failed      Passed
          │           │
          ▼           ▼
        Retry       Create PR
                      │
                      ▼
                Human Review

The system aims to move CI repair from **"detect and report"** toward **"detect, diagnose, repair, verify, and propose"** while keeping code execution isolated and verification deterministic.