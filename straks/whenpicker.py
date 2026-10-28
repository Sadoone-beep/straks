"""The 'when' block: six quick buttons plus a free text field with live preview."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk

from . import timeparse
from .i18n import t

FONT = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 8)


class WhenPicker(ttk.Frame):
    def __init__(self, master, initial: datetime | None = None, on_submit=None):
        super().__init__(master)
        self.on_submit = on_submit
        self._value: datetime | None = None
        self.var = tk.StringVar()
        self.preview = tk.StringVar(value="")

        grid = ttk.Frame(self)
        grid.pack(fill="x")
        self.buttons = []
        for i, (label, dt) in enumerate(timeparse.quick_options()):
            b = ttk.Button(grid, text=label, command=lambda d=dt: self.set_value(d))
            b.grid(row=i // 3, column=i % 3, sticky="ew", padx=3, pady=3)
            self.buttons.append(b)
        for c in range(3):
            grid.columnconfigure(c, weight=1)

        row = ttk.Frame(self)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text=t("picker.or_type"), font=FONT).pack(side="left")
        self.entry = ttk.Entry(row, textvariable=self.var, font=FONT)
        self.entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", self._on_return)

        self.preview_lbl = ttk.Label(self, textvariable=self.preview, font=FONT, foreground="#444")
        self.preview_lbl.pack(anchor="w", pady=(4, 0))
        ttk.Label(self, text=t("picker.hint"), font=FONT_SMALL, foreground="#888").pack(anchor="w")

        if initial is not None:
            self.set_value(initial)

    # -- api ---------------------------------------------------------------
    def set_value(self, dt: datetime) -> None:
        self.var.set(dt.strftime("%d-%m-%Y %H:%M"))
        self._on_key()
        self.entry.icursor("end")

    def get(self) -> datetime | None:
        self._on_key()
        return self._value

    def focus_entry(self) -> None:
        self.entry.focus_set()

    # -- internal ----------------------------------------------------------
    def _on_key(self, _event=None) -> None:
        text = self.var.get().strip()
        if not text:
            self._value = None
            self.preview.set("")
            return
        dt = timeparse.parse_when(text)
        self._value = dt
        if dt is None:
            self.preview.set(t("picker.not_understood"))
            self.preview_lbl.configure(foreground="#b00020")
        else:
            self.preview.set("→ " + timeparse.describe(dt))
            self.preview_lbl.configure(foreground="#1b5e20" if dt > datetime.now() else "#b26a00")

    def _on_return(self, _event=None):
        if self.on_submit:
            self.on_submit()
        return "break"
