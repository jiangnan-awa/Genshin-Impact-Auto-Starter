"""
GUI v2 application entrypoints.

本模块导入时不得产生 GUI 副作用（不创建窗口/不进入 mainloop）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .state import AppState


def _import_customtkinter():
    """
    延后导入 customtkinter，保证本模块 import 时无 GUI 相关副作用，
    且在缺少依赖时给出更可读的错误。
    """
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover - 仅在运行 GUI 时触发
        raise RuntimeError("customtkinter 未安装或不可用，无法启动 GUI v2") from e
    return ctk


@dataclass(slots=True)
class App:
    """
    GUI v2 的最小应用骨架。

    说明：这里只定义结构，不在 import 阶段创建任何窗口。
    """

    state: AppState
    root: object

    @classmethod
    def create(cls, state: Optional[AppState] = None) -> "App":
        ctk = _import_customtkinter()
        root = ctk.CTk()
        return cls(state=state or AppState(), root=root)

    def run(self) -> None:  # pragma: no cover
        """
        进入 mainloop。调用方负责在合适时机调用。
        """
        # 延后导入，避免 import 时加载 tkinter 相关内容
        ctk = _import_customtkinter()
        if isinstance(self.root, ctk.CTk):
            self.root.mainloop()
        else:
            raise RuntimeError("root 类型不正确，无法运行 GUI")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    GUI v2 启动入口（最小可运行骨架）。

    约束：
    - 本模块 import 时不得创建窗口/进入 mainloop
    - 仅在 main() 被调用时才导入/创建 customtkinter 组件
    """
    _ = argv  # 预留：未来解析命令行参数

    # 延后导入：避免 import 阶段引入 GUI 副作用
    from . import dpi
    from .bindings import bind_default_shortcuts
    from .pages import accounts, launch, mod, presets, signin
    from .widgets.sidebar import SidebarNavItem, SidebarSpec, build_sidebar
    from .widgets.toast import ToastManager, build_toast_bar

    # Windows 高 DPI：尽量在创建窗口之前调用
    dpi.set_dpi_awareness()

    ctk = _import_customtkinter()
    root = ctk.CTk()
    root.title("Genshin Impact Auto-Starter (GUI v2)")
    try:
        root.geometry("1100x720")
        root.minsize(900, 600)
    except Exception:
        pass

    # 可选：按检测到的缩放应用到 customtkinter（失败则忽略）
    try:
        dpi.apply_scaling_to_customtkinter(root)
    except Exception:
        pass

    # ───────────────────────── Layout ─────────────────────────
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=0)
    root.grid_columnconfigure(0, weight=1)

    body = ctk.CTkFrame(master=root, corner_radius=0)
    body.grid(row=0, column=0, sticky="nsew")
    body.grid_rowconfigure(0, weight=1)
    body.grid_columnconfigure(1, weight=1)

    # 底部 toast / 状态栏
    toast_bar = build_toast_bar(root)
    toast_bar.frame.grid(row=1, column=0, sticky="ew")
    toast = ToastManager(root=root, bar=toast_bar)

    # Content container（右侧）
    content_container = ctk.CTkFrame(master=body, corner_radius=0)
    content_container.grid(row=0, column=1, sticky="nsew")
    content_container.grid_rowconfigure(0, weight=1)
    content_container.grid_columnconfigure(0, weight=1)

    state = AppState()
    # 注入线程安全的 toast 回调，供各页面（后台线程）提示保存/错误信息使用。
    def _toast_cb(text: str, ms: int = 1800) -> None:
        try:
            from .widgets.toast import ToastOptions

            root.after(0, lambda: toast.show(text, options=ToastOptions(duration_ms=ms)))  # type: ignore[attr-defined]
        except Exception:
            # 不阻断业务
            return

    state.data["toast_cb"] = _toast_cb
    state.data["toast"] = _toast_cb
    current_page: dict[str, object] = {"widget": None, "key": ""}

    page_builders = {
        "accounts": accounts.build_page,
        "launch": launch.build_page,
        "mod": mod.build_page,
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

    # Sidebar（左侧）
    sidebar = build_sidebar(
        body,
        SidebarSpec(
            items=[
                SidebarNavItem("accounts", "账号管理"),
                SidebarNavItem("launch", "启动设置"),
                SidebarNavItem("mod", "Mod 设置"),
                SidebarNavItem("signin", "签到设置"),
                SidebarNavItem("presets", "预设"),
            ],
            active_key="accounts",
            on_navigate=on_navigate,
        ),
    )
    sidebar.frame.grid(row=0, column=0, sticky="nsw")

    # 默认页面
    show_page("accounts")

    # 快捷键（占位）
    bind_default_shortcuts(root, on_reload=lambda: show_page(current_page.get("key") or "accounts"))

    root.mainloop()
    return 0
