"""
Accounts page (GUI v2): 账号管理页（GUI v2）。

目标：
- 左侧：账号列表（新增/删除/选择）
- 右侧：Tabview（基本信息 / Cookie / 功能开关 / 高级）
  - 每个 tab 内使用 CTkScrollableFrame 保证滚轮可滚动
- 自动保存：输入/开关变更 -> Debouncer 防抖保存到 account_manager.update_account / update_settings
- Cookie tab：
  - 手动填入
  - 显示明文切换
  - 解析填入（parse_cookie -> stuid/stoken/mid）
  - 自动获取游戏 cookie（bindings）
  - 扫码获取米游社 cookie（qr_login_handler，后台线程 + 状态窗口）

约束：
- 导入无副作用：不在 import 阶段创建 GUI、不启动线程
- tests.test_gui_v2_imports 与 compileall 通过（不要求运行 GUI）
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from ..state import AppState


def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法创建 Accounts 页面") from e
    return ctk


def build_page(parent: object, state: Optional[AppState] = None) -> object:
    ctk = _import_customtkinter()
    import threading
    import tkinter as tk
    from tkinter import messagebox

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

    # ───────────────────────── Data model ─────────────────────────
    accounts: List[Dict[str, Any]] = []
    settings: Dict[str, Any] = {}
    selected_id: Optional[str] = None

    # cookie 明文缓存（避免在“隐藏模式”把明文直接放进 textbox）
    cookie_plain: Dict[str, str] = {"game": "", "miyoushe": ""}

    # UI 事件屏蔽：切换账号/批量刷新控件时，避免触发 autosave
    suspend_events: Dict[str, bool] = {"all": False}

    def set_suspend(flag: bool) -> None:
        suspend_events["all"] = bool(flag)

    def is_suspended() -> bool:
        return bool(suspend_events["all"])

    # ───────────────────────── Autosave ─────────────────────────
    def _gather_account_payload() -> Tuple[Optional[str], Dict[str, Any]]:
        if not selected_id:
            return None, {}
        payload: Dict[str, Any] = {
            "name": ent_name.get().strip(),
            "game_cookie": cookie_plain["game"].strip(),
            "miyoushe_cookie": cookie_plain["miyoushe"].strip(),
            "stuid": ent_stuid.get().strip(),
            "stoken": ent_stoken.get().strip(),
            "mid": ent_mid.get().strip(),
            "enable_genshin": bool(var_enable_genshin.get()),
            "enable_starrail": bool(var_enable_starrail.get()),
            "enable_zzz": bool(var_enable_zzz.get()),
            "enable_miyoushe": bool(var_enable_miyoushe.get()),
            "enable_bbs_read": bool(var_enable_bbs_read.get()),
            "enable_bbs_like": bool(var_enable_bbs_like.get()),
            "enable_bbs_share": bool(var_enable_bbs_share.get()),
        }
        return selected_id, payload

    def _save_account_now() -> None:
        acc_id, payload = _gather_account_payload()
        if not acc_id:
            return
        try:
            ok = b.update_account(acc_id, **payload)
            if ok:
                toast("已自动保存账号")
        except Exception as e:  # pragma: no cover
            toast(f"保存失败：{e}")

    def _save_settings_now() -> None:
        try:
            b.update_settings(
                gui_v2_show_cookie_plain=bool(var_show_plain.get()),
                gui_v2_last_selected_account_id=selected_id or "",
            )
        except Exception:
            return

    deb_save_account = Debouncer(0.6, _save_account_now)
    deb_save_settings = Debouncer(0.6, _save_settings_now)

    def trigger_save_account() -> None:
        if is_suspended():
            return
        deb_save_account.trigger()

    def trigger_save_settings() -> None:
        if is_suspended():
            return
        deb_save_settings.trigger()

    # ───────────────────────── UI helpers ─────────────────────────
    def _mask_text(val: str) -> str:
        if not val:
            return ""
        return f"（已隐藏，长度 {len(val)}）"

    def _set_textbox(tb: Any, text: str, *, editable: bool) -> None:
        try:
            tb.configure(state="normal")
            tb.delete("1.0", "end")
            tb.insert("1.0", text)
            if not editable:
                tb.configure(state="disabled")
        except Exception:
            return

    def _bind_textbox_change(tb: Any, on_change: Callable[[], None]) -> None:
        # CTkTextbox 内部是 tkinter.Text；不同版本事件略有差异，这里用最通用的 KeyRelease / FocusOut
        for ev in ("<KeyRelease>", "<FocusOut>"):
            try:
                tb.bind(ev, lambda _e=None: on_change())
            except Exception:
                pass

    def _refresh_cookie_visibility() -> None:
        # 刷新显示模式时避免触发 autosave（某些 Tk/Text 实现可能会触发事件）
        prev = is_suspended()
        set_suspend(True)
        try:
            show_plain = bool(var_show_plain.get())

            # 1) cookie textbox
            if show_plain:
                _set_textbox(txt_game_cookie, cookie_plain["game"], editable=True)
                _set_textbox(txt_miyoushe_cookie, cookie_plain["miyoushe"], editable=True)
            else:
                _set_textbox(txt_game_cookie, _mask_text(cookie_plain["game"]), editable=False)
                _set_textbox(txt_miyoushe_cookie, _mask_text(cookie_plain["miyoushe"]), editable=False)

            # 2) stoken/mid 之类敏感字段的显示模式
            try:
                ent_stoken.configure(show="" if show_plain else "*")
                ent_mid.configure(show="" if show_plain else "*")
            except Exception:
                pass
        finally:
            set_suspend(prev)

    def _open_manual_cookie_dialog(kind: str) -> None:
        title = "手动填入 Cookie" if kind in ("game", "miyoushe") else "手动填入"
        win = ctk.CTkToplevel()
        try:
            win.title(title)
            win.geometry("760x360")
            win.transient(frame)
            win.grab_set()
        except Exception:
            pass

        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(master=win, text=title, font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=14, pady=(14, 8), sticky="w"
        )
        tb = ctk.CTkTextbox(master=win)
        tb.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="nsew")
        try:
            tb.insert("1.0", cookie_plain.get(kind, ""))
        except Exception:
            pass

        btn_row = ctk.CTkFrame(master=win, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=0)
        btn_row.grid_columnconfigure(2, weight=0)

        def _apply_and_close():
            try:
                val = tb.get("1.0", "end").strip()
            except Exception:
                val = ""
            cookie_plain[kind] = val
            _refresh_cookie_visibility()
            trigger_save_account()
            try:
                win.destroy()
            except Exception:
                pass

        forms.make_button(btn_row, "取消", command=lambda: win.destroy()).grid(
            row=0, column=1, padx=(0, 8), pady=0, sticky="e"
        )
        forms.make_button(btn_row, "应用", command=_apply_and_close).grid(row=0, column=2, padx=0, pady=0, sticky="e")

    def _run_bg_task_with_status(
        *,
        title: str,
        worker: Callable[[Callable[[str], None]], Any],
        on_success: Callable[[Any], None],
        enable_qr: bool = False,
    ) -> None:
        """
        后台线程 + 状态窗口（占位式实现，避免阻塞 GUI 主线程）。
        worker: 接收 status_callback，并返回结果
        """
        win = ctk.CTkToplevel()
        try:
            win.title(title)
            win.geometry("780x460")
            win.transient(frame)
            win.grab_set()
        except Exception:
            pass

        win.grid_columnconfigure(0, weight=1)
        detail_row = 3 if enable_qr else 2
        btn_row_idx = 4 if enable_qr else 3
        win.grid_rowconfigure(detail_row, weight=1)

        ctk.CTkLabel(master=win, text=title, font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=14, pady=(14, 6), sticky="w"
        )
        lbl_status = ctk.CTkLabel(master=win, text="准备中...", anchor="w")
        lbl_status.grid(row=1, column=0, padx=14, pady=(0, 8), sticky="ew")

        # 扫码登录：图片二维码区（可选）
        qr_img_label: Any = None
        qr_url_row: Any = None
        qr_url_label: Any = None
        qr_url_value: Dict[str, str] = {"url": ""}
        if enable_qr:
            qr_frame = ctk.CTkFrame(master=win, fg_color="transparent")
            qr_frame.grid(row=2, column=0, padx=14, pady=(0, 10), sticky="ew")
            qr_frame.grid_columnconfigure(0, weight=1)

            qr_img_label = ctk.CTkLabel(master=qr_frame, text="", width=260, height=260)
            qr_img_label.grid(row=0, column=0, sticky="ew")

            qr_url_row = ctk.CTkFrame(master=qr_frame, fg_color="transparent")
            qr_url_row.grid(row=1, column=0, sticky="ew", pady=(10, 0))
            qr_url_row.grid_columnconfigure(0, weight=1)

            qr_url_label = ctk.CTkLabel(master=qr_url_row, text="", anchor="w", justify="left", wraplength=700)
            qr_url_label.grid(row=0, column=0, sticky="ew")

            def _copy_qr_url() -> None:
                url = qr_url_value.get("url", "")
                if not url:
                    return
                try:
                    win.clipboard_clear()
                    win.clipboard_append(url)
                except Exception:
                    return
                toast("已复制链接到剪贴板")

            forms.make_button(qr_url_row, "复制链接", command=_copy_qr_url).grid(
                row=0, column=1, padx=(10, 0), sticky="e"
            )
            try:
                qr_url_row.grid_remove()
            except Exception:
                pass

        tb_detail = ctk.CTkTextbox(master=win)
        tb_detail.grid(row=detail_row, column=0, padx=14, pady=(0, 10), sticky="nsew")
        _set_textbox(tb_detail, "", editable=True)

        btn_row = ctk.CTkFrame(master=win, fg_color="transparent")
        btn_row.grid(row=btn_row_idx, column=0, padx=14, pady=(0, 14), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_close = forms.make_button(btn_row, "关闭", command=lambda: win.destroy())
        btn_close.grid(row=0, column=1, padx=0, pady=0, sticky="e")

        def status_callback(msg: str) -> None:
            def _apply():
                try:
                    lbl_status.configure(text=msg)
                except Exception:
                    pass
                try:
                    tb_detail.insert("end", msg + "\n")
                    tb_detail.see("end")
                except Exception:
                    pass

            try:
                win.after(0, _apply)  # type: ignore[attr-defined]
            except Exception:
                pass

        class _StatusProxy:
            """
            兼容原 status_callback(msg) 的同时，为扫码弹窗提供：
            - set_qr_image(pil_image)
            - set_qr_url(url)
            """

            def __call__(self, msg: str) -> None:
                status_callback(msg)

            def set_qr_image(self, pil_image: Any) -> None:
                if not enable_qr or qr_img_label is None:
                    return

                def _apply():
                    try:
                        # qrcode 的 make_image() 可能返回包装对象（如 qrcode.image.pil.PilImage）
                        # 这里尽量转换为真正的 PIL.Image.Image，避免 CTkImage 渲染失败。
                        img = pil_image
                        if hasattr(img, "get_image"):
                            img = img.get_image()
                        if hasattr(img, "convert"):
                            img = img.convert("RGBA")

                        # PIL image -> CTkImage -> CTkLabel
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(260, 260))
                        qr_img_label.configure(image=ctk_img, text="")
                        # 防止被 GC 回收
                        setattr(qr_img_label, "_ctk_img_ref", ctk_img)
                    except Exception:
                        # 渲染失败时：展示链接作为兜底
                        try:
                            lbl_status.configure(text="二维码图片渲染失败，已改用链接方式（可复制链接在浏览器打开扫码）。")
                        except Exception:
                            pass
                        try:
                            # 若已存 URL，则展示出来
                            if qr_url_value.get("url"):
                                qr_url_label.configure(text=qr_url_value.get("url", ""))
                                qr_url_row.grid()
                        except Exception:
                            pass
                        return

                try:
                    win.after(0, _apply)  # type: ignore[attr-defined]
                except Exception:
                    pass

            def set_qr_url(self, url: str, show_row: bool = True) -> None:
                if not enable_qr or qr_url_row is None or qr_url_label is None:
                    return

                def _apply():
                    qr_url_value["url"] = url or ""
                    try:
                        qr_url_label.configure(text=url or "")
                    except Exception:
                        pass
                    if show_row:
                        try:
                            qr_url_row.grid()
                        except Exception:
                            return

                try:
                    win.after(0, _apply)  # type: ignore[attr-defined]
                except Exception:
                    pass

        def runner():
            try:
                # 允许特定 worker（例如扫码登录）通过 proxy 更新二维码图像/链接
                result = worker(_StatusProxy())
            except Exception as e:  # pragma: no cover
                status_callback(f"失败：{e}")
                return

            def _finish():
                try:
                    on_success(result)
                finally:
                    try:
                        win.destroy()
                    except Exception:
                        pass

            try:
                win.after(0, _finish)  # type: ignore[attr-defined]
            except Exception:
                pass

        threading.Thread(target=runner, daemon=True).start()

    # ───────────────────────── Load / Render ─────────────────────────
    def reload_data() -> None:
        nonlocal accounts, settings
        try:
            accounts = b.load_accounts()
        except Exception:
            accounts = []
        try:
            settings = b.load_settings()
        except Exception:
            settings = {}

    # ───────────────────────── UI Layout ─────────────────────────
    frame = ctk.CTkFrame(master=parent, corner_radius=0)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(master=frame, text="账号管理", font=ctk.CTkFont(size=18, weight="bold")).grid(
        row=0, column=0, padx=16, pady=(16, 10), sticky="w"
    )

    body = ctk.CTkFrame(master=frame, corner_radius=0, fg_color="transparent")
    body.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
    body.grid_rowconfigure(0, weight=1)
    body.grid_columnconfigure(0, weight=0)
    body.grid_columnconfigure(1, weight=1)

    # 左侧：账号列表
    left = ctk.CTkFrame(master=body, width=240, corner_radius=8)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    try:
        left.grid_propagate(False)
    except Exception:
        pass
    left.grid_rowconfigure(1, weight=1)
    left.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(master=left, text="账号列表", anchor="w").grid(
        row=0, column=0, padx=forms.PAD_X, pady=(forms.PAD_Y, 6), sticky="ew"
    )
    left_list = ctk.CTkScrollableFrame(master=left, corner_radius=6)
    left_list.grid(row=1, column=0, padx=forms.PAD_X, pady=(0, forms.PAD_Y), sticky="nsew")

    left_btn_row = ctk.CTkFrame(master=left, fg_color="transparent")
    left_btn_row.grid(row=2, column=0, padx=forms.PAD_X, pady=(0, forms.PAD_Y), sticky="ew")
    left_btn_row.grid_columnconfigure(0, weight=1)
    left_btn_row.grid_columnconfigure(1, weight=1)

    # 右侧：Tabview
    right = ctk.CTkFrame(master=body, corner_radius=8)
    right.grid(row=0, column=1, sticky="nsew")
    right.grid_rowconfigure(0, weight=1)
    right.grid_columnconfigure(0, weight=1)

    tabs = ctk.CTkTabview(master=right, corner_radius=8)
    tabs.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    tab_basic = tabs.add("基本信息")
    tab_cookie = tabs.add("Cookie")
    tab_toggles = tabs.add("功能开关")
    tab_adv = tabs.add("高级")

    # 每个 tab 内用 ScrollableFrame 包起来
    sf_basic = ctk.CTkScrollableFrame(master=tab_basic, corner_radius=6)
    sf_basic.pack(fill="both", expand=True, padx=10, pady=10)
    sf_cookie = ctk.CTkScrollableFrame(master=tab_cookie, corner_radius=6)
    sf_cookie.pack(fill="both", expand=True, padx=10, pady=10)
    sf_toggles = ctk.CTkScrollableFrame(master=tab_toggles, corner_radius=6)
    sf_toggles.pack(fill="both", expand=True, padx=10, pady=10)
    sf_adv = ctk.CTkScrollableFrame(master=tab_adv, corner_radius=6)
    sf_adv.pack(fill="both", expand=True, padx=10, pady=10)

    # ───────────────────────── Tab: 基本信息 ─────────────────────────
    forms.make_section_title(sf_basic, "账号信息").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))

    row_name = ctk.CTkFrame(master=sf_basic, fg_color="transparent")
    row_name.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
    row_name.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(master=row_name, text="备注名称").grid(row=0, column=0, padx=(0, 8), sticky="w")
    ent_name = forms.make_entry(row_name, placeholder="例如：主号/小号/代签到…")
    ent_name.grid(row=0, column=1, sticky="ew")

    lbl_id = ctk.CTkLabel(master=sf_basic, text="账号ID：-", anchor="w")
    lbl_id.pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))

    # ───────────────────────── Tab: Cookie ─────────────────────────
    row_cookie_top = ctk.CTkFrame(master=sf_cookie, fg_color="transparent")
    row_cookie_top.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
    row_cookie_top.grid_columnconfigure(0, weight=1)

    var_show_plain = tk.BooleanVar(value=bool(settings.get("gui_v2_show_cookie_plain", False)))
    sw_show_plain = forms.make_switch(row_cookie_top, "显示明文", variable=var_show_plain, command=trigger_save_settings)
    sw_show_plain.grid(row=0, column=0, sticky="w")

    # 游戏 cookie
    forms.make_section_title(sf_cookie, "游戏 Cookie（原神 / 崩铁 / 绝区零）").pack(
        anchor="w", pady=(forms.SECTION_GAP_Y, forms.ROW_GAP_Y)
    )
    row_game_btn = ctk.CTkFrame(master=sf_cookie, fg_color="transparent")
    row_game_btn.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
    btn_game_manual = forms.make_button(row_game_btn, "手动填入", command=lambda: _open_manual_cookie_dialog("game"))
    btn_game_manual.pack(side="right", padx=(8, 0))

    def _auto_get_game_cookie():
        def worker(status_cb: Callable[[str], None]) -> str:
            status_cb("将打开引导窗口/浏览器，请按提示完成登录…")
            return b.auto_get_game_cookie()

        def on_success(cookie_val: str) -> None:
            cookie_plain["game"] = cookie_val or ""
            _refresh_cookie_visibility()
            trigger_save_account()
            toast("已填入游戏 Cookie")

        _run_bg_task_with_status(title="自动获取游戏 Cookie", worker=worker, on_success=on_success)

    btn_game_auto = forms.make_button(row_game_btn, "自动获取", command=_auto_get_game_cookie)
    btn_game_auto.pack(side="right", padx=(8, 0))

    txt_game_cookie = ctk.CTkTextbox(master=sf_cookie, height=120)
    txt_game_cookie.pack(fill="x", pady=(0, forms.SECTION_GAP_Y))

    # 米游社 cookie
    forms.make_section_title(sf_cookie, "米游社 Cookie（含 Stoken）").pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )
    row_miy_btn = ctk.CTkFrame(master=sf_cookie, fg_color="transparent")
    row_miy_btn.pack(fill="x", pady=(0, forms.ROW_GAP_Y))

    btn_miy_manual = forms.make_button(row_miy_btn, "手动填入", command=lambda: _open_manual_cookie_dialog("miyoushe"))
    btn_miy_manual.pack(side="right", padx=(8, 0))

    def _qr_get_miyoushe_cookie():
        def worker(status_cb: Callable[[str], None]) -> Tuple[str, Dict[str, str]]:
            # 复用 qr_login_handler，且尽量展示二维码
            from autostarter import qr_login_handler as qr

            status_cb("正在创建扫码会话…")
            qr_url, app_id, ticket, device = qr.create_qr_session()
            # 先缓存 URL（默认不显示），用于图片渲染失败时兜底展示/复制
            try:
                if hasattr(status_cb, "set_qr_url"):
                    status_cb.set_qr_url(qr_url, show_row=False)  # type: ignore[attr-defined]
            except Exception:
                pass

            # 展示二维码（图片）；失败兜底展示 URL + 复制链接按钮
            try:
                pil_img, _ascii_art = qr.build_qr_image_and_ascii(qr_url)
                if hasattr(status_cb, "set_qr_image"):
                    status_cb.set_qr_image(pil_img)  # type: ignore[attr-defined]
                status_cb("请使用米游社 App 扫码…")
            except Exception:
                status_cb("无法生成二维码图片（可能缺少 qrcode/PIL），请使用链接在浏览器打开后扫码。")
                if hasattr(status_cb, "set_qr_url"):
                    status_cb.set_qr_url(qr_url, show_row=True)  # type: ignore[attr-defined]
                else:
                    status_cb(f"二维码 URL：{qr_url}")

            def inner_stat(msg: str) -> None:
                status_cb(msg)

            uid, game_token = qr.poll_qr_login(
                app_id=app_id,
                ticket=ticket,
                device=device,
                timeout_seconds=180,
                status_callback=inner_stat,
            )
            status_cb("正在换取 stoken…")
            mid, stoken = qr.get_stoken_by_game_token(uid=uid, game_token=game_token)
            cookie = qr.build_miyoushe_cookie(uid=uid, mid=mid, stoken=stoken)
            return cookie, {"stuid": str(uid), "mid": str(mid), "stoken": str(stoken)}

        def on_success(result: Tuple[str, Dict[str, str]]) -> None:
            cookie_val, parsed = result
            cookie_plain["miyoushe"] = cookie_val or ""
            try:
                ent_stuid.delete(0, "end")
                ent_stuid.insert(0, parsed.get("stuid", ""))
                ent_stoken.delete(0, "end")
                ent_stoken.insert(0, parsed.get("stoken", ""))
                ent_mid.delete(0, "end")
                ent_mid.insert(0, parsed.get("mid", ""))
            except Exception:
                pass
            _refresh_cookie_visibility()
            trigger_save_account()
            toast("已扫码获取米游社 Cookie")

        _run_bg_task_with_status(title="扫码获取米游社 Cookie", worker=worker, on_success=on_success, enable_qr=True)

    btn_miy_qr = forms.make_button(row_miy_btn, "扫码获取", command=_qr_get_miyoushe_cookie)
    btn_miy_qr.pack(side="right", padx=(8, 0))

    def _parse_fill_cookie():
        parsed = b.parse_cookie(cookie_plain.get("miyoushe", ""))
        if not parsed:
            toast("未解析到字段（请检查 Cookie）")
            return
        # 解析要求：用 parse_cookie 填 stuid/stoken/mid
        set_suspend(True)
        try:
            if parsed.get("stuid"):
                ent_stuid.delete(0, "end")
                ent_stuid.insert(0, parsed["stuid"])
            if parsed.get("stoken"):
                ent_stoken.delete(0, "end")
                ent_stoken.insert(0, parsed["stoken"])
            if parsed.get("mid"):
                ent_mid.delete(0, "end")
                ent_mid.insert(0, parsed["mid"])
        finally:
            set_suspend(False)
        trigger_save_account()
        toast("已解析并填入字段")

    btn_miy_parse = forms.make_button(row_miy_btn, "解析填入", command=_parse_fill_cookie)
    btn_miy_parse.pack(side="right", padx=(8, 0))

    txt_miyoushe_cookie = ctk.CTkTextbox(master=sf_cookie, height=120)
    txt_miyoushe_cookie.pack(fill="x", pady=(0, forms.SECTION_GAP_Y))

    # 解析字段
    forms.make_section_title(sf_cookie, "解析字段（米游币签到常用）").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    grid_fields = ctk.CTkFrame(master=sf_cookie, fg_color="transparent")
    grid_fields.pack(fill="x")
    grid_fields.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(master=grid_fields, text="Stuid").grid(row=0, column=0, padx=(0, 8), pady=(0, forms.ROW_GAP_Y))
    ent_stuid = forms.make_entry(grid_fields, placeholder="例如：123456789")
    ent_stuid.grid(row=0, column=1, sticky="ew", pady=(0, forms.ROW_GAP_Y))

    ctk.CTkLabel(master=grid_fields, text="Stoken").grid(row=1, column=0, padx=(0, 8), pady=(0, forms.ROW_GAP_Y))
    ent_stoken = forms.make_entry(grid_fields, placeholder="v2_xxx 或 xxx", show="*")
    ent_stoken.grid(row=1, column=1, sticky="ew", pady=(0, forms.ROW_GAP_Y))

    ctk.CTkLabel(master=grid_fields, text="Mid").grid(row=2, column=0, padx=(0, 8))
    ent_mid = forms.make_entry(grid_fields, placeholder="mid / mid_v2", show="*")
    ent_mid.grid(row=2, column=1, sticky="ew")

    # ───────────────────────── Tab: 功能开关 ─────────────────────────
    forms.make_section_title(sf_toggles, "签到开关").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    var_enable_genshin = tk.BooleanVar(value=True)
    var_enable_starrail = tk.BooleanVar(value=True)
    var_enable_zzz = tk.BooleanVar(value=True)
    var_enable_miyoushe = tk.BooleanVar(value=True)

    forms.make_switch(sf_toggles, "启用 原神 签到", variable=var_enable_genshin, command=trigger_save_account).pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )
    forms.make_switch(
        sf_toggles, "启用 崩坏：星穹铁道 签到", variable=var_enable_starrail, command=trigger_save_account
    ).pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    forms.make_switch(sf_toggles, "启用 绝区零 签到", variable=var_enable_zzz, command=trigger_save_account).pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )
    forms.make_switch(sf_toggles, "启用 米游社 签到", variable=var_enable_miyoushe, command=trigger_save_account).pack(
        anchor="w", pady=(0, forms.SECTION_GAP_Y)
    )

    forms.make_section_title(sf_toggles, "米游社任务").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    var_enable_bbs_read = tk.BooleanVar(value=True)
    var_enable_bbs_like = tk.BooleanVar(value=True)
    var_enable_bbs_share = tk.BooleanVar(value=True)
    forms.make_switch(sf_toggles, "看贴", variable=var_enable_bbs_read, command=trigger_save_account).pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )
    forms.make_switch(sf_toggles, "点赞", variable=var_enable_bbs_like, command=trigger_save_account).pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )
    forms.make_switch(sf_toggles, "分享", variable=var_enable_bbs_share, command=trigger_save_account).pack(
        anchor="w", pady=(0, forms.ROW_GAP_Y)
    )

    # ───────────────────────── Tab: 高级 ─────────────────────────
    forms.make_section_title(sf_adv, "高级").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
    ctk.CTkLabel(
        master=sf_adv,
        text="提示：该页主要用于查看/编辑解析字段。更多全局配置请在其他页面完成。",
        anchor="w",
        justify="left",
        wraplength=740,
    ).pack(anchor="w", pady=(0, forms.SECTION_GAP_Y))

    adv_grid = ctk.CTkFrame(master=sf_adv, fg_color="transparent")
    adv_grid.pack(fill="x")
    adv_grid.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(master=adv_grid, text="账号ID").grid(row=0, column=0, padx=(0, 8), pady=(0, forms.ROW_GAP_Y))
    ent_accid = forms.make_entry(adv_grid, placeholder="", state="disabled")
    ent_accid.grid(row=0, column=1, sticky="ew", pady=(0, forms.ROW_GAP_Y))

    # ───────────────────────── Bind events ─────────────────────────
    def on_name_change(_e=None):
        trigger_save_account()

    try:
        ent_name.bind("<KeyRelease>", on_name_change)
        ent_name.bind("<FocusOut>", on_name_change)
    except Exception:
        pass

    def _on_text_game_cookie_change():
        if not bool(var_show_plain.get()):
            return
        try:
            cookie_plain["game"] = txt_game_cookie.get("1.0", "end").strip()
        except Exception:
            cookie_plain["game"] = ""
        trigger_save_account()

    def _on_text_miy_cookie_change():
        if not bool(var_show_plain.get()):
            return
        try:
            cookie_plain["miyoushe"] = txt_miyoushe_cookie.get("1.0", "end").strip()
        except Exception:
            cookie_plain["miyoushe"] = ""
        trigger_save_account()

    _bind_textbox_change(txt_game_cookie, _on_text_game_cookie_change)
    _bind_textbox_change(txt_miyoushe_cookie, _on_text_miy_cookie_change)

    for ent in (ent_stuid, ent_stoken, ent_mid):
        try:
            ent.bind("<KeyRelease>", lambda _e=None: trigger_save_account())
            ent.bind("<FocusOut>", lambda _e=None: trigger_save_account())
        except Exception:
            pass

    def _on_toggle_plain():
        trigger_save_settings()
        _refresh_cookie_visibility()

    try:
        sw_show_plain.configure(command=_on_toggle_plain)  # type: ignore[attr-defined]
    except Exception:
        pass

    # ───────────────────────── Account list ─────────────────────────
    account_buttons: Dict[str, Any] = {}

    def render_account_list() -> None:
        # 清空
        for child in getattr(left_list, "winfo_children", lambda: [])():
            try:
                child.destroy()
            except Exception:
                pass
        account_buttons.clear()

        if not accounts:
            ctk.CTkLabel(master=left_list, text="暂无账号\n点击「新增」创建", justify="left").pack(
                anchor="w", padx=8, pady=8
            )
            return

        for acc in accounts:
            acc_id = str(acc.get("id", ""))
            name = str(acc.get("name", "未命名"))

            def _mk_cmd(aid=acc_id):
                return lambda: select_account(aid)

            btn = forms.make_button(left_list, name, command=_mk_cmd(), anchor="w")
            btn.pack(fill="x", padx=6, pady=4)
            account_buttons[acc_id] = btn

        _refresh_account_list_highlight()

    def _refresh_account_list_highlight() -> None:
        for aid, btn in list(account_buttons.items()):
            try:
                if selected_id and aid == selected_id:
                    btn.configure(fg_color=("gray75", "gray25"))  # type: ignore[attr-defined]
                else:
                    btn.configure(fg_color="transparent")  # type: ignore[attr-defined]
            except Exception:
                pass

    def _find_account(aid: str) -> Optional[Dict[str, Any]]:
        for acc in accounts:
            if str(acc.get("id", "")) == str(aid):
                return acc
        return None

    def select_account(aid: str) -> None:
        nonlocal selected_id
        acc = _find_account(aid)
        if not acc:
            return

        selected_id = str(aid)
        state.selected_account_id = selected_id
        deb_save_settings.trigger()  # 记录 last_selected（不要求立即）

        set_suspend(True)
        try:
            ent_name.delete(0, "end")
            ent_name.insert(0, str(acc.get("name", "")))
            lbl_id.configure(text=f"账号ID：{selected_id}")

            try:
                ent_accid.configure(state="normal")
                ent_accid.delete(0, "end")
                ent_accid.insert(0, selected_id)
                ent_accid.configure(state="disabled")
            except Exception:
                pass

            cookie_plain["game"] = str(acc.get("game_cookie", "") or "")
            cookie_plain["miyoushe"] = str(acc.get("miyoushe_cookie", "") or "")

            ent_stuid.delete(0, "end")
            ent_stuid.insert(0, str(acc.get("stuid", "") or ""))
            ent_stoken.delete(0, "end")
            ent_stoken.insert(0, str(acc.get("stoken", "") or ""))
            ent_mid.delete(0, "end")
            ent_mid.insert(0, str(acc.get("mid", "") or ""))

            # toggles
            var_enable_genshin.set(bool(acc.get("enable_genshin", True)))
            var_enable_starrail.set(bool(acc.get("enable_starrail", True)))
            var_enable_zzz.set(bool(acc.get("enable_zzz", True)))
            var_enable_miyoushe.set(bool(acc.get("enable_miyoushe", True)))
            var_enable_bbs_read.set(bool(acc.get("enable_bbs_read", True)))
            var_enable_bbs_like.set(bool(acc.get("enable_bbs_like", True)))
            var_enable_bbs_share.set(bool(acc.get("enable_bbs_share", True)))
        finally:
            set_suspend(False)

        _refresh_cookie_visibility()
        _refresh_account_list_highlight()

    def _add_account():
        win = ctk.CTkToplevel()
        try:
            win.title("新增账号")
            win.geometry("420x180")
            win.transient(frame)
            win.grab_set()
        except Exception:
            pass
        win.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(master=win, text="新增账号", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=14, pady=(14, 10), sticky="w"
        )
        ent = forms.make_entry(win, placeholder="备注名称")
        ent.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="ew")

        btn_row = ctk.CTkFrame(master=win, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=0)
        btn_row.grid_columnconfigure(2, weight=0)

        def _ok():
            name = ent.get().strip() or "未命名账号"
            try:
                b.add_account(name)
            except Exception as e:  # pragma: no cover
                toast(f"新增失败：{e}")
                try:
                    win.destroy()
                except Exception:
                    pass
                return

            reload_data()
            render_account_list()
            # 选中最后一个（通常是新建的）
            if accounts:
                select_account(str(accounts[-1].get("id", "")))
            toast("已新增账号")
            try:
                win.destroy()
            except Exception:
                pass

        forms.make_button(btn_row, "取消", command=lambda: win.destroy()).grid(row=0, column=1, padx=(0, 8))
        forms.make_button(btn_row, "创建", command=_ok).grid(row=0, column=2)

    def _delete_account():
        if not selected_id:
            toast("请先选择账号")
            return
        acc = _find_account(selected_id)
        name = str((acc or {}).get("name", selected_id))
        try:
            ok = messagebox.askyesno("确认删除", f"确定删除账号「{name}」吗？")
        except Exception:
            ok = True
        if not ok:
            return
        try:
            b.delete_account(selected_id)
        except Exception as e:  # pragma: no cover
            toast(f"删除失败：{e}")
            return
        reload_data()
        render_account_list()
        # 尝试选择第一个
        if accounts:
            select_account(str(accounts[0].get("id", "")))
        else:
            # 清空 UI
            nonlocal_cookie = cookie_plain
            set_suspend(True)
            try:
                ent_name.delete(0, "end")
                lbl_id.configure(text="账号ID：-")
                nonlocal_cookie["game"] = ""
                nonlocal_cookie["miyoushe"] = ""
                for entx in (ent_stuid, ent_stoken, ent_mid):
                    entx.delete(0, "end")
                try:
                    ent_accid.configure(state="normal")
                    ent_accid.delete(0, "end")
                    ent_accid.configure(state="disabled")
                except Exception:
                    pass
            finally:
                set_suspend(False)
            _refresh_cookie_visibility()
        toast("已删除账号")

    btn_add = forms.make_button(left_btn_row, "＋ 新增", command=_add_account)
    btn_add.grid(row=0, column=0, padx=(0, 6), sticky="ew")
    btn_del = forms.make_button(left_btn_row, "删除", command=_delete_account)
    btn_del.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    # 初始化数据与 UI
    reload_data()
    # 初始化 show_plain（需要 settings 先加载）
    set_suspend(True)
    try:
        var_show_plain.set(bool(settings.get("gui_v2_show_cookie_plain", False)))
    finally:
        set_suspend(False)

    render_account_list()

    # 选中：优先 state.selected_account_id -> settings last_selected -> accounts[0]
    candidate = state.selected_account_id or str(settings.get("gui_v2_last_selected_account_id", "") or "")
    if candidate and _find_account(candidate):
        select_account(candidate)
    elif accounts:
        select_account(str(accounts[0].get("id", "")))
    else:
        _refresh_cookie_visibility()

    return frame
