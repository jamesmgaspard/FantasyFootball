# run_all.py — the simple conductor
import sys, os, subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PY_EXE = sys.executable  # this will be your venv python when called via .venv\Scripts\python.exe

def run_step(name, argv):
    print(f"[RUN] {name} -> {' '.join(argv)}", flush=True)
    proc = subprocess.run(argv)
    rc = proc.returncode
    if rc == 0:
        print(f"[OK]  {name} completed", flush=True)
    else:
        print(f"[ERROR] {name} failed with errorlevel {rc}", flush=True)
    return rc

def main():
    # Always run from project root
    os.chdir(PROJECT_ROOT)
    print("[RUNNER] Starting run_all.py at project root:", PROJECT_ROOT, flush=True)

      # ---- STEP 1: fetch ESPN (already there) ----
    step1 = run_step(
        "fetch_espn",
        [PY_EXE, str(PROJECT_ROOT / "src" / "fetch_espn.py")]
    )
    if step1 != 0:
        return step1

    # ---- STEP 2: transform data (new) ----
    step2 = run_step(
        "transform_data",
        [PY_EXE, str(PROJECT_ROOT / "src" / "transform_data.py")]
    )
    if step2 != 0:
        return step2
    # ---- STEP 3: copy to Power BI drop ----
    step3 = run_step(
        "copy_to_powerbi",
        [PY_EXE, str(PROJECT_ROOT / "src" / "copy_to_powerbi.py")]
    )
    if step3 != 0:
        return step3

    # All steps passed
    return 0

if __name__ == "__main__":
    sys.exit(main())
