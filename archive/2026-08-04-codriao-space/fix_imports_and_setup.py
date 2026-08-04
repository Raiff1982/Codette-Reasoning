import os
import re

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
COMPONENT_DIR = "components"
PY_FILE_REGEX = re.compile(r"from\s+([a-zA-Z0-9_\.]+)\s+import\s+([a-zA-Z0-9_]+)")

def find_py_files(base_path):
    py_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files

def ensure_init_files():
    """Add __init__.py to every directory under components/"""
    for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, COMPONENT_DIR)):
        if '__init__.py' not in files:
            init_path = os.path.join(root, '__init__.py')
            open(init_path, 'w').close()
            print(f"[INIT ADDED] {init_path}")

def resolve_import_module(symbol):
    """Try to locate the module file matching the symbol name"""
    for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, COMPONENT_DIR)):
        for file in files:
            if file == f"{symbol}.py":
                relative = os.path.relpath(root, PROJECT_ROOT)
                return f"{relative.replace(os.sep, '.')}.{symbol}"
    return None

def fix_imports_in_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    changed = False
    new_lines = []
    for line in lines:
        match = PY_FILE_REGEX.match(line.strip())
        if match:
            module_path, symbol = match.groups()
            if module_path == symbol.lower():
                resolved = resolve_import_module(symbol)
                if resolved:
                    fixed_line = f"from {resolved} import {symbol}"
                    print(f"[FIX] {file_path} :: {line.strip()}  ->  {fixed_line}")
                    new_lines.append(fixed_line + '\n')
                    changed = True
                    continue
        new_lines.append(line)

    if changed:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        print(f"[UPDATED] {file_path}")

def run_full_fix():
    print("== Starting Full Import Fix and Init Generator ==\n")
    ensure_init_files()
    py_files = find_py_files(PROJECT_ROOT)
    for file in py_files:
        if file.endswith("__init__.py") or COMPONENT_DIR not in file:
            continue
        fix_imports_in_file(file)
    print("\n== Done ==")

if __name__ == "__main__":
    run_full_fix()