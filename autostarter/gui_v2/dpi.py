"""
DPI / scaling utilities for GUI v2.

导入无副作用；依赖 GUI 框架的操作应在函数调用时进行。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class DpiInfo:
    scale: float = 1.0
    source: str = "default"


def set_dpi_awareness() -> None:
    """在 Windows 下启用高 DPI 适配（安全降级）。

    约束：
    - 仅在 win32 下尝试设置
    - 调用方应尽量在创建 Tk/CTk 窗口前调用
    - 任意异常都必须吞掉，避免在精简/旧系统环境中阻断启动
    """

    import sys

    if sys.platform != "win32":
        return

    try:
        import ctypes

        # Windows 8.1+（shcore.dll）
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            return
        except Exception:
            pass

        # Windows Vista+（user32.dll）
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        return


def detect_dpi_scale() -> DpiInfo:
    """
    检测当前系统建议的 DPI 缩放比例。

    目前为占位实现：返回 1.0。
    """
    return DpiInfo(scale=1.0, source="placeholder")


def apply_scaling_to_customtkinter(root: object, scale: Optional[float] = None) -> None:
    """
    将缩放设置应用到 customtkinter。

    - root: CTk 实例（或兼容对象）
    - scale: 目标缩放比例；不提供则自动检测
    """
    if scale is None:
        scale = detect_dpi_scale().scale

    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法设置缩放") from e

    # customtkinter 的 API：set_widget_scaling / set_window_scaling
    # 这里保持最小副作用，仅在显式调用时执行。
    try:
        ctk.set_widget_scaling(scale)
        ctk.set_window_scaling(scale)
    except Exception:
        # 兼容未来 API 变更：不在此处中断导入/测试
        return
