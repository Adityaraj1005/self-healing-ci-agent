import ast
import os
from typing import Any, Dict, List


class SymbolExtractor(ast.NodeVisitor):
  """Walks through an AST syntax tree to collect all function and class definitions."""

  def __init__(self):
    self.symbols: List[Dict[str, Any]] = []

  def visit_FunctionDef(self, node: ast.FunctionDef):
    # Extract parameter names for the function
    params = [arg.arg for arg in node.args.args]
    self.symbols.append({
        "name": node.name,
        "type": "function",
        "line": node.lineno,
        "args": params,
    })
    # Continue traversing inner nodes (e.g. inner functions)
    self.generic_visit(node)

  def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
    params = [arg.arg for arg in node.args.args]
    self.symbols.append({
        "name": node.name,
        "type": "async_function",
        "line": node.lineno,
        "args": params,
    })
    self.generic_visit(node)

  def visit_ClassDef(self, node: ast.ClassDef):
    self.symbols.append({
        "name": node.name,
        "type": "class",
        "line": node.lineno,
    })
    self.generic_visit(node)


def build_repo_map(repo_dir: str) -> Dict[str, List[Dict[str, Any]]]:
  """Recursively scans a repository directory and returns an AST map of all symbols."""
  repo_map = {}
  ignored_dirs = {".git", "__pycache__", "venv", ".pytest_cache"}

  for root, dirs, files in os.walk(repo_dir):
    # Prune ignored directories in-place so os.walk doesn't enter them
    dirs[:] = [d for d in dirs if d not in ignored_dirs]

    for file in files:
      if file.endswith(".py") and not file.startswith("__"):
        full_path = os.path.join(root, file)
        # Convert path to clean relative path with forward slashes
        rel_path = os.path.relpath(full_path, repo_dir).replace("\\", "/")

        try:
          with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()

          tree = ast.parse(source, filename=rel_path)
          extractor = SymbolExtractor()
          extractor.visit(tree)

          repo_map[rel_path] = extractor.symbols
        except Exception as e:
          repo_map[rel_path] = [{"error": str(e)}]

  return repo_map


def find_symbol_file(
    repo_map: Dict[str, List[Dict[str, Any]]], symbol_name: str
) -> str | None:
  """Quick lookup helper: given a function or class name, returns the relative file path."""
  for file_path, symbols in repo_map.items():
    for item in symbols:
      if item.get("name") == symbol_name:
        return file_path
  return None


if __name__ == "__main__":
  target_dir = os.path.abspath("sandbox_repo")
  print(f"--- Scanning AST Map for: {target_dir} ---\n")

  symbol_index = build_repo_map(target_dir)

  import json

  print(json.dumps(symbol_index, indent=2))

  # Test lookup: where is 'percentage' defined?
  test_symbol = "percentage"
  found_in = find_symbol_file(symbol_index, test_symbol)
  print(f"\n🔍 Lookup test: '{test_symbol}' was found in -> {found_in}")