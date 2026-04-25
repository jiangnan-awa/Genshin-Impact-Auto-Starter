from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional
def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法创建 Sidebar") from e
    return ctk
@dataclass(slots=True)
class SidebarNavItem:
    key: str
    label: str
@dataclass(slots=True)
class SidebarSpec:
    items: Optional[List[SidebarNavItem]] = None
    active_key: Optional[str] = None
    on_navigate: Optional[Callable[[str], None]] = None
def default_nav_items() -> List[SidebarNavItem]:
    return [
        SidebarNavItem("accounts", "账号管理"),
        SidebarNavItem("startup", "启动配置"),
        SidebarNavItem("signin", "签到设置"),
    ]
class SidebarController:
    def __init__(self, frame: object, buttons: Dict[str, object], labels: Dict[str, str]):
        self.frame = frame
        self._buttons = buttons
        self._labels = labels
        self.active_key: Optional[str] = None
    def set_active(self, key: Optional[str]) -> None:
        ctk = _import_customtkinter()
        self.active_key = key
        for k, btn in self._buttons.items():
            txt = self._labels.get(k, k)
            if key is not None and k == key:
                txt = f"▶  {txt}"
            btn.configure(text=txt)  # type: ignore[attr-defined]
            try:
                if key is not None and k == key:
                    btn.configure(font=ctk.CTkFont(size=13, weight="bold"))
                else:
                    btn.configure(font=ctk.CTkFont(size=13, weight="normal"))
            except Exception:
                pass
def build_sidebar(parent: object, spec: Optional[SidebarSpec] = None) -> SidebarController:
    ctk = _import_customtkinter()
    spec = spec or SidebarSpec()
    items: Iterable[SidebarNavItem] = spec.items or default_nav_items()
    frame = ctk.CTkFrame(master=parent, width=220, corner_radius=0)
    try:
        frame.pack_propagate(False)
    except Exception:
        pass
    title = ctk.CTkLabel(master=frame, text="GIAutoStarter", anchor="w")
    title.pack(fill="x", padx=12, pady=(12, 6))
    sep = ctk.CTkFrame(master=frame, height=1)
    sep.pack(fill="x", padx=12, pady=(0, 10))
    buttons: Dict[str, object] = {}
    labels: Dict[str, str] = {}
    for item in items:
        labels[item.key] = item.label
        def _mk_cmd(k: str):
            return lambda: spec.on_navigate and spec.on_navigate(k)
        btn = ctk.CTkButton(master=frame, text=item.label, anchor="w", command=_mk_cmd(item.key))
        btn.pack(fill="x", padx=12, pady=4)
        buttons[item.key] = btn
    controller = SidebarController(frame=frame, buttons=buttons, labels=labels)
    controller.set_active(spec.active_key)
    return controller
