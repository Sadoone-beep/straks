"""Install / uninstall: right-click menu, autostart and a Start Menu shortcut.
Everything under HKEY_CURRENT_USER, so no admin rights.

Two flavours of the same thing:
- from source:  pythonw.exe straks_add.pyw "%1"
- as exe:       %LOCALAPPDATA%\\Straks\\Straks.exe add "%1"
The exe first copies itself to that fixed location, so the registry never
points into a Downloads folder.

All paths are parameters so tests can work in their own registry branch.
"""

from __future__ import annotations

import filecmp
import os
import shutil
import subprocess
import sys
import time
import winreg

from . import APP_NAME, paths
from .i18n import t

VERB = "Straks"


def menu_text() -> str:
    return t("menu.remind")
CLASSES = r"Software\Classes"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Straks"

ROOT = paths.ROOT
LAUNCHERS = {
    "add": os.path.join(ROOT, "straks_add.pyw"),
    "watch": os.path.join(ROOT, "straks_watch.pyw"),
    "overview": os.path.join(ROOT, "straks_overview.pyw"),
}


def _q(p: str) -> str:
    return f'"{p}"'


def _frozen_exe() -> str | None:
    return paths.installed_exe() if paths.FROZEN else None


def launcher(sub: str, exe: str | None = None) -> list[str]:
    """Program + arguments for a subcommand, as exe or as pythonw + .pyw."""
    exe = exe if exe is not None else _frozen_exe()
    if exe:
        return [exe, sub]
    return [paths.pythonw(), LAUNCHERS[sub]]


def _cmdline(parts: list[str], tail: str = "") -> str:
    s = " ".join(_q(p) for p in parts)
    return f"{s} {tail}" if tail else s


def add_command(exe: str | None = None) -> str:
    return _cmdline(launcher("add", exe), '"%1"')


def watch_command(exe: str | None = None) -> str:
    return _cmdline(launcher("watch", exe))


def icon_value(exe: str | None = None) -> str:
    exe = exe if exe is not None else _frozen_exe()
    return f"{exe},0" if exe else paths.ICON


# -- registry ----------------------------------------------------------------
def _delete_tree(root, path: str) -> None:
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as k:
            subs = []
            i = 0
            while True:
                try:
                    subs.append(winreg.EnumKey(k, i))
                    i += 1
                except OSError:
                    break
        for s in subs:
            _delete_tree(root, path + "\\" + s)
        winreg.DeleteKey(root, path)
    except FileNotFoundError:
        pass


def _write_verb(root, base: str, exe: str | None) -> None:
    key_path = f"{base}\\shell\\{VERB}"
    with winreg.CreateKey(root, key_path) as k:
        winreg.SetValueEx(k, None, 0, winreg.REG_SZ, menu_text())
        winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon_value(exe))
        winreg.SetValueEx(k, "MultiSelectModel", 0, winreg.REG_SZ, "Document")
    with winreg.CreateKey(root, key_path + "\\command") as k:
        winreg.SetValueEx(k, None, 0, winreg.REG_SZ, add_command(exe))


def _read_verb(root, base: str) -> dict | None:
    try:
        with winreg.OpenKey(root, f"{base}\\shell\\{VERB}") as k:
            text = winreg.QueryValueEx(k, None)[0]
        with winreg.OpenKey(root, f"{base}\\shell\\{VERB}\\command") as k:
            cmd = winreg.QueryValueEx(k, None)[0]
        return {"text": text, "command": cmd}
    except FileNotFoundError:
        return None


# -- shortcut -------------------------------------------------------------------
def shortcut_path() -> str:
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", f"{APP_NAME}.lnk")


def _make_shortcut(path: str, exe: str | None) -> bool:
    parts = launcher("overview", exe)
    args = " ".join(_q(p) for p in parts[1:])
    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{path}'); "
        f"$s.TargetPath = '{parts[0]}'; "
        f"$s.Arguments = '{args}'; "
        f"$s.WorkingDirectory = '{os.path.dirname(parts[0])}'; "
        f"$s.IconLocation = '{icon_value(exe)}'; "
        f"$s.Description = '{t('shortcut.description')}'; "
        "$s.Save()"
    )
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode == 0 and os.path.exists(path)
    except (OSError, subprocess.SubprocessError):
        return False


# -- the watcher as a process ---------------------------------------------------------
def spawn_watcher(exe: str | None = None) -> bool:
    from . import winutil
    from .watcher import WATCHER_MUTEX
    probe = winutil.acquire_mutex(WATCHER_MUTEX)
    if probe is None:
        return False  # already running
    winutil.release_mutex(probe)
    parts = launcher("watch", exe)
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(parts, creationflags=flags, close_fds=True, cwd=os.path.dirname(parts[0]))
    return True


