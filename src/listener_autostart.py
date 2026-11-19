r"""
listener_autostart.py
---------------------
Starts listener_service.py when the owner logs on to Windows: a shortcut "Ollaa listener" in the owner's
own Startup folder (no administrator rights, no system setting). Removing the shortcut stops the autostart.

    venv\Scripts\python.exe src\listener_autostart.py --status
    venv\Scripts\python.exe src\listener_autostart.py --install     (also starts the service now)
    venv\Scripts\python.exe src\listener_autostart.py --remove      (the service already running keeps going
                                                                    until the laptop restarts or it is ended)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
PYTHONW = BASE_DIR / "venv" / "Scripts" / "pythonw.exe"
SERVICE = BASE_DIR / "src" / "listener_service.py"
SHORTCUT = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Ollaa listener.lnk"


def install() -> None:
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:OLLAA_LNK); "
        "$s.TargetPath = $env:OLLAA_PYW; $s.Arguments = '\"' + $env:OLLAA_SVC + '\"'; "
        "$s.WorkingDirectory = $env:OLLAA_DIR; $s.WindowStyle = 7; "
        "$s.Description = 'Ollaa: the live Telegram listener (listener_service.py)'; $s.Save()")
    env = dict(os.environ, OLLAA_LNK=str(SHORTCUT), OLLAA_PYW=str(PYTHONW), OLLAA_SVC=str(SERVICE), OLLAA_DIR=str(BASE_DIR))
    subprocess.run(["powershell", "-NoProfile", "-Command", script], env=env, check=True)
    print(f"Installed: {SHORTCUT}")
    subprocess.Popen([str(PYTHONW), str(SERVICE)], cwd=BASE_DIR, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    print("The listener service is started (it starts by itself at each log-on from now on).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--install", action="store_true")
    g.add_argument("--remove", action="store_true")
    g.add_argument("--status", action="store_true")
    args = ap.parse_args()
    if args.install:
        install()
    elif args.remove:
        if SHORTCUT.exists():
            SHORTCUT.unlink()
        print("Removed: the listener no longer starts with Windows.")
    else:
        print(f"Autostart: {'on' if SHORTCUT.exists() else 'off'} ({SHORTCUT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
