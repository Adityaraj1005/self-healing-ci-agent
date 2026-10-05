import json
import os
from typing import TypedDict
import docker
from dotenv import load_dotenv
from groq import Groq
from langgraph.graph import END, StateGraph

from repo_mapper import build_repo_map, find_symbol_file
from traceback_parser import parse_pytest_output

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
docker_client = docker.from_env()

class AgentState(TypedDict):
    repo_path: str
    test_passed: bool
    error_logs: str
    iteration: int
    max_iterations: int

def run_tests_node(state: AgentState) -> dict:
    host_repo_path = os.path.abspath(state["repo_path"])
    print(f"\n🐳 [Node: run_tests] Running tests inside Docker on {host_repo_path}...")

    volumes = {host_repo_path: {"bind": "/workspace", "mode": "rw"}}
    container = None
    try:
        container = docker_client.containers.run(
            image="python:3.10-slim",
            command='sh -c "pip install --quiet --disable-pip-version-check pytest && PYTHONPATH=/workspace pytest -v /workspace/tests"',
            volumes=volumes,
            working_dir="/workspace",
            detach=True,
            remove=False,
        )
        result = container.wait()
        exit_code = result.get("StatusCode", 1)
        logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

        passed = exit_code == 0
        print(f"   >>> Exit Code: {exit_code} | Status: {'PASSED ✅' if passed else 'FAILED ❌'}")
        return {"test_passed": passed, "error_logs": logs}
    except Exception as e:
        return {"test_passed": False, "error_logs": str(e)}
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass

def patch_code_node(state: AgentState) -> dict:
    current_iter = state["iteration"] + 1
    print(f"\n🧠 [Node: patch_code] Generating patch (Attempt {current_iter})...")

    repo_path = state["repo_path"]
    repo_map = build_repo_map(repo_path)
    symbol_target = "percentage"
    found_file = find_symbol_file(repo_map, symbol_target)

    target_file_path = os.path.join(repo_path, found_file or "src/math_helpers.py").replace("\\", "/")
    print(f"   >>> AST Located Symbol '{symbol_target}' in: {target_file_path}")

    with open(target_file_path, "r", encoding="utf-8") as f:
        current_content = f.read()

    prompt = (
        f"You are a Python bug-fixing engine.\n"
        f"Failing test log:\n{state['error_logs']}\n\n"
        f"Current code of {target_file_path}:\n{current_content}\n\n"
        f"Provide ONLY the complete fixed Python code for {target_file_path}.\n"
        f"Do not include backticks, markdown, or explanations. Return pure raw python code."
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    patched_code = response.choices[0].message.content.strip()
    if patched_code.startswith("```"):
        lines = patched_code.split("\n")
        patched_code = "\n".join(lines[1:-1])

    with open(target_file_path, "w", encoding="utf-8") as f:
        f.write(patched_code)
    print(f"   >>> Successfully applied patch to {target_file_path} ✏️")

    return {"iteration": current_iter}

def check_test_status(state: AgentState) -> str:
    if state["test_passed"]:
        print("\n🎉 [Router] Tests passed! Navigating to END.")
        return "end"

    if state["iteration"] >= state["max_iterations"]:
        print(f"\n🛑 [Router] Reached max iterations ({state['max_iterations']}). Navigating to END.")
        return "end"

    print("\n🔁 [Router] Tests failed. Navigating to patch_code.")
    return "patch_code"

workflow = StateGraph(AgentState)
workflow.add_node("run_tests", run_tests_node)
workflow.add_node("patch_code", patch_code_node)
workflow.set_entry_point("run_tests")
workflow.add_conditional_edges("run_tests", check_test_status, {"end": END, "patch_code": "patch_code"})
workflow.add_edge("patch_code", "run_tests")

app = workflow.compile()

if __name__ == "__main__":
    initial_state = {
        "repo_path": "sandbox_repo",
        "test_passed": False,
        "error_logs": "",
        "iteration": 0,
        "max_iterations": 3,
    }

    print("🚀 Starting LangGraph Autonomous Repair Workflow...")
    final_output = app.invoke(initial_state)

    print("\n🏁 Workflow Execution Complete!")
    print(f"Final Test Status: {'PASSED ✅' if final_output['test_passed'] else 'FAILED ❌'}")
    print(f"Total Iterations: {final_output['iteration']}")