def stop_watcher_and_wait(timeout: float = 20.0) -> bool:
    """Ask the watcher to stop and wait until the mutex is free."""
    from . import winutil
    from .watcher import WATCHER_MUTEX, request_stop
    probe = winutil.acquire_mutex(WATCHER_MUTEX)
    if probe is not None:
        winutil.release_mutex(probe)
        return True  # was not running
    request_stop()
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.5)
        probe = winutil.acquire_mutex(WATCHER_MUTEX)
        if probe is not None:
            winutil.release_mutex(probe)
            return True
    return False


def stage_exe() -> str:
    """Copy the running exe to its fixed location (if it is not there already)."""
    src = os.path.abspath(sys.executable)
    dst = paths.installed_exe()
    if os.path.normcase(src) == os.path.normcase(dst):
        return dst
    if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
        return dst
    stop_watcher_and_wait()
    last: Exception | None = None
    for _ in range(10):
        try:
            shutil.copy2(src, dst)
            return dst
        except PermissionError as e:  # the old exe is still busy for a moment
            last = e
            time.sleep(0.5)
    raise last or PermissionError(dst)


# -- the three commands --------------------------------------------------------------
def install(root=winreg.HKEY_CURRENT_USER, classes: str = CLASSES, run_key: str = RUN_KEY,
            shortcut: str | None = None, autostart: bool = True, exe: str | None = None,
            start: bool = False) -> dict:
    if exe is None and paths.FROZEN:
        exe = stage_exe()
    _write_verb(root, f"{classes}\\*", exe)
    _write_verb(root, f"{classes}\\Directory", exe)
    result = {"context_menu": True, "autostart": False, "shortcut": False, "started": False, "exe": exe}
    if autostart:
        with winreg.CreateKey(root, run_key) as k:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, watch_command(exe))
        result["autostart"] = True
    if shortcut is None:
        shortcut = shortcut_path()
    if shortcut:
        result["shortcut"] = _make_shortcut(shortcut, exe)
    if start:
        stop_watcher_and_wait()  # an old (source or previous-version) watcher makes way
        result["started"] = spawn_watcher(exe)
    return result


def uninstall(root=winreg.HKEY_CURRENT_USER, classes: str = CLASSES, run_key: str = RUN_KEY,
              shortcut: str | None = None, stop: bool = False, remove_exe: bool = False) -> dict:
    if stop:
        stop_watcher_and_wait()
    _delete_tree(root, f"{classes}\\*\\shell\\{VERB}")
    _delete_tree(root, f"{classes}\\Directory\\shell\\{VERB}")
    try:
        with winreg.OpenKey(root, run_key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, RUN_NAME)
    except FileNotFoundError:
        pass
    if shortcut is None:
        shortcut = shortcut_path()
    if shortcut and os.path.exists(shortcut):
        try:
            os.remove(shortcut)
        except OSError:
            pass
    result = {"exe_removed": False}
    if remove_exe:
        exe = paths.installed_exe()
        if os.path.exists(exe):
            try:
                os.remove(exe)
                result["exe_removed"] = True
            except OSError:
                pass  # still running (it is us); stays behind, harmless
    return result


def status(root=winreg.HKEY_CURRENT_USER, classes: str = CLASSES, run_key: str = RUN_KEY) -> dict:
    out = {
        "files": _read_verb(root, f"{classes}\\*"),
        "dirs": _read_verb(root, f"{classes}\\Directory"),
        "autostart": None,
        "shortcut": os.path.exists(shortcut_path()),
        "data_dir": paths.data_dir(),
        "exe": paths.installed_exe() if os.path.exists(paths.installed_exe()) else None,
    }
    try:
        with winreg.OpenKey(root, run_key) as k:
            out["autostart"] = winreg.QueryValueEx(k, RUN_NAME)[0]
    except FileNotFoundError:
        pass
    return out


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "install":
        r = install(start=True)
        print("Context menu:", "ok" if r["context_menu"] else "failed")
        print("Autostart:   ", "ok" if r["autostart"] else "skipped")
        print("Start Menu:  ", "ok" if r["shortcut"] else "failed")
        print("Watcher:     ", "started" if r["started"] else "not started")
        return 0
    if cmd == "uninstall":
        uninstall(stop=True, remove_exe=True)
        print("Removed: context menu, autostart, Start Menu shortcut.")
        print("Your reminders are still in", paths.data_dir())
        return 0
    s = status()
    for k, v in s.items():
        print(f"{k:12} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
