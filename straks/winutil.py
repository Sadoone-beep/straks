"""Windows helpers via ctypes: full-screen detection, showing a window
without stealing focus, single-instance mutex, opening files.

Everything fails soft: on error we do the conservative thing.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import urllib.parse
from ctypes import wintypes

IS_WIN = sys.platform == "win32"

if IS_WIN:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
else:  # pragma: no cover
    user32 = kernel32 = None


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


_SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def foreground_info() -> dict:
    """Class, title and rectangle of the foreground window (for diagnostics)."""
    if not IS_WIN:
        return {}
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return {}
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, title, 512)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return {"hwnd": hwnd, "class": cls.value, "title": title.value,
            "rect": (rect.left, rect.top, rect.right, rect.bottom)}


def is_fullscreen_foreground() -> bool:
    """True if the foreground window covers the whole screen without borders:
    a game, film or presentation. A maximized ordinary window does not count."""
    if not IS_WIN:
        return False
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value in _SHELL_CLASSES:
            return False
        if user32.IsZoomed(hwnd):
            return False
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        mon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        mi = _MONITORINFO()
        mi.cbSize = ctypes.sizeof(_MONITORINFO)
        if not user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
            return False
        m = mi.rcMonitor
        return (rect.left <= m.left and rect.top <= m.top
                and rect.right >= m.right and rect.bottom >= m.bottom)
    except Exception:
        return False


def work_area() -> tuple[int, int, int, int]:
    """Desktop minus taskbar: (left, top, right, bottom)."""
    if IS_WIN:
        rect = wintypes.RECT()
        if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, 1920, 1040


def toplevel_hwnd(win) -> int:
    """The real window handle of a Tk toplevel (Tk returns the child)."""
    if not IS_WIN:
        return 0
    h = win.winfo_id()
    parent = user32.GetParent(h)
    return parent or h


def set_no_activate(win) -> bool:
    """Mark a Tk window as 'never activate' (WS_EX_NOACTIVATE): Windows then
    gives it no focus when shown and keeps it out of the taskbar."""
    if not IS_WIN:
        return False
    try:
        GWL_EXSTYLE, WS_EX_NOACTIVATE = -20, 0x08000000
        hwnd = toplevel_hwnd(win)
        if not hwnd:
            return False
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE)
        return True
    except Exception:
        return False


def show_no_activate(win, topmost: bool = True) -> bool:
    """Show a (withdrawn) Tk window without taking focus."""
    if not IS_WIN:
        win.deiconify()
        return False
    try:
        win.update_idletasks()
        hwnd = toplevel_hwnd(win)
        if not hwnd:
            win.deiconify()
            return False
        SW_SHOWNOACTIVATE = 4
        HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
        SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        user32.SetWindowPos(hwnd, HWND_TOPMOST if topmost else HWND_NOTOPMOST,
                            0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        return True
    except Exception:
        try:
            win.deiconify()
        except Exception:
            pass
        return False


def acquire_mutex(name: str):
    """Return a handle if we are the first instance, else None. Keep the handle!"""
    if not IS_WIN:
        return object()
    ERROR_ALREADY_EXISTS = 183
    kernel32.SetLastError(0)
    h = kernel32.CreateMutexW(None, False, name)
    if not h:
        return None
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(h)
        return None
    return h


def release_mutex(handle) -> None:
    if IS_WIN and handle:
        try:
            kernel32.ReleaseMutex(handle)
            kernel32.CloseHandle(handle)
        except Exception:
            pass


def open_target(path_or_url: str) -> bool:
    try:
        os.startfile(path_or_url)  # noqa: S606 - deliberate: open with the default program
        return True
    except OSError:
        return False


def reveal_in_explorer(path: str) -> None:
    path = os.path.normpath(path)
    if os.path.isdir(path):
        subprocess.Popen(["explorer.exe", path])
    else:
        subprocess.Popen(["explorer.exe", "/select,", path])


def search_explorer(name: str, folder: str | None = None) -> None:
    """Open Explorer search by file name, handy when something has moved."""
    q = urllib.parse.quote(name)
    url = f"search-ms:query={q}"
    if folder and os.path.isdir(folder):
        url += "&crumb=location:" + urllib.parse.quote(folder)
    open_target(url)


def beep() -> None:
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass
