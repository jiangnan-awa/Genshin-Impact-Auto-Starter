"""
GUI v2 package.

注意：
- 本包内模块需保证 import 无副作用（不创建窗口、不调用 mainloop）。
- customtkinter 的 import 需尽量延后（函数内部）或使用 try/except。
"""

from __future__ import annotations

__all__ = [
    "app",
    "dpi",
    "state",
    "autosave",
    "bindings",
]

