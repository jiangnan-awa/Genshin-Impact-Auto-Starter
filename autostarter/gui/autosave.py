from __future__ import annotations
import threading
from dataclasses import dataclass
from typing import Callable, Optional
@dataclass(slots=True)
class AutoSaveService:
    save_fn: Callable[[], None]
    interval_sec: float = 10.0
    running: bool = False
    def start(self) -> None:  # pragma: no cover
        self.running = True
    def stop(self) -> None:  # pragma: no cover
        self.running = False
    def tick(self) -> None:
        if self.running:
            self.save_fn()
def create_default_autosave(save_fn: Optional[Callable[[], None]] = None) -> AutoSaveService:
    if save_fn is None:
        save_fn = lambda: None
    return AutoSaveService(save_fn=save_fn)
class Debouncer:
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
