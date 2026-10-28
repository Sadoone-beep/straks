"""The overview: everything still to come, and what you have already done."""

from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from . import paths, store, timeparse, winutil
from .add_gui import AddDialog
from .i18n import t
from .whenpicker import FONT, FONT_SMALL, WhenPicker


class EditDialog(tk.Toplevel):
    def __init__(self, master, reminder: store.Reminder, on_done):
        super().__init__(master)
        self.headless = bool(os.environ.get("STRAKS_HEADLESS"))
        self.withdraw()
        self.reminder = reminder
        self.on_done = on_done
        self.title(t("edit.title"))
        self.resizable(False, False)
        try:
            self.iconbitmap(paths.ICON)
        except tk.TclError:
            pass
        self.bind("<Escape>", lambda e: self.destroy())
        ttk.Label(self, text=reminder.name, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
        if reminder.kind != "text":
            ttk.Label(self, text=reminder.target, font=FONT_SMALL, foreground="#777").pack(anchor="w", padx=14)
        ttk.Label(self, text=t("add.when"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 0))
        self.picker = WhenPicker(self, initial=reminder.due_dt, on_submit=self.save)
        self.picker.pack(fill="x", padx=14, pady=(4, 0))
        row = ttk.Frame(self)
        row.pack(fill="x", padx=14, pady=(10, 0))
        ttk.Label(row, text=t("add.note"), font=FONT).pack(side="left")
        self.note_var = tk.StringVar(value=reminder.note)
        ttk.Entry(row, textvariable=self.note_var, font=FONT).pack(side="left", fill="x", expand=True, padx=(6, 0))
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=14, pady=12)
        ttk.Button(btns, text=t("add.cancel"), command=self.destroy).pack(side="right")
        ttk.Button(btns, text=t("add.save"), command=self.save, style="Primary.TButton").pack(side="right", padx=(0, 6))
        if not self.headless:
            self.update_idletasks()
            self.deiconify()
            self.lift()
            self.picker.focus_entry()

    def save(self) -> None:
        due = self.picker.get()
        if due is None:
            if not self.headless:
                messagebox.showinfo("Straks", t("add.need_when"), parent=self)
            return
        self.on_done(self.reminder, due, self.note_var.get().strip())
        self.destroy()


