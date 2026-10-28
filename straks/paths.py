"""Locations of data, log and helper files.

Everything lives under %LOCALAPPDATA%\\Straks unless STRAKS_DATA_DIR is set
(tests use that to point at a temporary folder).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    # PyInstaller: the source folder is the exe's folder; bundled files live in _MEIPASS
    BUNDLE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    ROOT = os.path.dirname(os.path.abspath(sys.executable))
    ASSETS = os.path.join(BUNDLE, "assets")
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS = os.path.join(ROOT, "assets")
ICON = os.path.join(ASSETS, "straks.ico")
EXE_NAME = "Straks.exe"


def installed_exe() -> str:
    """Where the exe lives after installation (and where the registry starts it from)."""
    return os.path.join(data_dir(), EXE_NAME)


def data_dir() -> str:
    base = os.environ.get("STRAKS_DATA_DIR")
    if not base:
        local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        base = os.path.join(local, "Straks")
    os.makedirs(base, exist_ok=True)
    return base


def store_path() -> str:
    return os.path.join(data_dir(), "reminders.json")


def queue_dir() -> str:
    p = os.path.join(data_dir(), "queue")
    os.makedirs(p, exist_ok=True)
    return p


def flag_path(name: str) -> str:
    return os.path.join(data_dir(), f"{name}.flag")


def log_path() -> str:
    return os.path.join(data_dir(), "straks.log")


def log(msg: str) -> None:
    """Small log with rotation, so pythonw processes never die silently."""
    try:
        p = log_path()
        if os.path.exists(p) and os.path.getsize(p) > 512 * 1024:
            old = p + ".1"
            if os.path.exists(old):
                os.remove(old)
            os.replace(p, old)
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


def pythonw() -> str:
    """Path to pythonw.exe of the currently running interpreter."""
    for base in (sys.base_prefix, sys.prefix, os.path.dirname(sys.executable)):
        cand = os.path.join(base, "pythonw.exe")
        if os.path.exists(cand):
            return cand
    return sys.executable
