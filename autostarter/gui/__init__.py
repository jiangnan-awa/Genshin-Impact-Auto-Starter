"""
autostarter.gui

GUI 重构包骨架（仅提供可导入的模块与入口定义）。

约束：
- 导入本包及其子模块不得创建 Tk/CTk 实例
- 导入时不得调用 mainloop()

真正启动 GUI 请调用：autostarter.gui.app.main()
"""

from __future__ import annotations

__all__ = [
    "app",
    "style",
    "bindings",
    "widgets",
    "pages",
    "dialogs",
]

