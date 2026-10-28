"""The 'remind me about this' dialog, opened from the right-click menu.

Explorer starts a separate process for every selected file. We coalesce
them: each process drops its path in a queue folder, the first process takes
the mutex and shows one dialog with all paths; the rest exit.
"""

from __future__ import annotations

import os
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from . import paths, store, winutil
from .i18n import t
from .whenpicker import FONT, FONT_SMALL, WhenPicker

MUTEX = "Local\\StraksAddDialog"
QUEUE_MAX_AGE = 10.0  # seconds; older queue files are orphans of a crashed dialog


def enqueue(targets: list[str]) -> None:
    qd = paths.queue_dir()
    for i, t in enumerate(targets):
        name = f"{time.time_ns()}_{os.getpid()}_{i}.txt"
        with open(os.path.join(qd, name), "w", encoding="utf-8") as f:
            f.write(t)


def drain_queue(max_age: float = QUEUE_MAX_AGE) -> list[str]:
    qd = paths.queue_dir()
    out: list[str] = []
    now = time.time()
    for name in sorted(os.listdir(qd)):
        p = os.path.join(qd, name)
        try:
            fresh = now - os.path.getmtime(p) <= max_age
            with open(p, "r", encoding="utf-8") as f:
                t = f.read().strip()
            os.remove(p)
        except OSError:
            continue
        if fresh and t and t not in out:
            out.append(t)
    return out


def _kind_icon(kind: str) -> str:
    return {"dir": "\U0001F4C1", "file": "\U0001F4C4", "text": "\U0001F4DD"}.get(kind, "•")


