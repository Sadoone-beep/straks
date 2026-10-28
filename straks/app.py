"""Entry point of Straks.exe: one program, several roles.

  Straks.exe                 first run: install? afterwards: the overview
  Straks.exe add PATH...     the 'remind me about this' dialog (right-click menu)
  Straks.exe watch           the background watcher (autostart)
  Straks.exe overview        the overview (Start Menu)
  Straks.exe install         install without asking
  Straks.exe uninstall       uninstall (asks first; --quiet does not)
  Straks.exe stop            stop the watcher
  Straks.exe lang nl|en      pin the language
"""

from __future__ import annotations

import tkinter as tk
import traceback
from tkinter import messagebox

from . import __version__, i18n, install, paths
from .i18n import t


def _dialog(kind: str, title: str, text: str):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        root.iconbitmap(paths.ICON)
    except tk.TclError:
        pass
    fn = {"info": messagebox.showinfo, "ask": messagebox.askyesno, "error": messagebox.showerror}[kind]
    try:
        return fn(title, text, parent=root)
    finally:
        root.destroy()


def do_install(quiet: bool = False) -> int:
    r = install.install(start=True)
    paths.log(f"installed via exe v{__version__}: {r}")
    if not quiet:
        _dialog("info", "Straks", t("app.install_done"))
    return 0


def do_uninstall(quiet: bool = False) -> int:
    if not quiet and not _dialog("ask", t("app.uninstall_title"),
                                 t("app.uninstall_question", dir=paths.data_dir())):
        return 0
    r = install.uninstall(stop=True, remove_exe=True)
    paths.log(f"uninstalled via exe: {r}")
    if not quiet:
        rest = "" if r["exe_removed"] else t("app.exe_left", dir=paths.data_dir())
        _dialog("info", "Straks", t("app.uninstalled") + rest)
    return 0


def first_run() -> int:
    s = install.status()
    installed = s["files"] is not None and (not paths.FROZEN or s["exe"] is not None)
    if not installed:
        if _dialog("ask", t("app.install_title"), t("app.install_question")):
            return do_install()
    from .overview_gui import main as overview
    return overview([])


def main(argv: list[str]) -> int:
    cmd = argv[0].lower().lstrip("-") if argv else ""
    rest = argv[1:]
    try:
        if cmd == "add":
            from .add_gui import main as m
            return m(rest)
        if cmd == "watch":
            from .watcher import main as m
            return m(rest)
        if cmd == "overview":
            from .overview_gui import main as m
            return m(rest)
        if cmd == "stop":
            from .watcher import request_stop
            request_stop()
            return 0
        if cmd == "install":
            return do_install(quiet="--quiet" in rest)
        if cmd == "uninstall":
            return do_uninstall(quiet="--quiet" in rest)
        if cmd == "lang" and rest:
            i18n.set_language(rest[0])
            return 0
        if cmd == "status":
            s = install.status()
            s["language"] = i18n.get_language()
            _dialog("info", f"Straks v{__version__}", "\n".join(f"{k}: {v}" for k, v in s.items()))
            return 0
        if cmd in ("", "gui"):
            return first_run()
        _dialog("error", "Straks", t("app.unknown", cmd=cmd) + "\n\n" + (__doc__ or ""))
        return 2
    except Exception:
        paths.log(f"app '{cmd}' crashed:\n" + traceback.format_exc())
        try:
            _dialog("error", "Straks", t("app.error", log=paths.log_path()))
        except Exception:
            pass
        return 1
