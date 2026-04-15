"""
autostarter.gui.dialogs.common

通用对话框封装（骨架）。

导入时不得创建 Tk/CTk，也不得调用 mainloop。
"""

from __future__ import annotations

from typing import Any, Optional


def show_info(master: Optional[Any], title: str, message: str) -> None:
    try:
        from tkinter import messagebox  # type: ignore

        messagebox.showinfo(title=title, message=message, parent=master)
    except Exception:
        # 在无 tkinter / headless 环境下退化为 no-op
        return


def show_error(master: Optional[Any], title: str, message: str) -> None:
    try:
        from tkinter import messagebox  # type: ignore

        messagebox.showerror(title=title, message=message, parent=master)
    except Exception:
        return


__all__ = ["show_info", "show_error"]

