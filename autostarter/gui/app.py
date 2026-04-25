from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence
from .state import AppState
def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover - 仅在运行 GUI 时触发
        raise RuntimeError("customtkinter 未安装或不可用，无法启动 GUI") from e
    return ctk
@dataclass(slots=True)
class App:
    state: AppState
    root: object
    @classmethod
    def create(cls, state: Optional[AppState] = None) -> "App":
        ctk = _import_customtkinter()
        root = ctk.CTk()
        return cls(state=state or AppState(), root=root)
    def run(self) -> None:  # pragma: no cover
        ctk = _import_customtkinter()
        if isinstance(self.root, ctk.CTk):
            self.root.mainloop()
        else:
            raise RuntimeError("root 类型不正确，无法运行 GUI")
def main(argv: Optional[Sequence[str]] = None) -> int:
    _ = argv  # 预留：未来解析命令行参数
    from . import dpi
    from .bindings import bind_default_shortcuts
    from .pages import accounts, presets, signin, startup
    from .widgets.sidebar import SidebarNavItem, SidebarSpec, build_sidebar
    from .widgets.toast import ToastManager, build_toast_bar
    dpi.set_dpi_awareness()
    ctk = _import_customtkinter()
    root = ctk.CTk()
    root.title("Genshin Impact Auto-Starter")
    try:
        root.geometry("1100x720")
        root.minsize(900, 600)
    except Exception:
        pass
    try:
        dpi.apply_scaling_to_customtkinter(root)
    except Exception:
        pass
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=0)
    root.grid_columnconfigure(0, weight=1)
    body = ctk.CTkFrame(master=root, corner_radius=0)
    body.grid(row=0, column=0, sticky="nsew")
    body.grid_rowconfigure(0, weight=1)
    body.grid_columnconfigure(1, weight=1)
    toast_bar = build_toast_bar(root)
    toast_bar.frame.grid(row=1, column=0, sticky="ew")
    toast = ToastManager(root=root, bar=toast_bar)
    content_container = ctk.CTkFrame(master=body, corner_radius=0)
    content_container.grid(row=0, column=1, sticky="nsew")
    content_container.grid_rowconfigure(0, weight=1)
    content_container.grid_columnconfigure(0, weight=1)
    state = AppState()
    def _toast_cb(text: str, ms: int = 1800) -> None:
        try:
            from .widgets.toast import ToastOptions
            root.after(0, lambda: toast.show(text, options=ToastOptions(duration_ms=ms)))  # type: ignore[attr-defined]
        except Exception:
            return
    state.data["toast_cb"] = _toast_cb
    state.data["toast"] = _toast_cb
    current_page: dict[str, object] = {"widget": None, "key": ""}
    page_builders = {
        "accounts": accounts.build_page,
        "startup": startup.build_page,
        "signin": signin.build_page,
        "presets": presets.build_page,
    }
    def show_page(key: str) -> None:
        builder = page_builders.get(key)
        if builder is None:
            return
        old = current_page.get("widget")
        if old is not None:
            try:
                old.destroy()  # type: ignore[attr-defined]
            except Exception:
                pass
        page = builder(content_container, state=state)
        try:
            page.grid(row=0, column=0, sticky="nsew")  # type: ignore[attr-defined]
        except Exception:
            try:
                page.pack(fill="both", expand=True)  # type: ignore[attr-defined]
            except Exception:
                pass
        sidebar.set_active(key)
        current_page["widget"] = page
        current_page["key"] = key
    def on_navigate(key: str) -> None:
        show_page(key)
        try:
            toast.show(f"切换到：{key}")
        except Exception:
            pass
    sidebar = build_sidebar(
        body,
        SidebarSpec(
            items=[
                SidebarNavItem("accounts", "账号管理"),
                SidebarNavItem("startup", "启动配置"),
                SidebarNavItem("signin", "签到设置"),
                SidebarNavItem("presets", "预设"),
            ],
            active_key="accounts",
            on_navigate=on_navigate,
        ),
    )
    sidebar.frame.grid(row=0, column=0, sticky="nsw")
    show_page("accounts")
    bind_default_shortcuts(root, on_reload=lambda: show_page(current_page.get("key") or "accounts"))
    root.mainloop()
    return 0