class AddDialog(tk.Toplevel):
    """One dialog for one or more targets. Runs as a Toplevel under a (hidden) root."""

    def __init__(self, master, targets: list[str] | None = None, poll_queue: bool = False,
                 on_close=None):
        super().__init__(master)
        self.headless = bool(os.environ.get("STRAKS_HEADLESS"))
        self.withdraw()
        self.store = store.Store()
        self.targets: list[str] = []
        self.poll_queue = poll_queue
        self.on_close = on_close
        self.saved: list[store.Reminder] = []
        self.title(t("add.title"))
        self.resizable(False, False)
        try:
            self.iconbitmap(paths.ICON)
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda e: self.cancel())
        self._build()
        for target in targets or []:
            self.add_target(target)
        if self.poll_queue:
            self.after(500, self._poll)
        if not self.headless:
            self.update_idletasks()
            self._center()
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
            self.picker.focus_entry()

    # -- layout --------------------------------------------------------------
    def _build(self) -> None:
        pad = {"padx": 14, "pady": (10, 0)}
        ttk.Label(self, text=t("add.header"), font=("Segoe UI", 13, "bold")).pack(anchor="w", **pad)

        box = ttk.Frame(self)
        box.pack(fill="x", padx=14, pady=(6, 0))
        self.listbox = tk.Listbox(box, height=3, font=FONT, activestyle="none",
                                  selectmode="browse", relief="flat", bg="#f4f4f4",
                                  highlightthickness=1, highlightbackground="#ddd")
        self.listbox.pack(side="left", fill="x", expand=True)
        side = ttk.Frame(box)
        side.pack(side="left", padx=(6, 0))
        ttk.Button(side, text=t("add.file"), width=10, command=self._pick_file).pack(fill="x")
        ttk.Button(side, text=t("add.folder"), width=10, command=self._pick_dir).pack(fill="x", pady=(3, 0))
        ttk.Button(side, text=t("add.remove"), width=10, command=self._remove_selected).pack(fill="x", pady=(3, 0))

        row = ttk.Frame(self)
        row.pack(fill="x", padx=14, pady=(6, 0))
        ttk.Label(row, text=t("add.or_text"), font=FONT).pack(side="left")
        self.text_var = tk.StringVar()
        e = ttk.Entry(row, textvariable=self.text_var, font=FONT)
        e.pack(side="left", fill="x", expand=True, padx=(6, 0))
        e.bind("<Return>", lambda ev: self._add_text())
        ttk.Button(row, text=t("add.add"), command=self._add_text).pack(side="left", padx=(6, 0))

        ttk.Separator(self).pack(fill="x", padx=14, pady=10)
        ttk.Label(self, text=t("add.when"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14)
        self.picker = WhenPicker(self, on_submit=self.save)
        self.picker.pack(fill="x", padx=14, pady=(4, 0))

        row2 = ttk.Frame(self)
        row2.pack(fill="x", padx=14, pady=(10, 0))
        ttk.Label(row2, text=t("add.note"), font=FONT).pack(side="left")
        self.note_var = tk.StringVar()
        ne = ttk.Entry(row2, textvariable=self.note_var, font=FONT)
        ne.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ne.bind("<Return>", lambda ev: self.save())

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=14, pady=12)
        ttk.Button(btns, text=t("add.cancel"), command=self.cancel).pack(side="right")
        self.save_btn = ttk.Button(btns, text=t("add.save"), command=self.save, default="active")
        self.save_btn.pack(side="right", padx=(0, 6))
        self.status = ttk.Label(btns, text="", font=FONT_SMALL, foreground="#888")
        self.status.pack(side="left")

    def _center(self) -> None:
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        l, t, r, b = winutil.work_area()
        x = l + (r - l - w) // 2
        y = t + (b - t - h) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    # -- targets ---------------------------------------------------------------
    def add_target(self, target: str) -> None:
        target = target.strip()
        if not target or target in self.targets:
            return
        kind = store.detect_kind(target)
        self.targets.append(target)
        label = (os.path.basename(target.rstrip("\\/")) or target) if kind != "text" else target
        self.listbox.insert("end", f" {_kind_icon(kind)}  {label}")
        self.listbox.configure(height=max(3, min(8, len(self.targets))))
        self._refresh_status()

    def _remove_selected(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.listbox.delete(idx)
        del self.targets[idx]
        self._refresh_status()

    def _add_text(self) -> None:
        t = self.text_var.get().strip()
        if t:
            self.add_target(t)
            self.text_var.set("")

    def _pick_file(self) -> None:
        for p in filedialog.askopenfilenames(parent=self, title=t("add.choose_file")):
            self.add_target(os.path.normpath(p))

    def _pick_dir(self) -> None:
        p = filedialog.askdirectory(parent=self, title=t("add.choose_folder"))
        if p:
            self.add_target(os.path.normpath(p))

    def _refresh_status(self) -> None:
        n = len(self.targets)
        self.status.configure(text="" if n == 0 else t("add.items", n=n))

    def _poll(self) -> None:
        if not self.winfo_exists():
            return
        for target in drain_queue():
            self.add_target(target)
        self.after(500, self._poll)

    # -- finishing ---------------------------------------------------------------
    def save(self) -> bool:
        self._add_text()
        if not self.targets:
            self._warn(t("add.need_target"))
            return False
        due = self.picker.get()
        if due is None:
            self._warn(t("add.need_when"))
            self.picker.focus_entry()
            return False
        note = self.note_var.get()
        for target in self.targets:
            self.saved.append(self.store.add(store.new_reminder(target, due, note)))
        paths.log(f"added: {len(self.targets)} x {due:%Y-%m-%d %H:%M}")
        self._finish()
        return True

    def cancel(self) -> None:
        self._finish()

    def _finish(self) -> None:
        if self.on_close:
            self.on_close(self)
        self.destroy()

    def _warn(self, msg: str) -> None:
        if self.headless:
            self.status.configure(text=msg)
            return
        messagebox.showinfo("Straks", msg, parent=self)


def main(argv: list[str]) -> int:
    """Entry from the right-click menu / CLI. Coalesces multiple selections into one dialog."""
    targets = [a for a in argv if a and not a.startswith("--")]
    handle = None
    if targets:
        enqueue(targets)
        handle = winutil.acquire_mutex(MUTEX)
        if handle is None:
            return 0  # another dialog is already open and will pick up our queue
        time.sleep(0.35)
    root = tk.Tk()
    root.withdraw()
    try:
        from . import theme
        theme.apply(root)
    except Exception:
        pass
    dlg = AddDialog(root, drain_queue() if targets else [], poll_queue=bool(targets),
                    on_close=lambda d: root.after(50, root.destroy))
    if not targets:
        dlg.text_var.set("")
    root.mainloop()
    winutil.release_mutex(handle)
    return 0
