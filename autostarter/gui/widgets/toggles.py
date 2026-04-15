"""
autostarter.gui.widgets.toggles

从根目录 gui.py 拆出的 ToggleSwitch 控件。

约束：导入时不得创建 Tk，也不得调用 mainloop。
"""

from __future__ import annotations

# 允许在无 tkinter 环境下被导入（见 tests.test_gui_imports）。
try:
    import tkinter as tk  # type: ignore
    _FrameBase = tk.Frame  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    tk = None  # type: ignore

    class _FrameBase:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("tkinter 不可用，无法创建 GUI 控件")

from autostarter.gui.style import ACCENT, BG, FG


class ToggleSwitch(_FrameBase):
    """Modern pill-shaped toggle switch drawn on Canvas."""

    W, H = 46, 24  # pill dimensions
    PAD = 3  # thumb padding inside pill

    def __init__(self, master, text: str = "", variable=None, command=None, bg=None, **kw):
        _bg = bg or BG
        super().__init__(master, bg=_bg, cursor="hand2", **kw)
        self._var = variable or tk.BooleanVar(value=False)
        self._cmd = command
        self._animating = False

        # Canvas for the pill + thumb
        self._cv = tk.Canvas(self, width=self.W, height=self.H, bg=_bg, highlightthickness=0, cursor="hand2")
        self._cv.pack(side=tk.LEFT)

        # Label text next to toggle
        if text:
            tk.Label(self, text=text, bg=_bg, fg=FG, font=("Microsoft YaHei UI", 10), cursor="hand2").pack(
                side=tk.LEFT, padx=(8, 0)
            )

        self._draw()
        # Trace variable changes (e.g. from _load_data)
        self._var.trace_add("write", lambda *_: self._draw())

        for w in self.winfo_children() + [self]:
            w.bind("<Button-1>", self._toggle)
        self._cv.bind("<Button-1>", self._toggle)

    def _draw(self):
        """Render the pill and thumb at their current (resting) state."""
        cv = self._cv
        cv.delete("all")
        on = self._var.get()
        pill_color = ACCENT if on else "#3a3a5a"
        r = self.H // 2
        # Pill background (perfect arcs)
        cv.create_arc(0, 0, self.H, self.H, start=90, extent=180, fill=pill_color, outline="")
        cv.create_arc(self.W - self.H, 0, self.W, self.H, start=270, extent=180, fill=pill_color, outline="")
        cv.create_rectangle(r, 0, self.W - r, self.H, fill=pill_color, outline="")
        # Thumb
        thumb_x = self.W - self.H + self.PAD if on else self.PAD
        d = self.H - 2 * self.PAD
        cv.create_oval(thumb_x, self.PAD, thumb_x + d, self.PAD + d, fill="#ffffff", outline="")

    def _toggle(self, _=None):
        self._var.set(not self._var.get())
        if self._cmd:
            self._cmd()

    def get(self) -> bool:
        return bool(self._var.get())

    def set(self, value: bool) -> None:
        self._var.set(bool(value))


__all__ = ["ToggleSwitch"]
