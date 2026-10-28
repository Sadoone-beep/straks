"""The quiet watcher: runs in the background (pythonw), checks every 10 s
whether something is due, and then shows a card. Lives in the system tray.

Rules:
- One instance at a time (mutex).
- Full screen active (game, film)? Then we wait until it is over.
- A card never takes focus.
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import traceback
from datetime import datetime

from . import __version__, i18n, paths, store, timeparse, winutil
from .i18n import t
from .popup_gui import ReminderPopup

WATCHER_MUTEX = "Local\\StraksWatcher"
POLL_MS = 10_000
FAST_POLL_MS = 1_500


def request_overview() -> None:
    with open(paths.flag_path("overview"), "w") as f:
        f.write("1")


def request_stop() -> None:
    with open(paths.flag_path("stop"), "w") as f:
        f.write("1")


def _take_flag(name: str) -> bool:
    p = paths.flag_path(name)
    if os.path.exists(p):
        try:
            os.remove(p)
        except OSError:
            pass
        return True
    return False


def make_hidden_root() -> tk.Tk:
    """A Tk root window that never shows up.

    Measured: the very first Tk window in a process activates itself once on
    creation, whatever you set. That is why the watcher only starts once no
    full-screen window is active (wait_until_not_fullscreen); the flags below
    then keep it out of the taskbar and out of any activation."""
    root = tk.Tk()
    try:
        root.tk.call("focus", "")
    except tk.TclError:
        pass
    root.withdraw()
    winutil.set_no_activate(root)
    return root


def wait_until_not_fullscreen(max_wait: float = 6 * 3600, step: float = 5.0) -> None:
    """At start-up: if a full-screen game or film is running, we postpone creating
    the (invisible) root window until it is over."""
    import time
    waited = 0.0
    logged = False
    while waited < max_wait and winutil.is_fullscreen_foreground():
        if not logged:
            paths.log("start postponed: full screen active")
            logged = True
        time.sleep(step)
        waited += step


class Watcher:
    def __init__(self, root: tk.Tk | None = None, store_obj: store.Store | None = None):
        self.root = root or make_hidden_root()
        self.root.withdraw()
        try:
            from . import theme
            theme.apply(self.root)
        except Exception:
            pass
        self.store = store_obj or store.Store()
        self.popups: dict[str, ReminderPopup] = {}
        self.cmds: queue.Queue[str] = queue.Queue()
        self.tray = None
        self.overview = None
        self._deferred_logged = False
        self._stopping = False
        self.headless = bool(os.environ.get("STRAKS_HEADLESS"))

    # -- lifecycle ---------------------------------------------------------------
    def run(self) -> int:
        handle = winutil.acquire_mutex(WATCHER_MUTEX)
        if handle is None:
            paths.log("watcher already running, second instance exits")
            return 0
        paths.log(f"watcher started v{__version__} (pid {os.getpid()})")
        try:
            removed = self.store.prune_done()
            if removed:
                paths.log(f"{removed} old done reminders pruned")
            self._start_tray()
            self.root.after(500, self.tick)
            self.root.mainloop()
        finally:
            self._stop_tray()
            winutil.release_mutex(handle)
            paths.log("watcher stopped")
        return 0

    def stop(self) -> None:
        if self._stopping:
            return
        self._stopping = True
        try:
            self.root.after(0, self.root.quit)
        except Exception:
            pass

    # -- the clock ---------------------------------------------------------------
    def tick(self) -> None:
        delay = POLL_MS
        try:
            if _take_flag("stop"):
                self.stop()
                return
            if _take_flag("overview"):
                self.open_overview()
            while True:
                try:
                    cmd = self.cmds.get_nowait()
                except queue.Empty:
                    break
                self._handle_cmd(cmd)
            delay = self.check_due()
        except Exception:
            paths.log("error in tick:\n" + traceback.format_exc())
        finally:
            if not self._stopping:
                self.root.after(delay, self.tick)

    def check_due(self, now: datetime | None = None) -> int:
        """Show cards for what is due. Returns the next poll delay."""
        now = now or datetime.now()
        due = [r for r in self.store.due_items(now) if r.id not in self.popups]
        if not due:
            self._deferred_logged = False
            return POLL_MS
        if winutil.is_fullscreen_foreground():
            if not self._deferred_logged:
                info = winutil.foreground_info()
                paths.log(f"{len(due)} reminder(s) waiting: full screen active "
                          f"({info.get('class')} / {info.get('title', '')[:60]})")
                self._deferred_logged = True
            return FAST_POLL_MS
        self._deferred_logged = False
        for r in due:
            self.show(r)
        return POLL_MS

    def show(self, r: store.Reminder) -> ReminderPopup:
        index = len(self.popups)
        popup = ReminderPopup(self.root, r, index, self.on_action)
        self.popups[r.id] = popup
        paths.log(f"card shown: {r.name} ({r.id})")
        self._update_tray_title()
        return popup

    def _close_popup(self, rid: str) -> None:
        p = self.popups.pop(rid, None)
        if p is not None:
            try:
                p.destroy()
            except tk.TclError:
                pass
        self._update_tray_title()

    # -- buttons on the card ----------------------------------------------------------
    def on_action(self, r: store.Reminder, action: str, payload=None) -> None:
        try:
            if action == "open":
                ok = winutil.open_target(r.target)
                paths.log(f"opened: {r.target} -> {ok}")
                self.store.mark_done(r.id)
                self._close_popup(r.id)
            elif action == "reveal":
                winutil.reveal_in_explorer(r.target)
            elif action == "search":
                winutil.search_explorer(r.name, r.folder)
            elif action == "copy":
                self.root.clipboard_clear()
                self.root.clipboard_append(r.target)
                self.store.mark_done(r.id)
                self._close_popup(r.id)
            elif action == "snooze":
                when = payload if isinstance(payload, datetime) else timeparse.snooze_options()[0][1]
                self.store.snooze(r.id, when)
                paths.log(f"snoozed until {when:%Y-%m-%d %H:%M}: {r.name}")
                self._close_popup(r.id)
            elif action == "reschedule":
                self._close_popup(r.id)
                self.store.snooze(r.id, timeparse.snooze_options()[1][1])  # an hour for now, until you choose
                from .overview_gui import EditDialog
                fresh = self.store.get(r.id) or r
                EditDialog(self.root, fresh, lambda rem, due, note: self.store.update(
                    rem.id, due=store.fmt(due), note=note, status="open"))
            elif action == "done":
                self.store.mark_done(r.id)
                self._close_popup(r.id)
            else:
                self._close_popup(r.id)
        except Exception:
            paths.log("error in action:\n" + traceback.format_exc())
            self._close_popup(r.id)

    # -- overview ---------------------------------------------------------------------
    def open_overview(self) -> None:
        from .overview_gui import OverviewWindow
        if self.overview is not None:
            try:
                if self.overview.winfo_exists():
                    self.overview.deiconify()
                    self.overview.lift()
                    self.overview.focus_force()
                    return
            except tk.TclError:
                pass
        self.overview = OverviewWindow(self.root, on_close=lambda w: setattr(self, "overview", None))

    def open_add(self) -> None:
        from .add_gui import AddDialog
        AddDialog(self.root, [])

    def _handle_cmd(self, cmd) -> None:
        if isinstance(cmd, tuple) and cmd[0] == "lang":
            i18n.set_language(cmd[1])
            paths.log(f"language set to {cmd[1]}")
            self._rebuild_tray_menu()
            return
        if cmd == "overview":
            self.open_overview()
        elif cmd == "add":
            self.open_add()
        elif cmd == "quit":
            self.stop()
        elif cmd == "uninstall":
            from tkinter import messagebox
            if messagebox.askyesno(t("app.uninstall_title"),
                                   t("app.uninstall_question", dir=paths.data_dir()), parent=self.root):
                from . import install
                install.uninstall(remove_exe=True)
                paths.log("uninstalled via tray")
                self.stop()

    # -- system tray ------------------------------------------------------------------
    def _start_tray(self) -> None:
        if self.headless:
            return
        try:
            import pystray
            from PIL import Image
        except ImportError:
            paths.log("pystray/Pillow not available: no tray icon")
            return
        try:
            image = Image.open(paths.ICON) if os.path.exists(paths.ICON) else self._fallback_image()
            self.tray = pystray.Icon("straks", image, "Straks", self._tray_menu())
            threading.Thread(target=self.tray.run, name="straks-tray", daemon=True).start()
            self._update_tray_title()
        except Exception:
            paths.log("tray failed:\n" + traceback.format_exc())
            self.tray = None

    def _tray_menu(self):
        import pystray

        def lang_item(code: str, name: str):
            return pystray.MenuItem(
                name, lambda: self.cmds.put(("lang", code)),
                checked=lambda item, c=code: i18n.get_language() == c, radio=True)

        return pystray.Menu(
            pystray.MenuItem(t("tray.overview"), lambda: self.cmds.put("overview"), default=True),
            pystray.MenuItem(t("tray.new"), lambda: self.cmds.put("add")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.language"), pystray.Menu(
                *[lang_item(code, name) for code, name in i18n.NAMES.items()])),
            pystray.MenuItem(f"Straks v{__version__}", None, enabled=False),
            pystray.MenuItem(t("tray.uninstall"), lambda: self.cmds.put("uninstall")),
            pystray.MenuItem(t("tray.quit"), lambda: self.cmds.put("quit")),
        )

    def _rebuild_tray_menu(self) -> None:
        if self.tray is None:
            return
        try:
            self.tray.menu = self._tray_menu()
            self.tray.update_menu()
            self._update_tray_title()
        except Exception:
            paths.log("refreshing tray menu failed:\n" + traceback.format_exc())

    @staticmethod
    def _fallback_image():
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((4, 4, 60, 60), fill=(245, 180, 40, 255))
        d.line((32, 32, 32, 14), fill=(60, 40, 0, 255), width=5)
        d.line((32, 32, 46, 40), fill=(60, 40, 0, 255), width=5)
        return img

    def _update_tray_title(self) -> None:
        if self.tray is None:
            return
        try:
            n = len(self.store.open_items())
            self.tray.title = t("tray.n_open", n=n) if n else "Straks"
        except Exception:
            pass

    def _stop_tray(self) -> None:
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
            self.tray = None


def main(argv: list[str] | None = None) -> int:
    argv = argv or []
    if "--stop" in argv:
        request_stop()
        return 0
    try:
        probe = winutil.acquire_mutex(WATCHER_MUTEX)
        if probe is None:
            paths.log("watcher already running, second instance exits")
            return 0
        winutil.release_mutex(probe)
        wait_until_not_fullscreen()
        return Watcher().run()
    except Exception:
        paths.log("watcher crashed:\n" + traceback.format_exc())
        return 1
