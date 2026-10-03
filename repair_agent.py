import os
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Tool 1: Execute test runner
def run_tests() -> dict:
    """Runs the pytest test suite in sandbox_repo and returns stdout, stderr, and exit code."""
    print("\n[Tool: run_tests] Running pytest on sandbox_repo...")
    result = subprocess.run(
        ["pytest", "sandbox_repo/test_math.py"],
        capture_output=True,
        text=True,
    )
    passed = (result.returncode == 0)
    print(f"  >>> Result: {'PASSED' if passed else 'FAILED'}")
    return {
        "passed": passed,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

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

# Create the chat session with all 3 tools
chat = client.chats.create(
    model="gemini-3.6-flash",
    config=types.GenerateContentConfig(
        tools=[run_tests, read_file, write_file],
        temperature=0.0,
    ),
)

prompt = (
    "You are an autonomous CI repair agent. Your objective is to ensure all tests in "
    "sandbox_repo pass. First, run the tests to find the error. If they fail, inspect the relevant "
    "file, write a fix, and rerun the tests. Do not stop until run_tests reports passed=True."
)

print(f"Goal: {prompt}\n")
response = chat.send_message(prompt)

print("\n--- Final Agent Summary ---")
print(response.text)