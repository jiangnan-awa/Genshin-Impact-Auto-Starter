from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Tuple, Any
def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法创建表单组件") from e
    return ctk
CONTROL_HEIGHT = 32
PAD_X = 10
PAD_Y = 8
ROW_GAP_Y = 8
SECTION_GAP_Y = 12
def make_button(parent: object, text: str, command=None, **kwargs) -> object:
    ctk = _import_customtkinter()
    return ctk.CTkButton(master=parent, text=text, command=command, height=CONTROL_HEIGHT, **kwargs)
def make_browse_file_button(
    parent: object,
    var: Any,
    title: str,
    filetypes: Sequence[Tuple[str, str]] | None = None,
    on_selected: Optional[Callable[[], None]] = None,
    *,
    text: str = "浏览…",
    **kwargs,
) -> object:
    def _on_click() -> None:
        import tkinter.filedialog as fd
        path = fd.askopenfilename(title=title, filetypes=list(filetypes) if filetypes else None)
        if not path:
            return
        try:
            var.set(path)
        except Exception:
            return
        if on_selected is not None:
            try:
                on_selected()
            except Exception:
                return
    return make_button(parent, text=text, command=_on_click, **kwargs)
def make_entry(parent: object, placeholder: str = "", **kwargs) -> object:
    ctk = _import_customtkinter()
    return ctk.CTkEntry(master=parent, placeholder_text=placeholder, height=CONTROL_HEIGHT, **kwargs)
def make_switch(parent: object, text: str, variable=None, command=None, **kwargs) -> object:
    ctk = _import_customtkinter()
    return ctk.CTkSwitch(master=parent, text=text, variable=variable, command=command, height=CONTROL_HEIGHT, **kwargs)
def make_section_title(parent: object, text: str, **kwargs) -> object:
    ctk = _import_customtkinter()
    label = ctk.CTkLabel(master=parent, text=text, font=ctk.CTkFont(size=14, weight="bold"), **kwargs)
    return label
@dataclass(slots=True)
class LabeledEntrySpec:
    label: str
    placeholder: str = ""
    on_change: Optional[Callable[[str], None]] = None
def build_labeled_entry(parent: object, spec: LabeledEntrySpec) -> object:
    ctk = _import_customtkinter()
    frame = ctk.CTkFrame(master=parent)
    frame.grid_columnconfigure(1, weight=1)
    label = ctk.CTkLabel(master=frame, text=spec.label)
    label.grid(row=0, column=0, padx=(PAD_X, 6), pady=PAD_Y, sticky="w")
    entry = make_entry(frame, placeholder=spec.placeholder)
    entry.grid(row=0, column=1, padx=(6, PAD_X), pady=PAD_Y, sticky="ew")
    if spec.on_change is not None:
        try:
            entry.bind("<KeyRelease>", lambda _e: spec.on_change(entry.get()))
        except Exception:
            pass
    return frame
__all__ = [
    "CONTROL_HEIGHT",
    "PAD_X",
    "PAD_Y",
    "ROW_GAP_Y",
    "SECTION_GAP_Y",
    "make_button",
    "make_browse_file_button",
    "make_entry",
    "make_switch",
    "make_section_title",
    "LabeledEntrySpec",
    "build_labeled_entry",
]
