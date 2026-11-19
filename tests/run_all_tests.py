r"""
run_all_tests.py
----------------
Runs every test in tests/ (test_*.py) and the database structure check (database\export_schema.py --check).
Exits with 1 if any of them fails. The git pre-push check (.githooks/pre-push) runs it, so nothing reaches
GitHub unless everything passes; commit only after it says "ALL PASSED" (CLAUDE.md, "Git and GitHub").

Usage:
    venv\Scripts\python.exe tests\run_all_tests.py
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "venv" / "Scripts" / "python.exe"
TIMEOUT = 600   # seconds per test


def main() -> int:
    jobs = [[str(t)] for t in sorted((ROOT / "tests").glob("test_*.py"))]
    jobs.append([str(ROOT / "database" / "export_schema.py"), "--check"])
    failed = []
    for job in jobs:
        name = Path(job[0]).name + (" " + " ".join(job[1:]) if job[1:] else "")
        start = time.monotonic()
        try:
            r = subprocess.run([str(PYTHON), "-X", "utf8", *job], cwd=ROOT, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=TIMEOUT)
            ok = r.returncode == 0 and not (job[1:] == ["--check"] and "identical" not in r.stdout)
            out = r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            ok, out = False, f"took longer than {TIMEOUT} s"
        print(f"{'ok  ' if ok else 'FAIL'} {name} ({time.monotonic() - start:.0f} s)", flush=True)
        if not ok:
            failed.append(name)
            print("     " + "\n     ".join(out.strip().splitlines()[-15:]))
    print(f"\n{'ALL PASSED' if not failed else 'FAILED: ' + ', '.join(failed)} ({len(jobs)} checks)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
