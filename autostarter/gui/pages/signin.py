from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from ..state import AppState
def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法创建 Signin 页面") from e
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
    suspend_events: Dict[str, bool] = {"all": False}
    def set_suspend(flag: bool) -> None:
        suspend_events["all"] = bool(flag)
    def is_suspended() -> bool:
        return bool(suspend_events["all"])
    signin_items: List[tuple[str, str]] = [
        ("genshin", "原神"),
        ("starrail", "崩坏：星穹铁道"),
        ("zzz", "绝区零"),
        ("miyoushe", "米游社"),
    ]
    default_order = [x[0] for x in signin_items]
    valid = {x[0] for x in signin_items}
    order_ids = settings.get("signin_order") or default_order
    if not isinstance(order_ids, list):
        order_ids = default_order
    order_ids = [str(x) for x in order_ids if str(x) in valid]
    if len(order_ids) != len(default_order):
        order_ids = default_order[:]
    selected: Dict[str, str] = {"id": order_ids[0] if order_ids else ""}
    var_daily_signin_once = tk.BooleanVar(value=bool(settings.get("daily_signin_once", True)))
    var_skip_captcha_items_today = tk.BooleanVar(value=bool(settings.get("skip_captcha_items_today", True)))
    last_signin_date = str(settings.get("last_signin_date", "") or "")
    def _save_now() -> None:
        payload = {
            "signin_order": list(order_ids),
            "daily_signin_once": bool(var_daily_signin_once.get()),
            "skip_captcha_items_today": bool(var_skip_captcha_items_today.get()),
        }
        try:
            b.update_settings(**payload)
            toast("已自动保存签到设置")
        except Exception as e:  # pragma: no cover
            toast(f"保存失败：{e}")
    deb_save = Debouncer(0.6, _save_now)
    def trigger_save() -> None:
        if is_suspended():
            return
        deb_save.trigger()
    frame = ctk.CTkFrame(master=parent, corner_radius=0)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(master=frame, text="签到设置", font=ctk.CTkFont(size=18, weight="bold")).grid(
        row=0, column=0, padx=16, pady=(16, 10), sticky="w"
    )
    scroll = ctk.CTkScrollableFrame(master=frame, corner_radius=8)
    scroll.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
    forms.make_section_title(scroll, "执行顺序").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    ctk.CTkLabel(
        master=scroll,
        text="提示：按顺序依次对所有账号执行。你可以选中一项后上移/下移。",
        anchor="w",
        justify="left",
        wraplength=780,
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    list_wrap = ctk.CTkFrame(master=scroll, corner_radius=8)
    list_wrap.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
    list_frame = ctk.CTkFrame(master=list_wrap, fg_color="transparent")
    list_frame.pack(fill="x", padx=10, pady=10)
    id2label = {k: v for k, v in signin_items}
    order_buttons: Dict[str, Any] = {}
    def _refresh_order_highlight() -> None:
        for iid, btn in list(order_buttons.items()):
            try:
                if iid == selected.get("id"):
                    btn.configure(fg_color=("gray75", "gray25"))  # type: ignore[attr-defined]
                else:
                    btn.configure(fg_color="transparent")  # type: ignore[attr-defined]
            except Exception:
                pass
    def render_order_list() -> None:
        for child in getattr(list_frame, "winfo_children", lambda: [])():
            try:
                child.destroy()
            except Exception:
                pass
        order_buttons.clear()
        for i, iid in enumerate(order_ids):
            text = f"{i+1}. {id2label.get(iid, iid)}"
            def _mk_cmd(x=iid):
                return lambda: (selected.__setitem__("id", x), _refresh_order_highlight())
            btn = forms.make_button(list_frame, text, command=_mk_cmd(), anchor="w")
            btn.pack(fill="x", pady=4)
            order_buttons[iid] = btn
        _refresh_order_highlight()
    def _move_selected(delta: int) -> None:
        iid = selected.get("id") or ""
        if not iid or iid not in order_ids:
            return
        i = order_ids.index(iid)
        j = i + int(delta)
        if j < 0 or j >= len(order_ids):
            return
        order_ids[i], order_ids[j] = order_ids[j], order_ids[i]
        render_order_list()
        trigger_save()
    def _reset_default() -> None:
        order_ids[:] = default_order[:]
        selected["id"] = order_ids[0] if order_ids else ""
        render_order_list()
        trigger_save()
    btn_row = ctk.CTkFrame(master=scroll, fg_color="transparent")
    btn_row.pack(fill="x", pady=(0, forms.SECTION_GAP_Y))
    btn_row.grid_columnconfigure(0, weight=1)
    btn_row.grid_columnconfigure(1, weight=1)
    btn_row.grid_columnconfigure(2, weight=1)
    forms.make_button(btn_row, "▲ 上移", command=lambda: _move_selected(-1)).grid(
        row=0, column=0, padx=(0, 8), sticky="ew"
    )
    forms.make_button(btn_row, "▼ 下移", command=lambda: _move_selected(1)).grid(
        row=0, column=1, padx=(0, 8), sticky="ew"
    )
    forms.make_button(btn_row, "恢复默认", command=_reset_default).grid(row=0, column=2, sticky="ew")
    forms.make_section_title(scroll, "策略").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    forms.make_switch(
        scroll, "每天仅在首次启动时执行自动签到", variable=var_daily_signin_once, command=trigger_save
    ).pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    forms.make_switch(
        scroll, "若今日已触发验证码则跳过相应项", variable=var_skip_captcha_items_today, command=trigger_save
    ).pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))
    forms.make_section_title(scroll, "状态").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    ctk.CTkLabel(
        master=scroll,
        text=f"上次签到日期：{last_signin_date or '（无）'}",
        anchor="w",
        justify="left",
        wraplength=780,
    ).pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))
    set_suspend(True)
    try:
        render_order_list()
    finally:
        set_suspend(False)
    return frame
