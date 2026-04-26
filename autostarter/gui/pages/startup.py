from __future__ import annotations
from typing import Any, Callable, Dict, Optional
from ..state import AppState
def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法创建启动配置页面") from e
    return ctk
def build_page(parent: object, state: Optional[AppState] = None) -> object:
    ctk = _import_customtkinter()
    import tkinter as tk
    from .. import bindings as b
    from ..autosave import Debouncer
    from ..widgets import forms
    state = state or AppState()
    toast_cb: Optional[Callable[[str], None]] = None
    if isinstance(getattr(state, "data", None), dict):
        maybe = state.data.get("toast") or state.data.get("toast_cb") or state.data.get("toast_callback")
        if callable(maybe):
            toast_cb = maybe  # type: ignore[assignment]
    notify_cb: Optional[Callable[..., None]] = None
    NotifyRequest = None
    if isinstance(getattr(state, "data", None), dict):
        maybe2 = state.data.get("notify")
        if callable(maybe2):
            notify_cb = maybe2
        NotifyRequest = state.data.get("NotifyRequest")
    def toast(msg: str) -> None:
        if toast_cb is None:
            return
        try:
            toast_cb(msg)
        except Exception:
            return
    def notify(level: str, title: str, message: str, *, kind: str, toast_ms: int = 2200, debug_only_modal: bool = False) -> None:
        if notify_cb is None or NotifyRequest is None:
            toast(message)
            return
        try:
            req = NotifyRequest(level=level, title=title, message=message, kind=kind, toast_ms=int(toast_ms), debug_only_modal=bool(debug_only_modal))
            notify_cb(req)
        except Exception:
            toast(message)
    settings: Dict[str, Any] = {}
    try:
        settings = b.load_settings()
    except Exception:
        settings = {}
    suspend_events: Dict[str, bool] = {"all": False}
    def set_suspend(flag: bool) -> None:
        suspend_events["all"] = bool(flag)
    def is_suspended() -> bool:
        return bool(suspend_events["all"])
    var_bettergi_path = tk.StringVar(value=str(settings.get("bettergi_path", "") or ""))
    var_bettergi_onedragon_config = tk.StringVar(value=str(settings.get("bettergi_onedragon_config", "") or ""))
    var_bettergi_onedragon_config_2 = tk.StringVar(value=str(settings.get("bettergi_onedragon_config_2", "") or ""))
    var_genshin_path = tk.StringVar(value=str(settings.get("genshin_path", "") or ""))
    var_external_launcher_path = tk.StringVar(value=str(settings.get("external_launcher_path", "") or ""))
    var_external_launcher_args = tk.StringVar(value=str(settings.get("external_launcher_args", "") or ""))
    var_external_launcher_wait_seconds = tk.StringVar(value=str(settings.get("external_launcher_wait_seconds", 5) or 5))
    var_mod_path = tk.StringVar(value=str(settings.get("mod_path", "") or ""))
    var_mod_wait_seconds = tk.StringVar(value=str(settings.get("mod_wait_seconds", 6) or 6))
    def _safe_int(val: str, default: int, *, min_v: int = 0, max_v: int = 300) -> int:
        try:
            n = int(str(val).strip())
        except Exception:
            n = int(default)
        n = max(min_v, min(max_v, n))
        return n
    def _save_now() -> None:
        payload = {
            "bettergi_path": str(var_bettergi_path.get()).strip(),
            "bettergi_onedragon_config": str(var_bettergi_onedragon_config.get()).strip(),
            "bettergi_onedragon_config_2": str(var_bettergi_onedragon_config_2.get()).strip(),
            "genshin_path": str(var_genshin_path.get()).strip(),
            "external_launcher_path": str(var_external_launcher_path.get()).strip(),
            "external_launcher_args": str(var_external_launcher_args.get()).strip(),
            "external_launcher_wait_seconds": _safe_int(var_external_launcher_wait_seconds.get(), 5, min_v=0, max_v=300),
            "mod_path": str(var_mod_path.get()).strip(),
            "mod_wait_seconds": _safe_int(var_mod_wait_seconds.get(), 6, min_v=0, max_v=120),
        }
        try:
            b.update_settings(**payload)
            toast("已自动保存启动配置")
        except Exception as e:  # pragma: no cover
            notify("error", "保存失败", f"保存失败：{e}", kind="save_failed", toast_ms=2400, debug_only_modal=True)
    deb_save = Debouncer(0.6, _save_now)
    def trigger_save() -> None:
        if is_suspended():
            return
        deb_save.trigger()
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
    frame = ctk.CTkFrame(master=parent, corner_radius=0)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(master=frame, text="启动配置", font=ctk.CTkFont(size=18, weight="bold")).grid(
        row=0, column=0, padx=16, pady=(16, 10), sticky="w"
    )
    scroll = ctk.CTkScrollableFrame(master=frame, corner_radius=8)
    scroll.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
    try:
        scroll.grid_columnconfigure(0, weight=1)  # type: ignore[attr-defined]
    except Exception:
        pass
    ctk.CTkLabel(
        master=scroll,
        text="说明：是否执行由“预设流程”决定；这里仅设置流程步骤需要的参数。",
        anchor="w",
        justify="left",
        wraplength=820,
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))
    forms.make_section_title(scroll, "BetterGI（用于：BetterGI / 一条龙 步骤）").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    _path_row(
        "BetterGI 路径 (.exe)",
        var_bettergi_path,
        placeholder="例如：D:\\BetterGI\\BetterGI.exe",
        dialog_title="选择 BetterGI 可执行文件",
        filetypes=exe_filetypes,
    )
    _entry_row("一条龙配置名称（可选）", var_bettergi_onedragon_config, placeholder="例如：每日任务")
    _entry_row("第二个一条龙配置（可选）", var_bettergi_onedragon_config_2, placeholder="任务结束后切换")
    warn_label = ctk.CTkLabel(
        master=scroll,
        text="",
        anchor="w",
        justify="left",
        wraplength=820,
        text_color=("#b00020", "#ff6b6b"),
    )
    warn_label.pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))
    def _refresh_bettergi_warning() -> None:
        try:
            config_name = str(var_bettergi_onedragon_config.get() or "").strip()
            bettergi_path = str(var_bettergi_path.get() or "").strip()
            if not config_name:
                warn_label.configure(text="")
                return
            if not bettergi_path:
                warn_label.configure(
                    text="提示：已填写“一条龙配置名称”，但未设置 BetterGI.exe 路径。\n"
                    "此时无法执行指定配置名称（不会回退到 URL Scheme）。"
                )
                return
            warn_label.configure(text="")
        except Exception:
            return
    _refresh_bettergi_warning()
    try:
        var_bettergi_onedragon_config.trace_add("write", lambda *_: _refresh_bettergi_warning())
        var_bettergi_path.trace_add("write", lambda *_: _refresh_bettergi_warning())
    except Exception:
        pass
    forms.make_section_title(scroll, "外部启动器（用于：外部启动器 步骤）").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    _path_row(
        "启动器路径",
        var_external_launcher_path,
        placeholder="例如：D:\\Launcher\\launcher.exe",
        dialog_title="选择外部启动器",
        filetypes=exe_filetypes,
    )
    _entry_row("启动参数（可选）", var_external_launcher_args, placeholder="例如：--profile default")
    _entry_row("启动后等待（秒）", var_external_launcher_wait_seconds, placeholder="0~300")
    forms.make_section_title(scroll, "Mod（用于：Mod 步骤）").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    _path_row(
        "Mod 程序路径",
        var_mod_path,
        placeholder="例如：D:\\Mod\\mod.exe",
        dialog_title="选择 Mod 程序",
        filetypes=exe_filetypes,
    )
    _entry_row("启动后等待（秒）", var_mod_wait_seconds, placeholder="0~120")
    forms.make_section_title(scroll, "直接启动原神（用于：直接启动原神 步骤）").pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )
    _path_row(
        "游戏路径 (Genshin Impact.exe)",
        var_genshin_path,
        placeholder="例如：...\\Genshin Impact\\Genshin Impact.exe",
        dialog_title="选择原神可执行文件",
        filetypes=exe_filetypes,
    )
    set_suspend(True)
    try:
        pass
    finally:
        set_suspend(False)
    _ = tk
    return frame
