"""A calm, consistent look for all windows."""

from __future__ import annotations

from tkinter import ttk


def apply(root) -> None:
    style = ttk.Style(root)
    for name in ("vista", "winnative", "clam"):
        if name in style.theme_names():
            try:
                style.theme_use(name)
                break
            except Exception:
                continue
    style.configure(".", font=("Segoe UI", 10))
    style.configure("TButton", padding=(8, 4))
    style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
    style.configure("Treeview", rowheight=24, font=("Segoe UI", 10))
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    try:
        root.option_add("*Font", "{Segoe UI} 10")
    except Exception:
        pass
