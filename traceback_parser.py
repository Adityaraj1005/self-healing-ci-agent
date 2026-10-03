import re
from typing import Any, Dict, List


def parse_pytest_output(pytest_logs: str) -> List[Dict[str, Any]]:
  """Parses raw pytest stdout/stderr output into structured error records.

  Returns a list of parsed failures with file path, line number, and error
  details.
  """
  failures = []

  # Pattern 1: Matches standard traceback location -> path/to/file.py:LINE: ErrorType
  location_pattern = re.compile(
      r"([a-zA-Z0-9_\-\./\\]+\.py):(\d+): (\w+)(?:: (.+))?"
  )

  # Pattern 2: Matches pytest short summary lines -> FAILED file.py::test_name - ErrorType: message
  summary_pattern = re.compile(
      r"FAILED ([a-zA-Z0-9_\-\./\\]+\.py)::(\w+) - (?:(\w+):? ?(.*))?"
  )

  for line in pytest_logs.splitlines():
    line = line.strip()

    # Try matching file location with line number
    loc_match = location_pattern.search(line)
    if loc_match:
      file_path, line_no, error_type, message = loc_match.groups()
      failures.append({
          "file": file_path.replace("\\", "/"),
          "line": int(line_no),
          "error_type": error_type,
          "message": message.strip() if message else "",
          "source": "traceback_line",
      })
      continue

    # Try matching summary failure lines
    sum_match = summary_pattern.search(line)
    if sum_match:
      file_path, test_func, error_type, message = sum_match.groups()
      failures.append({
          "file": file_path.replace("\\", "/"),
          "test_function": test_func,
          "error_type": error_type or "UnknownError",
          "message": message.strip() if message else "",
          "source": "summary_line",
      })

  return failures


if __name__ == "__main__":
  # Sample real log from our previous docker_sandbox run
  sample_log = """
    tests/test_calculator.py:9: AssertionError
    =========================== short test summary info ============================
    FAILED tests/test_calculator.py::test_calculate_discounted_total - AssertionError: Expected 80.0, but got -100.0
    =========================== 1 failed in 0.62s ===========================
    """

  parsed = parse_pytest_output(sample_log)
  print(f"Detected {len(parsed)} failure markers:")
  for item in parsed:
    print(" ", item)