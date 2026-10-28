"""The reminder card that appears when a reminder is due.

Shows bottom-right, on top of everything, but does NOT take focus: you
just keep typing. Closing with the X = try again in 10 minutes.
"""

from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk

from . import paths, store, timeparse, winutil
from .i18n import t

WIDTH = 430
GAP = 10
BG = "#fffdf5"


class ReminderPopup(tk.Toplevel):
    def __init__(self, master, reminder: store.Reminder, index: int, on_action):
        super().__init__(master)
        self.headless = bool(os.environ.get("STRAKS_HEADLESS"))
        self.withdraw()
        self.reminder = reminder
        self.index = index
        self.on_action = on_action
        self.title("Straks")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        try:
            self.iconbitmap(paths.ICON)
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", lambda: self._do("close"))
        self.configure(bg=BG)
        self._build()
        self.update_idletasks()
        self._place()
        if not self.headless:
            winutil.set_no_activate(self)
            winutil.show_no_activate(self)
            winutil.beep()

    def _build(self) -> None:
        r = self.reminder
        body = tk.Frame(self, bg=BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        top = tk.Frame(body, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="⏰  " + t("popup.header"), bg=BG, fg="#8a6d00",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        when = timeparse.describe(r.due_dt)
        if r.snoozes:
            when += "  · " + t("popup.snoozed", n=r.snoozes)
        tk.Label(top, text=when, bg=BG, fg="#888", font=("Segoe UI", 8)).pack(side="right")

        icon = {"dir": "\U0001F4C1", "file": "\U0001F4C4", "text": "\U0001F4DD"}.get(r.kind, "•")
        name = r.name if r.kind != "text" else (r.target.strip()[:90] or t("popup.empty"))
        tk.Label(body, text=f"{icon}  {name}", bg=BG, fg="#111", anchor="w",
                 wraplength=WIDTH - 40, justify="left",
                 font=("Segoe UI", 12, "bold")).pack(fill="x", pady=(6, 0))
        if r.kind != "text" and r.folder:
            tk.Label(body, text=r.folder, bg=BG, fg="#777", anchor="w",
                     wraplength=WIDTH - 40, justify="left", font=("Segoe UI", 8)).pack(fill="x")
        if r.note:
            tk.Label(body, text=r.note, bg=BG, fg="#333", anchor="w",
                     wraplength=WIDTH - 40, justify="left", font=("Segoe UI", 10)).pack(fill="x", pady=(6, 0))
        self.missing = not r.exists()
        if self.missing:
            tk.Label(body, text="⚠  " + t("popup.missing"), bg=BG, fg="#b00020", anchor="w",
                     wraplength=WIDTH - 40, justify="left", font=("Segoe UI", 9)).pack(fill="x", pady=(6, 0))

        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(12, 0))
        self.buttons: dict[str, ttk.Button] = {}

        def add(key, text, side="left", primary=False):
            b = ttk.Button(btns, text=text, command=lambda: self._do(key),
                           style="Primary.TButton" if primary else "TButton")
            b.pack(side=side, padx=(0, 6) if side == "left" else (6, 0))
            self.buttons[key] = b

        if r.kind == "text":
            if r.is_url:
                add("open", t("popup.open"), primary=True)
            add("copy", t("popup.copy"), primary=not r.is_url)
        elif self.missing:
            add("search", t("popup.search"), primary=True)
        else:
            add("open", t("popup.open"), primary=True)
            add("reveal", t("popup.reveal"))
        add("done", t("popup.done"), side="right")

        # Snooze: plain buttons, no native menu (that needs focus, which we never take)
        later = tk.Frame(body, bg=BG)
        later.pack(fill="x", pady=(8, 0))
        tk.Label(later, text=t("popup.later"), bg=BG, fg="#8a6d00", font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self.snooze_buttons: list[tk.Button] = []
        for label, dt in timeparse.snooze_options():
            b = self._flat(later, label, lambda d=dt: self._do("snooze", d))
            b.pack(side="left", padx=(0, 4))
            self.snooze_buttons.append(b)
        self._flat(later, t("popup.custom"), lambda: self._do("reschedule")).pack(side="left")

    @staticmethod
    def _flat(parent, text, command) -> tk.Button:
        return tk.Button(parent, text=text, command=command, relief="flat", bg="#f0ead2",
                         activebackground="#e6dcb8", font=("Segoe UI", 9), padx=7, pady=1,
                         cursor="hand2", bd=0)

    def _place(self) -> None:
        h = self.winfo_reqheight()
        l, tp, r, b = winutil.work_area()
        x = r - WIDTH - GAP
        y = b - (h + GAP) * (self.index + 1)
        if y < tp:
            y = tp + GAP
        self.geometry(f"{WIDTH}x{h}+{x}+{y}")

    def _do(self, action: str, payload=None) -> None:
        if action == "close":
            action, payload = "snooze", datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=10)
        self.on_action(self.reminder, action, payload)
