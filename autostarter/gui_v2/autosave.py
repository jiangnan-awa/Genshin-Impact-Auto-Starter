"""
Autosave helpers for GUI v2.

导入时不得启动线程/定时器；所有后台行为都必须显式 start()。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(slots=True)
class AutoSaveService:
    """
    轻量自动保存骨架（占位）。

    - save_fn: 实际保存逻辑回调
    - interval_sec: 保存间隔（未来可用于定时器/after）
    """

    save_fn: Callable[[], None]
    interval_sec: float = 10.0
    running: bool = False

    def start(self) -> None:  # pragma: no cover
        self.running = True

    def stop(self) -> None:  # pragma: no cover
        self.running = False

    def tick(self) -> None:
        """
        执行一次保存（由外部调度，比如 customtkinter 的 after）。
        """
        if self.running:
            self.save_fn()


def create_default_autosave(save_fn: Optional[Callable[[], None]] = None) -> AutoSaveService:
    if save_fn is None:
        save_fn = lambda: None
    return AutoSaveService(save_fn=save_fn)


class Debouncer:
    """
    防抖器：在触发后延迟执行 callback；若在延迟内再次触发，则重置计时。

    注意：实现基于 threading.Timer，callback 会在后台线程执行。
    - 适合：写文件/调用业务逻辑
    - 不建议：直接操作 tkinter/customtkinter UI（请通过注入的回调在主线程调度）
    """

    def __init__(self, delay_seconds: float, callback: Callable[[], None]):
        self.delay_seconds = float(delay_seconds)
        self.callback = callback
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def trigger(self) -> None:
        with self._lock:
            if self._timer is not None:
                try:
                    self._timer.cancel()
                except Exception:
                    pass
            self._timer = threading.Timer(self.delay_seconds, self.callback)
            self._timer.daemon = True
            self._timer.start()