class OverviewWindow(tk.Toplevel):
    COLS = ("when", "what", "where", "note")

    def __init__(self, master, on_close=None):
        super().__init__(master)
        self.headless = bool(os.environ.get("STRAKS_HEADLESS"))
        self.withdraw()
        self.store = store.Store()
        self.on_close = on_close
        self.show_done = tk.BooleanVar(value=False)
        self._mtime = None
        self.title(t("overview.title"))
        self.minsize(640, 360)
        try:
            self.iconbitmap(paths.ICON)
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())
        self._build()
        self.refresh(force=True)
        self.after(3000, self._tick)
        if not self.headless:
            self.update_idletasks()
            self.geometry("820x460")
            self.deiconify()
            self.lift()
            self.focus_force()

    def _build(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=12, pady=(10, 6))
        ttk.Label(bar, text="Straks", font=("Segoe UI", 14, "bold")).pack(side="left")
        self.count_lbl = ttk.Label(bar, text="", font=FONT, foreground="#777")
        self.count_lbl.pack(side="left", padx=(10, 0), pady=(4, 0))
        ttk.Checkbutton(bar, text=t("overview.show_done"), variable=self.show_done,
                        command=lambda: self.refresh(force=True)).pack(side="right")

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=12)
        self.tree = ttk.Treeview(frame, columns=self.COLS, show="headings", selectmode="browse")
        heads = {"when": (t("overview.col_when"), 190), "what": (t("overview.col_what"), 220),
                 "where": (t("overview.col_where"), 220), "note": (t("overview.col_note"), 160)}
        for c in self.COLS:
            self.tree.heading(c, text=heads[c][0])
            self.tree.column(c, width=heads[c][1], anchor="w", stretch=(c != "when"))
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.tag_configure("due", foreground="#b26a00")
        self.tree.tag_configure("done", foreground="#999")
        self.tree.tag_configure("missing", foreground="#b00020")
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Return>", lambda e: self.edit_selected())

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=12, pady=10)
        ttk.Button(btns, text=t("overview.new"), command=self.new, style="Primary.TButton").pack(side="left")
        ttk.Button(btns, text=t("overview.open"), command=self.open_selected).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text=t("overview.edit"), command=self.edit_selected).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text=t("overview.done"), command=self.done_selected).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text=t("overview.delete"), command=self.delete_selected).pack(side="left", padx=(6, 0))
        ttk.Label(btns, text=t("overview.hint"), font=FONT_SMALL, foreground="#888").pack(side="right")

    # -- data ---------------------------------------------------------------------
    def refresh(self, force: bool = False) -> None:
        m = self.store.mtime()
        if not force and m == self._mtime:
            return
        self._mtime = m
        now = datetime.now()
        sel = self.tree.selection()
        sel_id = sel[0] if sel else None
        self.tree.delete(*self.tree.get_children())
        items = self.store.open_items()
        for r in items:
            tags = ["due"] if r.is_due(now) else []
            if not r.exists():
                tags.append("missing")
            self.tree.insert("", "end", iid=r.id, tags=tags, values=(
                timeparse.describe(r.due_dt, now), r.name,
                r.folder if r.kind != "text" else t("overview.text_kind"), r.note))
        if self.show_done.get():
            for r in self.store.done_items():
                self.tree.insert("", "end", iid=r.id, tags=["done"], values=(
                    f"{t('overview.done_prefix')} {r.done_at.replace('T', ' ')}", r.name,
                    r.folder if r.kind != "text" else t("overview.text_kind"), r.note))
        self.count_lbl.configure(text=t("overview.n_open", n=len(items)))
        if sel_id and self.tree.exists(sel_id):
            self.tree.selection_set(sel_id)

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        self.refresh()
        self.after(3000, self._tick)

    def _selected(self) -> store.Reminder | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.store.get(sel[0])

    # -- actions ------------------------------------------------------------------
    def new(self) -> None:
        AddDialog(self, [], on_close=lambda d: self.refresh(force=True))

    def open_selected(self) -> None:
        r = self._selected()
        if r is None:
            return
        if r.kind == "text":
            if r.is_url:
                winutil.open_target(r.target)
            else:
                self.clipboard_clear()
                self.clipboard_append(r.target)
        elif r.exists():
            winutil.open_target(r.target)
        else:
            winutil.search_explorer(r.name, r.folder)

    def edit_selected(self) -> None:
        r = self._selected()
        if r is None:
            return
        EditDialog(self, r, self._apply_edit)

    def _apply_edit(self, r: store.Reminder, due: datetime, note: str) -> None:
        self.store.update(r.id, due=store.fmt(due), note=note, status="open", done_at="")
        self.refresh(force=True)

    def done_selected(self) -> None:
        r = self._selected()
        if r is None:
            return
        if r.status == "done":
            self.store.reopen(r.id, r.due_dt)
        else:
            self.store.mark_done(r.id)
        self.refresh(force=True)

    def delete_selected(self) -> None:
        r = self._selected()
        if r is None:
            return
        if not self.headless and not messagebox.askyesno("Straks", t("overview.confirm_delete", name=r.name), parent=self):
            return
        self.store.delete(r.id)
        self.refresh(force=True)

    def close(self) -> None:
        if self.on_close:
            self.on_close(self)
        self.destroy()


def main(argv: list[str] | None = None) -> int:
    """Standalone: if the watcher is running, ask it to open the overview; else do it here."""
    from .watcher import WATCHER_MUTEX, request_overview
    probe = winutil.acquire_mutex(WATCHER_MUTEX)
    if probe is None:
        request_overview()
        return 0
    winutil.release_mutex(probe)
    root = tk.Tk()
    root.withdraw()
    try:
        from . import theme
        theme.apply(root)
    except Exception:
        pass
    OverviewWindow(root, on_close=lambda w: root.after(50, root.destroy))
    root.mainloop()
    return 0
