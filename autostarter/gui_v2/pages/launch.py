"""
Launch page (GUI v2): 启动设置。

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
        raise RuntimeError("customtkinter 未安装或不可用，无法创建 Launch 页面") from e
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

    # ───────────────────────── Load settings ─────────────────────────
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
    var_bettergi_enabled = tk.BooleanVar(value=bool(settings.get("bettergi_enabled", True)))
    var_bettergi_onedragon_enabled = tk.BooleanVar(value=bool(settings.get("bettergi_onedragon_enabled", False)))
    var_bettergi_path = tk.StringVar(value=str(settings.get("bettergi_path", "") or ""))
    var_bettergi_onedragon_config = tk.StringVar(value=str(settings.get("bettergi_onedragon_config", "") or ""))
    var_bettergi_onedragon_config_2 = tk.StringVar(value=str(settings.get("bettergi_onedragon_config_2", "") or ""))

    var_genshin_path = tk.StringVar(value=str(settings.get("genshin_path", "") or ""))

    var_external_launcher_mode = tk.BooleanVar(value=bool(settings.get("external_launcher_mode", False)))
    var_external_launcher_path = tk.StringVar(value=str(settings.get("external_launcher_path", "") or ""))
    var_external_launcher_args = tk.StringVar(value=str(settings.get("external_launcher_args", "") or ""))
    var_external_launcher_wait_seconds = tk.StringVar(value=str(settings.get("external_launcher_wait_seconds", 5) or 5))

    # ───────────────────────── Autosave ─────────────────────────
    def _safe_int(val: str, default: int, *, min_v: int = 0, max_v: int = 300) -> int:
        try:
            n = int(str(val).strip())
        except Exception:
            n = int(default)
        n = max(min_v, min(max_v, n))
        return n

    def _save_now() -> None:
        payload = {
            "bettergi_enabled": bool(var_bettergi_enabled.get()),
            "bettergi_path": str(var_bettergi_path.get()).strip(),
            "bettergi_onedragon_enabled": bool(var_bettergi_onedragon_enabled.get()),
            "bettergi_onedragon_config": str(var_bettergi_onedragon_config.get()).strip(),
            "bettergi_onedragon_config_2": str(var_bettergi_onedragon_config_2.get()).strip(),
            "genshin_path": str(var_genshin_path.get()).strip(),
            "external_launcher_mode": bool(var_external_launcher_mode.get()),
            "external_launcher_path": str(var_external_launcher_path.get()).strip(),
            "external_launcher_args": str(var_external_launcher_args.get()).strip(),
            "external_launcher_wait_seconds": _safe_int(var_external_launcher_wait_seconds.get(), 5, min_v=0, max_v=300),
        }
        try:
            b.update_settings(**payload)
            toast("已自动保存启动设置")
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

    ctk.CTkLabel(master=frame, text="启动设置", font=ctk.CTkFont(size=18, weight="bold")).grid(
        row=0, column=0, padx=16, pady=(16, 10), sticky="w"
    )

    scroll = ctk.CTkScrollableFrame(master=frame, corner_radius=8)
    scroll.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
    try:
        scroll.grid_columnconfigure(0, weight=1)  # type: ignore[attr-defined]
    except Exception:
        pass

    # ───────────────────────── Section: BetterGI ─────────────────────────
    forms.make_section_title(scroll, "BetterGI 设置").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))

    row1 = ctk.CTkFrame(master=scroll, fg_color="transparent")
    row1.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
    sw_bettergi = forms.make_switch(row1, "启用 BetterGI 启动", variable=var_bettergi_enabled, command=trigger_save)
    sw_bettergi.pack(side="left", padx=(0, 18))
    sw_od = forms.make_switch(row1, "启用一条龙模式", variable=var_bettergi_onedragon_enabled, command=trigger_save)
    sw_od.pack(side="left")

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
        "BetterGI 路径 (.exe)",
        var_bettergi_path,
        placeholder="例如：D:\\BetterGI\\BetterGI.exe",
        dialog_title="选择 BetterGI 可执行文件",
        filetypes=exe_filetypes,
    )
    _entry_row("一条龙配置名称", var_bettergi_onedragon_config, placeholder="例如：每日任务")
    _entry_row("第二个一条龙配置", var_bettergi_onedragon_config_2, placeholder="可选：任务结束后切换")
    ctk.CTkLabel(
        master=scroll,
        text="提示：填写第二个配置后，将在第一个任务结束后自动切换；留空则使用 BetterGI 当前选定的配置。",
        anchor="w",
        justify="left",
        wraplength=780,
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))

    # ───────────────────────── Section: Direct Genshin ─────────────────────────
    forms.make_section_title(scroll, "直接启动原神").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    _path_row(
        "游戏路径 (Genshin Impact.exe)",
        var_genshin_path,
        placeholder="例如：...\\Genshin Impact\\Genshin Impact.exe",
        dialog_title="选择原神可执行文件",
        filetypes=exe_filetypes,
    )
    ctk.CTkLabel(
        master=scroll,
        text="提示：仅在禁用 BetterGI 且未使用外置启动器时生效。",
        anchor="w",
        justify="left",
        wraplength=780,
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))

    # ───────────────────────── Section: External launcher ─────────────────────────
    forms.make_section_title(scroll, "外置启动器模式").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    forms.make_switch(scroll, "启用外置启动器", variable=var_external_launcher_mode, command=trigger_save).pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )
    _path_row(
        "外置启动器路径",
        var_external_launcher_path,
        placeholder="例如：...\\launcher.exe",
        dialog_title="选择外置启动器",
        filetypes=exe_filetypes,
    )
    _entry_row("启动参数", var_external_launcher_args, placeholder="例如：--arg1 --arg2")
    _entry_row("启动后等待 (秒)", var_external_launcher_wait_seconds, placeholder="0~300")
    ctk.CTkLabel(
        master=scroll,
        text="提示：启用后，先启动外置启动器，等待指定秒数后再继续启动 BetterGI/原神。",
        anchor="w",
        justify="left",
        wraplength=780,
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))

    # 首次渲染：防止一些 Tk 版本在 set/insert 时触发事件
    set_suspend(True)
    try:
        pass
    finally:
        set_suspend(False)

    return frame
