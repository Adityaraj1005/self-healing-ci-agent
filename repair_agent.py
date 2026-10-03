import os
import docker
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
docker_client = docker.from_env()

# Tool 1: Sandboxed Test Runner
def run_tests() -> dict:
    """
    Runs pytest inside an isolated Docker container on sandbox_repo.
    Returns whether the tests passed, the exit code, and the execution logs.
    """
    host_repo_path = os.path.abspath("sandbox_repo")
    print(f"\n[Tool: run_tests] Running sandboxed pytest on {host_repo_path}...")

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
            command='sh -c "pip install --quiet --disable-pip-version-check pytest && pytest /workspace/test_math.py"',
            volumes=volumes,
            working_dir="/workspace",
            detach=True,
            remove=False
        )

        result = container.wait()
        exit_code = result.get("StatusCode", 1)
        logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

        passed = (exit_code == 0)
        print(f"  >>> Sandbox Exit Code: {exit_code} | Result: {'PASSED' if passed else 'FAILED'}")
        return {
            "passed": passed,
            "exit_code": exit_code,
            "output": logs
        }
    except Exception as e:
        return {
            "passed": False,
            "exit_code": -1,
            "output": str(e)
        }
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass

# Tool 2: Read source file
def read_file(file_path: str) -> dict:
    """Reads and returns the contents of a file inside sandbox_repo."""
    print(f"\n[Tool: read_file] Reading '{file_path}'...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Tool 3: Write corrected source file
def write_file(file_path: str, new_content: str) -> dict:
    """Overwrites a file with new content to fix a bug."""
    print(f"\n[Tool: write_file] Overwriting '{file_path}' with patch...")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return {"status": "success", "message": f"Successfully updated {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Create the agent session with the sandboxed tools
chat = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        tools=[run_tests, read_file, write_file],
        temperature=0.0,
    ),
)

prompt = (
    "You are an autonomous CI repair agent. Your objective is to ensure all tests in "
    "sandbox_repo pass. First, run the tests to find the error. If they fail, inspect the relevant "
    "file, write a fix, and rerun the tests in the sandbox. Do not stop until run_tests reports passed=True."
)

print(f"Goal: {prompt}\n")
response = chat.send_message(prompt)

print("\n--- Final Agent Summary ---")
print(response.text)