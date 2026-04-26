from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
from .widgets.dialog import show_dialog


@dataclass(slots=True)
class NotifyRequest:
    level: str
    title: str
    message: str
    kind: str
    toast_ms: int = 1800
    debug_only_modal: bool = False


def should_modal(*, kind: str, debug_mode: bool, debug_only_modal: bool = False) -> bool:
    if debug_only_modal and not debug_mode:
        return False
    if kind in {"path_invalid", "preset_failed", "action_required", "cookie_invalid", "feature_unavailable"}:
        return True
    if kind == "save_failed":
        return bool(debug_only_modal and debug_mode)
    return False


def build_notifier(
    *,
    root: Any,
    toast_cb: Optional[Callable[[str, int], None]] = None,
    debug_mode_getter: Optional[Callable[[], bool]] = None,
) -> Callable[[NotifyRequest], None]:
    def _debug() -> bool:
        if debug_mode_getter is None:
            return False
        try:
            return bool(debug_mode_getter())
        except Exception:
            return False

    def _show(req: NotifyRequest) -> None:
        if toast_cb is not None:
            try:
                toast_cb(req.message, int(req.toast_ms))
            except Exception:
                pass
        if not should_modal(kind=req.kind, debug_mode=_debug(), debug_only_modal=bool(req.debug_only_modal)):
            return
        modal = req.kind in {"path_invalid", "preset_failed", "action_required", "cookie_invalid"}
        auto_close_ms = 2200 if req.kind == "feature_unavailable" else None
        try:
            show_dialog(
                root,
                title=req.title,
                message=req.message,
                level=req.level,
                modal=bool(modal),
                auto_close_ms=auto_close_ms,
            )
        except Exception:
            return

    def notify(req: NotifyRequest) -> None:
        if hasattr(root, "after"):
            root.after(0, lambda: _show(req))
            return
        _show(req)

    return notify
