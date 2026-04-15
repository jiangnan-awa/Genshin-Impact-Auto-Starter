"""
autostarter.gui.style

从根目录 gui.py 拆出的样式常量与通用 UI helper。

约束：
- 导入本模块不得创建 Tk/CTk，也不得调用 mainloop()
"""

from __future__ import annotations

from types import SimpleNamespace
try:
    import tkinter as tk
except ModuleNotFoundError:  # pragma: no cover
    # 允许在无 tkinter 环境下 import（例如 CI / headless）。
    # 注意：此时调用这些 UI helper 并不会真正渲染界面。
    class _DummyWidget:
        def __init__(self, *_args, **_kwargs):
            pass

        def pack(self, *_args, **_kwargs):
            pass

    tk = SimpleNamespace(  # type: ignore
        Canvas=_DummyWidget,
        Frame=_DummyWidget,
        Label=_DummyWidget,
        Entry=_DummyWidget,
        X="x",
        LEFT="left",
    )
from typing import Optional, Sequence, Tuple


# ─────────────────────────────────────────────
#  Color palette  (dark + amber/gold accent)
# ─────────────────────────────────────────────
BG = "#1a1a2e"  # deepest bg
SURFACE = "#16213e"  # card / panel bg
SURFACE2 = "#0f3460"  # secondary surface
ACCENT = "#e2a44a"  # gold amber
ACCENT_HV = "#f0c070"  # hover highlight
FG = "#e8e8e8"  # primary text
FG2 = "#a0a0b0"  # secondary text
BORDER = "#2a2a4a"  # subtle border
DANGER = "#e05c5c"  # red
SUCCESS = "#5cba7e"  # green


NAV_W = 200  # Sidebar width increased
WIN_W = 1920  # Initial window width
WIN_H = 1080  # Initial window height


def draw_rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs):
    """Helper to draw a rounded rectangle on a canvas."""
    points = [
        x1 + radius,
        y1,
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)


def sep(parent, pady: int = 8) -> None:
    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=pady)


def section_title(parent, text: str) -> None:
    tk.Label(parent, text=text, bg=BG, fg=ACCENT, font=("Microsoft YaHei UI", 10, "bold")).pack(
        anchor="w", pady=(12, 4)
    )


def label(parent, text: str, secondary: bool = False) -> tk.Label:
    return tk.Label(
        parent, text=text, bg=BG, fg=FG2 if secondary else FG, font=("Microsoft YaHei UI", 9 if secondary else 10)
    )


def entry(parent, textvariable: tk.Variable, show: str = "", width: int = 40) -> tk.Entry:
    # Wrapped in a frame for rounded effect simul (just border/padx)
    e = tk.Entry(
        parent,
        textvariable=textvariable,
        show=show,
        bg=SURFACE,
        fg=FG,
        insertbackground=ACCENT,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        font=("Microsoft YaHei UI", 10),
        width=width,
    )
    return e


FileTypes = Optional[Sequence[Tuple[str, str]]]


def browse_btn(parent, var: tk.StringVar, filetypes: FileTypes = None):
    """
    统一的“浏览”按钮（使用 StyledButton）。

    注意：为避免循环依赖，这里在函数内部导入 StyledButton。
    """
    if filetypes is None:
        filetypes = [("Executable Files", "*.exe;*.bat;*.cmd"), ("All Files", "*.*")]

    def _browse():
        from tkinter import filedialog

        p = filedialog.askopenfilename(title="选择文件", filetypes=filetypes)
        if p:
            var.set(p)

    from autostarter.gui.widgets.buttons import StyledButton

    return StyledButton(parent, "浏览", command=_browse, width=60)


__all__ = [
    # colors
    "BG",
    "SURFACE",
    "SURFACE2",
    "ACCENT",
    "ACCENT_HV",
    "FG",
    "FG2",
    "BORDER",
    "DANGER",
    "SUCCESS",
    # sizes
    "NAV_W",
    "WIN_W",
    "WIN_H",
    # helpers
    "draw_rounded_rect",
    "sep",
    "section_title",
    "label",
    "entry",
    "browse_btn",
]
