"""
Mod page (GUI v2): Mod 启动模式设置。

导入无副作用。

需求：
- 使用 CTkScrollableFrame，保证滚轮可用
- 按钮/输入框统一使用 gui_v2.widgets.forms
- 关键字段对接 settings.json（通过 gui_v2.bindings.load_settings/update_settings）
- Debouncer 防抖自动保存 + toast 回调（从 state.data 注入）
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..state import AppState


def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法创建 Mod 页面") from e
    return ctk


def build_page(parent: object, state: Optional[AppState] = None) -> object:
    ctk = _import_customtkinter()
    import tkinter as tk

    from .. import bindings as b
    from ..autosave import Debouncer
    from ..widgets import forms

    state = state or AppState()

    # toast 注入：允许 app 通过 state.data 传入一个线程安全回调
    toast_cb: Optional[Callable[[str], None]] = None
    if isinstance(getattr(state, "data", None), dict):
        maybe = state.data.get("toast") or state.data.get("toast_cb") or state.data.get("toast_callback")
        if callable(maybe):
            toast_cb = maybe  # type: ignore[assignment]

    def toast(msg: str) -> None:
        if toast_cb is None:
            return
        try:
            toast_cb(msg)
        except Exception:
            return

    settings: Dict[str, Any] = {}
    try:
        settings = b.load_settings()
    except Exception:
        settings = {}

    # UI 事件屏蔽：初始化/批量刷新控件时，避免触发 autosave
    suspend_events: Dict[str, bool] = {"all": False}

    def set_suspend(flag: bool) -> None:
        suspend_events["all"] = bool(flag)

    def is_suspended() -> bool:
        return bool(suspend_events["all"])

    # ───────────────────────── Variables ─────────────────────────
    var_mod_enabled = tk.BooleanVar(value=bool(settings.get("mod_enabled", False)))
    var_mod_path = tk.StringVar(value=str(settings.get("mod_path", "") or ""))
    var_mod_wait_seconds = tk.StringVar(value=str(settings.get("mod_wait_seconds", 6) or 6))

    # ───────────────────────── Autosave ─────────────────────────
    def _safe_int(val: str, default: int, *, min_v: int = 0, max_v: int = 120) -> int:
        try:
            n = int(str(val).strip())
        except Exception:
            n = int(default)
        n = max(min_v, min(max_v, n))
        return n

    def _save_now() -> None:
        payload = {
            "mod_enabled": bool(var_mod_enabled.get()),
            "mod_path": str(var_mod_path.get()).strip(),
            "mod_wait_seconds": _safe_int(var_mod_wait_seconds.get(), 6, min_v=0, max_v=120),
        }
        try:
            b.update_settings(**payload)
            toast("已自动保存 Mod 设置")
        except Exception as e:  # pragma: no cover
            toast(f"保存失败：{e}")

    deb_save = Debouncer(0.6, _save_now)

    def trigger_save() -> None:
        if is_suspended():
            return
        deb_save.trigger()

    # ───────────────────────── UI Layout ─────────────────────────
    frame = ctk.CTkFrame(master=parent, corner_radius=0)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(master=frame, text="Mod 设置", font=ctk.CTkFont(size=18, weight="bold")).grid(
        row=0, column=0, padx=16, pady=(16, 10), sticky="w"
    )

    scroll = ctk.CTkScrollableFrame(master=frame, corner_radius=8)
    scroll.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")

    forms.make_section_title(scroll, "Mod 启动模式").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    forms.make_switch(scroll, "启用 Mod 启动模式", variable=var_mod_enabled, command=trigger_save).pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )

    def _entry_row(label_text: str, var: tk.StringVar, placeholder: str = "") -> object:
        r = ctk.CTkFrame(master=scroll, fg_color="transparent")
        r.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
        r.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(master=r, text=label_text).grid(row=0, column=0, padx=(0, 8), sticky="w")
        ent = forms.make_entry(r, placeholder=placeholder, textvariable=var)
        ent.grid(row=0, column=1, sticky="ew")
        try:
            ent.bind("<KeyRelease>", lambda _e=None: trigger_save())
            ent.bind("<FocusOut>", lambda _e=None: trigger_save())
        except Exception:
            pass
        return ent

    def _path_row(
        label_text: str,
        var: tk.StringVar,
        *,
        placeholder: str = "",
        dialog_title: str = "选择文件",
        filetypes=None,
    ) -> object:
        r = ctk.CTkFrame(master=scroll, fg_color="transparent")
        r.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
        r.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(master=r, text=label_text).grid(row=0, column=0, padx=(0, 8), sticky="w")

        ent = forms.make_entry(r, placeholder=placeholder, textvariable=var)
        ent.grid(row=0, column=1, sticky="ew")
        try:
            ent.bind("<KeyRelease>", lambda _e=None: trigger_save())
            ent.bind("<FocusOut>", lambda _e=None: trigger_save())
        except Exception:
            pass

        btn = forms.make_browse_file_button(
            r,
            var,
            dialog_title,
            filetypes=filetypes,
            on_selected=trigger_save,
            width=90,
        )
        btn.grid(row=0, column=2, padx=(8, 0), sticky="e")
        return ent

    exe_filetypes = [("可执行文件", "*.exe"), ("所有文件", "*.*")]
    _path_row(
        "Mod 程序路径",
        var_mod_path,
        placeholder="例如：D:\\Mod\\mod.exe",
        dialog_title="选择 Mod 程序",
        filetypes=exe_filetypes,
    )
    _entry_row("启动后等待 (秒)", var_mod_wait_seconds, placeholder="0~120")

    ctk.CTkLabel(
        master=scroll,
        text="说明：在启动其他程序前，先以 --auto-launch 参数运行该 Mod 程序，并等待指定秒数。",
        anchor="w",
        justify="left",
        wraplength=780,
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(0, 4))
    ctk.CTkLabel(
        master=scroll,
        text="提示：也可在命令行加 --mod-mode 临时启用。",
        anchor="w",
        justify="left",
        wraplength=780,
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))

    set_suspend(True)
    try:
        pass
    finally:
        set_suspend(False)

    return frame
