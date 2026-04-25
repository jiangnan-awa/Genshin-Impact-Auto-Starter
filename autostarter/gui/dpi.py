from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
@dataclass(slots=True)
class DpiInfo:
    scale: float = 1.0
    source: str = "default"
def set_dpi_awareness() -> None:
    import sys
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            return
        except Exception:
            pass
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        return
def detect_dpi_scale() -> DpiInfo:
    return DpiInfo(scale=1.0, source="placeholder")
def apply_scaling_to_customtkinter(root: object, scale: Optional[float] = None) -> None:
    if scale is None:
        scale = detect_dpi_scale().scale
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法设置缩放") from e
    try:
        ctk.set_widget_scaling(scale)
        ctk.set_window_scaling(scale)
    except Exception:
        return
