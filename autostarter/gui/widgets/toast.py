from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法显示 Toast") from e
    return ctk
@dataclass(slots=True)
class ToastOptions:
    duration_ms: int = 2000
class ToastBar:
    def __init__(self, frame: object, label: object):
        self.frame = frame
        self.label = label
    def set_text(self, text: str) -> None:
        try:
            self.label.configure(text=text)  # type: ignore[attr-defined]
        except Exception:
            return
class ToastManager:
    def __init__(self, root: object, bar: Optional[ToastBar] = None):
        self.root = root
        self.bar = bar
    def show(self, message: str, options: Optional[ToastOptions] = None) -> None:  # pragma: no cover
        _ = _import_customtkinter()
        options = options or ToastOptions()
        if self.bar is not None:
            self.bar.set_text(message)
        if hasattr(self.root, "after"):
            self.root.after(options.duration_ms, lambda: None)  # type: ignore[attr-defined]
            if self.bar is not None:
                self.root.after(options.duration_ms, lambda: self.bar and self.bar.set_text(""))  # type: ignore[attr-defined]
            else:
                self.root.after(options.duration_ms, lambda: None)  # type: ignore[attr-defined]
def build_toast_bar(parent: object) -> ToastBar:
    ctk = _import_customtkinter()
    frame = ctk.CTkFrame(master=parent, height=28, corner_radius=0)
    try:
        frame.pack_propagate(False)
    except Exception:
        pass
    label = ctk.CTkLabel(master=frame, text="", anchor="w")
    label.pack(fill="both", expand=True, padx=10)
    return ToastBar(frame=frame, label=label)
