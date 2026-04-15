"""
autostarter.gui.widgets.buttons

从根目录 gui.py 拆出的按钮控件：
- StyledButton
- NavButton

约束：导入时不得创建 Tk，也不得调用 mainloop。
"""

from __future__ import annotations

# 注意：tests.test_gui_imports 允许在“没有 tkinter”的环境下导入本模块。
# 因此这里需要在缺少 tk.Canvas 时提供可导入的占位基类。
try:
    import tkinter as tk  # type: ignore
    _CanvasBase = tk.Canvas  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - 仅用于无 tkinter 环境的导入兜底
    tk = None  # type: ignore

    class _CanvasBase:  # noqa: D401
        """tk.Canvas 占位基类（仅用于 import 通过）。"""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("tkinter 不可用，无法创建 GUI 控件")

from autostarter.gui.style import (
    ACCENT,
    ACCENT_HV,
    BG,
    BORDER,
    DANGER,
    FG,
    FG2,
    SURFACE,
    SURFACE2,
    draw_rounded_rect,
)


class StyledButton(_CanvasBase):
    """Modern rounded button."""

    def __init__(
        self,
        master,
        text: str,
        command=None,
        primary: bool = False,
        danger: bool = False,
        width: int = 80,
        height: int = 34,
        **kw,
    ):
        bg = kw.pop("bg", BG)
        self._width = width
        super().__init__(
            master, bg=bg, width=width, height=height, highlightthickness=0, cursor="hand2", **kw
        )
        self._main_color = ACCENT if primary else (DANGER if danger else SURFACE2)
        self._hv_color = ACCENT_HV if primary else (DANGER + "aa" if danger else "#2a4a7a")
        self._fg = "#111" if primary else FG
        self._cmd = command
        self._text = text
        self._width = width

        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._draw(True))
        self.bind("<Leave>", lambda e: self._draw(False))
        self.bind("<Button-1>", lambda e: self._on_click())

    def _draw(self, hover: bool = False):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10:
            return
        color = self._hv_color if hover else self._main_color
        draw_rounded_rect(self, 0, 0, w, h, 16, fill=color)
        self.create_text(w / 2, h / 2, text=self._text, fill=self._fg, font=("Microsoft YaHei UI", 9, "bold"))

    def _on_click(self):
        if self._cmd:
            self._cmd()


class NavButton(_CanvasBase):
    """Sidebar navigation button with rounded highlight."""

    def __init__(self, master, text: str, command=None, **kw):
        super().__init__(master, bg=SURFACE, height=48, highlightthickness=0, cursor="hand2", **kw)
        self._cmd = command
        self._text = text
        self._active = False
        self.bind("<Enter>", lambda e: self._draw(hover=True))
        self.bind("<Leave>", lambda e: self._draw(hover=False))
        self.bind("<Button-1>", lambda e: self._on_click())
        self.bind("<Configure>", lambda e: self._draw())

    def set_active(self, active: bool):
        self._active = active
        self._draw()

    def _draw(self, hover: bool = False):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10:
            return

        if self._active:
            # Rounded highlight 'pill'
            draw_rounded_rect(self, 8, 4, w - 8, h - 4, 18, fill=SURFACE2)
            fg = ACCENT
            font = ("Microsoft YaHei UI", 10, "bold")
        elif hover:
            draw_rounded_rect(self, 8, 4, w - 8, h - 4, 18, fill=BORDER)
            fg = FG
            font = ("Microsoft YaHei UI", 10)
        else:
            fg = FG2
            font = ("Microsoft YaHei UI", 10)

        self.create_text(24, h / 2, text=self._text, fill=fg, font=font, anchor="w")

    def _on_click(self):
        if self._cmd:
            self._cmd()


__all__ = ["StyledButton", "NavButton"]
