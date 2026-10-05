import os
import re
from typing import TypedDict
from dotenv import load_dotenv
from groq import Groq
from langgraph.graph import StateGraph, END

from docker_sandbox import run_tests_in_docker
from traceback_parser import extract_failure_details
from repo_mapper import scan_repository, find_symbol_file

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# 1. State Definition
class AgentState(TypedDict):
    repo_path: str
    test_passed: bool
    error_logs: str
    iteration: int
    max_iterations: int


# 2. Node: Run Tests
def run_tests_node(state: AgentState) -> AgentState:
    print(f"\n--- [Iteration {state['iteration']}/{state['max_iterations']}] Running Tests in Docker ---")
    passed, logs = run_tests_in_docker(state["repo_path"])
    return {
        **state,
        "test_passed": passed,
        "error_logs": logs,
    }


# 3. Node: Patch Code
def patch_code_node(state: AgentState) -> AgentState:
    print("\n--- Analyzing Failure & Generating Patch ---")
    parsed = extract_failure_details(state["error_logs"])
    
    # Static Analysis: locate the target file defining the failed symbol
    repo_map = scan_repository(state["repo_path"])
    target_file = find_symbol_file(repo_map, parsed["failing_symbol"])
    
    if not target_file:
        # Fallback to the test file itself if symbol location fails
        target_file = os.path.join(state["repo_path"], parsed["test_file"])
    
    # -------------------------------------------------------------------------
    # Guard against reward hacking: never permit writes to the test suite
    # -------------------------------------------------------------------------
    normalized_path = target_file.replace("\\", "/")
    if "/tests/" in normalized_path or normalized_path.endswith("/tests") or os.path.basename(normalized_path).startswith("test_"):
        print(f"🛑 Security violation: Attempted write to test suite '{target_file}' blocked!")
        return {
            **state,
            "iteration": state["iteration"] + 1,
            "error_logs": "Security violation: Agent attempted to modify test files to pass verification.",
        }

    print(f"🎯 Target file identified: {target_file}")
    with open(target_file, "r") as f:
        file_content = f.read()

    system_prompt = (
        "You are an automated software repair engineer. Fix the failing code.\n"
        "Return ONLY the complete updated file content wrapped in a single ```python block.\n"
        "Do not include any introductory remarks, markdown explanations, or postscripts."
    )
    user_prompt = (
        f"Failing Test Name: {parsed['test_name']}\n"
        f"Exception & Trace: {parsed['error_message']}\n\n"
        f"Current File Content:\n{file_content}"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0
    )

    raw_patch = response.choices[0].message.content
    match = re.search(r"```python\n(.*?)```", raw_patch, re.DOTALL)
    cleaned_code = match.group(1) if match else raw_patch

    # Write patched code to disk
    with open(target_file, "w") as f:
        f.write(cleaned_code)
    print(f"💾 Applied patch to: {target_file}")

    return {
        **state,
        "iteration": state["iteration"] + 1,
    }


# 4. Conditional Edge Router
def check_test_status(state: AgentState) -> str:
    if state["test_passed"]:
        return "passed"
    if state["iteration"] >= state["max_iterations"]:
        return "max_iterations"
    return "failed"


# 5. Build StateGraph Workflow
workflow = StateGraph(AgentState)

workflow.add_node("run_tests", run_tests_node)
workflow.add_node("patch_code", patch_code_node)

workflow.set_entry_point("run_tests")

workflow.add_conditional_edges(
    "run_tests",
    check_test_status,
    {
        "passed": END,
        "failed": "patch_code",
        "max_iterations": END,
    },
)

workflow.add_edge("patch_code", "run_tests")

repair_graph = workflow.compile()


if __name__ == "__main__":
    target_repo = os.path.abspath("sandbox_repo")
    initial_state: AgentState = {
        "repo_path": target_repo,
        "test_passed": False,
        "error_logs": "",
        "iteration": 1,
        "max_iterations": 3,
    }
    
    final_output = repair_graph.invoke(initial_state)
    if final_output["test_passed"]:
        print("\n✅ Verification Succeeded: All tests passed inside Docker sandbox!")
    else:
        print("\n❌ Verification Failed: Maximum repair iterations reached without passing tests.")