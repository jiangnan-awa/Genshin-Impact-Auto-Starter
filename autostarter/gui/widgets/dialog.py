from __future__ import annotations

from typing import Any, Optional


def _import_customtkinter():
    import customtkinter as ctk  # type: ignore
    return ctk


def show_dialog(
    root: Any,
    *,
    title: str,
    message: str,
    level: str,
    modal: bool,
    auto_close_ms: Optional[int] = None,
) -> None:
    ctk = _import_customtkinter()
    win = ctk.CTkToplevel(master=root)
    try:
        win.title(title)
    except Exception:
        pass
    try:
        win.transient(root)
    except Exception:
        pass
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass

    try:
        sw = int(win.winfo_screenwidth())
        sh = int(win.winfo_screenheight())
    except Exception:
        sw, sh = 1200, 800
    w, h = 520, 220
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    try:
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        pass

    win.grid_columnconfigure(0, weight=1)
    win.grid_rowconfigure(1, weight=1)

    hdr = ctk.CTkLabel(master=win, text=title, font=ctk.CTkFont(size=15, weight="bold"), anchor="w")
    hdr.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")

    body = ctk.CTkTextbox(master=win, height=110)
    body.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="nsew")
    try:
        body.insert("1.0", message or "")
        body.configure(state="disabled")
    except Exception:
        pass

    btn_row = ctk.CTkFrame(master=win, fg_color="transparent")
    btn_row.grid(row=2, column=0, padx=16, pady=(0, 14), sticky="ew")
    btn_row.grid_columnconfigure(0, weight=1)

    def _close():
        try:
            win.destroy()
        except Exception:
            return

    ok_btn = ctk.CTkButton(master=btn_row, text="确定", command=_close, width=90)
    ok_btn.grid(row=0, column=1, sticky="e")

    _ = level

    if auto_close_ms is not None and hasattr(win, "after"):
        try:
            win.after(int(auto_close_ms), _close)
        except Exception:
            pass

    if modal:
        try:
            win.grab_set()
        except Exception:
            pass
        try:
            win.wait_window()
        except Exception:
            return

