import json
import os
import docker
from dotenv import load_dotenv
from groq import Groq

# Phase 3 modules: AST mapping and regex traceback parsing
from repo_mapper import build_repo_map, find_symbol_file
from traceback_parser import parse_pytest_output

load_dotenv()
groq_api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=groq_api_key)
docker_client = docker.from_env()

# --- TOOL IMPLEMENTATIONS ---

def run_tests() -> dict:
    """Runs pytest inside an isolated Docker container on sandbox_repo."""
    host_repo_path = os.path.abspath("sandbox_repo")
    print(f"\n⚙️ [Tool: run_tests] Executing sandboxed pytest on {host_repo_path}...")

    volumes = {
        host_repo_path: {
            "bind": "/workspace",
            "mode": "rw"
        }
    }

    container = None
    try:
        container = docker_client.containers.run(
            image="python:3.10-slim",
            command='sh -c "pip install --quiet --disable-pip-version-check pytest && PYTHONPATH=/workspace pytest -v /workspace/tests"',
            volumes=volumes,
            working_dir="/workspace",
            detach=True,
            remove=False
        )

        result = container.wait()
        exit_code = result.get("StatusCode", 1)
        logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

        passed = (exit_code == 0)
        print(f"   >>> Exit Code: {exit_code} | Status: {'PASSED ✅' if passed else 'FAILED ❌'}")

        parsed_failures = parse_pytest_output(logs) if not passed else []

        return {
            "passed": passed,
            "exit_code": exit_code,
            "failures": parsed_failures,
            "raw_output": logs if not parsed_failures else "See structured failures list."
        }
    except Exception as e:
        return {"passed": False, "exit_code": -1, "failures": [], "raw_output": str(e)}
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass


def locate_symbol(symbol_name: str) -> dict:
    """Uses the AST index to find which file in sandbox_repo defines a function or class."""
    print(f"\n🔍 [Tool: locate_symbol] Querying AST index for symbol '{symbol_name}'...")
    repo_path = os.path.abspath("sandbox_repo")
    repo_map = build_repo_map(repo_path)
    file_path = find_symbol_file(repo_map, symbol_name)

    if file_path:
        full_rel_path = os.path.join("sandbox_repo", file_path).replace("\\", "/")
        print(f"   >>> Found '{symbol_name}' in: {full_rel_path}")
        return {"found": True, "file_path": full_rel_path, "symbol": symbol_name}

    print(f"   >>> Symbol '{symbol_name}' not found in AST index.")
    return {"found": False, "message": f"Symbol '{symbol_name}' not found."}


def read_file(file_path: str) -> dict:
    """Reads and returns the contents of a source file."""
    # Ensure path resolves properly relative to workspace
    if not file_path.startswith("sandbox_repo") and not os.path.isabs(file_path):
        target_path = os.path.join("sandbox_repo", file_path)
        if os.path.exists(target_path):
            file_path = target_path

    print(f"\n📖 [Tool: read_file] Reading '{file_path}'...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def write_file(file_path: str, new_content: str) -> dict:
    """Overwrites a file with new content to fix a bug."""
    if not file_path.startswith("sandbox_repo") and not os.path.isabs(file_path):
        target_path = os.path.join("sandbox_repo", file_path)
        if os.path.exists(os.path.dirname(target_path)):
            file_path = target_path

    print(f"\n✏️ [Tool: write_file] Overwriting '{file_path}' with patch...")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return {"status": "success", "message": f"Successfully updated {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Map tool names to Python functions
TOOL_MAP = {
    "run_tests": run_tests,
    "locate_symbol": locate_symbol,
    "read_file": read_file,
    "write_file": write_file,
}

# Tool schemas for Groq / OpenAI format
tools = [
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Runs the test suite inside an isolated Docker container and returns failures.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "locate_symbol",
            "description": "Uses the AST index to find the file defining a function or class.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol_name": {"type": "string", "description": "The function or class name to search for."}
                },
                "required": ["symbol_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads a file from the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The relative path to the file."}
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrites a file with corrected code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The path to the file to update."},
                    "new_content": {"type": "string", "description": "The full updated file content."}
                },
                "required": ["file_path", "new_content"],
            },
        },
    },
]

# --- AGENT ORCHESTRATION LOOP ---

messages = [
    {
        "role": "system",
        "content": (
            "You are an autonomous CI repair agent working on a multi-file repository in 'sandbox_repo'.\n"
            "Your objective is to ensure all tests pass.\n\n"
            "Workflow instructions:\n"
            "1. First, call `run_tests` to inspect failure tracebacks.\n"
            "2. Read the failing test file. If the bug comes from an imported function or helper, "
            "call `locate_symbol` to find the exact file defining that function via AST instead of guessing.\n"
            "3. Read the definition file using `read_file`, diagnose the root cause, and write a targeted patch with `write_file`.\n"
            "4. Rerun `run_tests` to verify the fix in the sandbox.\n"
            "Do not finish until `run_tests` returns passed=True."
        ),
    },
    {
        "role": "user",
        "content": "Start the verification and repair process on sandbox_repo.",
    }
]

print("🤖 Autonomous Repair Agent initialized with Groq...")

for iteration in range(1, 9):
    print(f"\n--- [Iteration {iteration}] Calling Model ---")

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.0,
    )

    msg = response.choices[0].message
    messages.append(msg)

    # Check if the model requested tool calls
    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

            target_func = TOOL_MAP.get(func_name)
            if target_func:
                if func_name == "run_tests":
                    result = target_func()
                else:
                    clean_args = {k: v for k, v in func_args.items() if k}
                    result = target_func(**clean_args)
            else:
                result = {"error": f"Unknown tool: {func_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": func_name,
                "content": json.dumps(result),
            })
    else:
        print("\n🏁 Agent Response:")
        print(msg.content)
        break