import os
import docker

client = docker.from_env()

def run_tests_in_sandbox() -> dict:
    """
    Executes pytest inside an isolated Docker container with sandbox_repo mounted.
    Safely captures stdout/stderr logs even on test failure before tearing down the container.
    """
    host_repo_path = os.path.abspath("sandbox_repo")
    print(f"🐳 Spinning up container sandbox for: {host_repo_path}...")

    volumes = {
        host_repo_path: {
            "bind": "/workspace",
            "mode": "rw"
        }
    }

    container = None
    try:
        # Create and run container without auto-remove so we can extract logs safely
        container = client.containers.run(
            image="python:3.10-slim",
            command='sh -c "pip install --quiet --disable-pip-version-check pytest && pytest /workspace/test_math.py"',
            volumes=volumes,
            working_dir="/workspace",
            detach=True,       # Run in background to let us manage wait and logs
            remove=False       # Don't delete immediately on exit
        )

        # Wait for the command to finish and get exit code
        result = container.wait()
        exit_code = result.get("StatusCode", 1)

        # Fetch complete stdout + stderr logs
        logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

        passed = (exit_code == 0)
        if passed:
            print("✅ Sandbox result: PASSED!")
        else:
            print("❌ Sandbox result: FAILED (Tests caught a bug!)")

        return {
            "passed": passed,
            "exit_code": exit_code,
            "output": logs
        }

    except Exception as e:
        print(f"⚠️ Sandbox execution error: {e}")
        return {
            "passed": False,
            "exit_code": -1,
            "output": str(e)
        }

    finally:
        # Guarantee container deletion regardless of pass, fail, or crash
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass

if __name__ == "__main__":
    res = run_tests_in_sandbox()
    print("\n--- Sandbox Full Diagnostic Output ---")
    print(res["output"])