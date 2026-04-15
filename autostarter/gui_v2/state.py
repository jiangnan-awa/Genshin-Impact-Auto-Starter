"""
GUI v2 runtime state (pure data).

不应依赖 customtkinter / tkinter，保证 import 纯净。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(slots=True)
class AppState:
    """
    GUI v2 的最小状态容器（占位）。
    """

    # 未来可替换为更严格的类型/结构
    user: Optional[str] = None
    selected_account_id: Optional[str] = None
    flags: Dict[str, bool] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)

