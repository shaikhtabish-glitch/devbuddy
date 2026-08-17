#!/usr/bin/env python3
"""
Run a DevBuddy script inside the project's virtual environment (no `make` needed).

    python run.py                    # runs src/verification.py
    python run.py src/other.py       # runs a specific script

Uses uv if available, otherwise the .venv created by install.py.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
script = sys.argv[1] if len(sys.argv) > 1 else "src/verification.py"


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


if shutil.which("uv"):
    sys.exit(subprocess.call(["uv", "run", "python", script], cwd=HERE))

py = venv_python()
if not py.exists():
    print("No virtual environment found. Run first:  python install.py")
    sys.exit(1)
sys.exit(subprocess.call([str(py), script], cwd=HERE))
