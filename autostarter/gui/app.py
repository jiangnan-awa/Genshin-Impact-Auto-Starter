"""
autostarter.gui.app

从根目录 gui.py 迁移出的 GUI 主体：
- AutoStarterGUI
- main()

约束：
- 导入本模块不得创建 Tk，也不得调用 mainloop()
"""

from __future__ import annotations

import datetime
import threading
from types import SimpleNamespace

try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog
except ModuleNotFoundError:  # pragma: no cover
    # 让模块在“无 tkinter 环境”也能被 import（例如 CI / headless 环境）。
    # 注意：此时调用 main() 不会得到可用 GUI，仅用于避免导入阶段崩溃。

    class _DummyVar:
        def __init__(self, value=None):
            self._v = value

        def get(self):
            return self._v

        def set(self, v):
            self._v = v

        def trace_add(self, *_args, **_kwargs):
            return None

    class _DummyWidget:
        def __init__(self, *_args, **_kwargs):
            pass

        def pack(self, *_args, **_kwargs):
            pass

        def pack_propagate(self, *_args, **_kwargs):
            pass

        def grid(self, *_args, **_kwargs):
            pass

        def place(self, *_args, **_kwargs):
            pass

        def bind(self, *_args, **_kwargs):
            pass

        def bind_all(self, *_args, **_kwargs):
            pass

        def configure(self, *_args, **_kwargs):
            pass

        config = configure

        def insert(self, *_args, **_kwargs):
            pass

        def delete(self, *_args, **_kwargs):
            pass

        def itemconfig(self, *_args, **_kwargs):
            pass

        def create_window(self, *_args, **_kwargs):
            return 0

        def bbox(self, *_args, **_kwargs):
            return (0, 0, 0, 0)

        def yview_scroll(self, *_args, **_kwargs):
            pass

        def yview(self, *_args, **_kwargs):
            pass

        def set(self, *_args, **_kwargs):
            pass

        def selection_set(self, *_args, **_kwargs):
            pass

        def curselection(self):
            return ()

        def see(self, *_args, **_kwargs):
            pass

        def edit_modified(self, *_args, **_kwargs):
            pass

        def winfo_width(self):
            return 0

        def winfo_height(self):
            return 0

        def winfo_exists(self):
            return False

        def after(self, *_args, **_kwargs):
            pass

        def protocol(self, *_args, **_kwargs):
            pass

        def destroy(self):
            pass

        def withdraw(self):
            pass

        def title(self, *_args, **_kwargs):
            pass

        def geometry(self, *_args, **_kwargs):
            pass

        def minsize(self, *_args, **_kwargs):
            pass

        def attributes(self, *_args, **_kwargs):
            pass

        def update_idletasks(self):
            pass

        def winfo_screenwidth(self):
            return 0

        def winfo_screenheight(self):
            return 0

    class _DummyTk(_DummyWidget):
        def mainloop(self):
            pass

    tk = SimpleNamespace(
        Tk=_DummyTk,
        Toplevel=_DummyWidget,
        Frame=_DummyWidget,
        Canvas=_DummyWidget,
        Label=_DummyWidget,
        Text=_DummyWidget,
        Scrollbar=_DummyWidget,
        Listbox=_DummyWidget,
        Spinbox=_DummyWidget,
        BooleanVar=_DummyVar,
        StringVar=_DummyVar,
        IntVar=_DummyVar,
        BOTH="both",
        X="x",
        Y="y",
        LEFT="left",
        RIGHT="right",
        TOP="top",
        BOTTOM="bottom",
        END="end",
        WORD="word",
        FLAT="flat",
        NORMAL="normal",
        DISABLED="disabled",
    )

    def _unavailable(*_args, **_kwargs):
        raise RuntimeError("当前环境缺少 tkinter，无法启动 GUI。请在 Windows 或安装了 tkinter 的环境运行。")

    messagebox = SimpleNamespace(
        showwarning=_unavailable,
        showerror=_unavailable,
        showinfo=_unavailable,
        askyesno=_unavailable,
        askokcancel=_unavailable,
    )
    simpledialog = SimpleNamespace(askstring=_unavailable)

from autostarter.account_manager import account_manager
from autostarter.gui import bindings as gui_bindings
from autostarter.gui.pages.accounts import build_accounts_page, build_signin_page
from autostarter.gui.pages.launcher import build_launch_page, build_mod_page
from autostarter.gui.style import (
    ACCENT,
    BG,
    BORDER,
    FG,
    FG2,
    NAV_W,
    SURFACE,
    SURFACE2,
    WIN_H,
    WIN_W,
)
from autostarter.gui.widgets.buttons import NavButton, StyledButton
from autostarter.mihoyo_api import mihoyo_client


def _set_dpi_awareness():
    """在 Windows 下启用高 DPI 适配。

    约束：
    - 仅在 win32 下生效
    - 必须在创建 Tk() 之前调用
    - 所有调用均需 try/except 安全降级，避免在旧系统/精简环境报错
    """

    import sys

    if sys.platform != "win32":
        return

    try:
        import ctypes

        # Windows 8.1+（shcore.dll）
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            return
        except Exception:
            pass

        # Windows Vista+（user32.dll）
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        # 任何异常都不应阻止 GUI 启动
        return


class AutoStarterGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Genshin Impact Auto-Starter")
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)

        self.accounts = []
        self.current_account_id = None
        self.current_game_cookie = ""
        self.current_miyoushe_cookie = ""

        self._build_layout()
        self._load_data()
        self._navigate("accounts")

    # ──────────────────── Layout skeleton ────────────────────

    def _build_layout(self):
        # ─ Top bar ─
        topbar = tk.Frame(self.root, bg=SURFACE, height=50)
        topbar.pack(fill=tk.X, side=tk.TOP)
        topbar.pack_propagate(False)
        tk.Label(
            topbar,
            text="  ✦  Genshin Impact Auto-Starter",
            bg=SURFACE,
            fg=ACCENT,
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=10)
        tk.Label(topbar, text="配置工具", bg=SURFACE, fg=FG2, font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)

        # ─ Body ─
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self.sidebar = tk.Frame(body, bg=SURFACE, width=NAV_W)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill=tk.X)

        self._nav_buttons = {}
        nav_items = [
            ("accounts", "👤  账号管理"),
            ("launch", "🚀  启动设置"),
            ("mod", "🎮  Mod 设置"),
            ("signin", "📋  签到设置"),
        ]
        for key, txt in nav_items:
            btn = NavButton(self.sidebar, txt, command=lambda k=key: self._navigate(k))
            btn.pack(fill=tk.X)
            self._nav_buttons[key] = btn

        # Content area
        self.content_area = tk.Frame(body, bg=BG)
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._pages = {}
        build_accounts_page(self)
        build_launch_page(self)
        build_mod_page(self)
        build_signin_page(self)

    def _navigate(self, key: str):
        for k, btn in self._nav_buttons.items():
            btn.set_active(k == key)
        for k, page in self._pages.items():
            if k == key:
                page.pack(fill=tk.BOTH, expand=True)
            else:
                page.pack_forget()
        self._current_page = key

    # ──────────────────── Data Loading ───────────────────────

    def _load_data(self):
        self.accounts = gui_bindings.load_accounts()
        self.account_listbox.delete(0, tk.END)
        current_idx = -1
        for i, acc in enumerate(self.accounts):
            self.account_listbox.insert(tk.END, f"  {acc['name']}")
            if acc["id"] == self.current_account_id:
                current_idx = i
        if current_idx >= 0:
            self.account_listbox.selection_set(current_idx)
        elif self.accounts:
            self.account_listbox.selection_set(0)
            self._on_select_account(None)
        else:
            self._clear_account_form()

        settings = gui_bindings.load_settings()
        self.var_bettergi_enabled.set(settings.get("bettergi_enabled", True))
        self.var_bettergi_path.set(settings.get("bettergi_path", ""))
        self.var_bettergi_onedragon_enabled.set(settings.get("bettergi_onedragon_enabled", False))
        self.var_bettergi_onedragon_config.set(settings.get("bettergi_onedragon_config", ""))
        self.var_bettergi_onedragon_config_2.set(settings.get("bettergi_onedragon_config_2", ""))
        self.var_genshin_path.set(settings.get("genshin_path", ""))
        self.var_external_launcher_mode.set(settings.get("external_launcher_mode", False))
        self.var_external_launcher_path.set(settings.get("external_launcher_path", ""))
        self.var_external_launcher_args.set(settings.get("external_launcher_args", ""))
        try:
            self.var_external_launcher_wait_seconds.set(int(settings.get("external_launcher_wait_seconds", 5)))
        except Exception:
            self.var_external_launcher_wait_seconds.set(5)
        self.var_mod_enabled.set(settings.get("mod_enabled", False))
        self.var_mod_path.set(settings.get("mod_path", ""))
        try:
            self.var_mod_wait_seconds.set(int(settings.get("mod_wait_seconds", 6)))
        except Exception:
            self.var_mod_wait_seconds.set(6)
        self.var_daily_signin_once.set(settings.get("daily_signin_once", True))
        self.var_skip_captcha_items_today.set(settings.get("skip_captcha_items_today", True))

        order = settings.get("signin_order") or [x[0] for x in self.signin_item_labels]
        valid = {x[0] for x in self.signin_item_labels}
        order = [x for x in order if x in valid]
        if len(order) != len(self.signin_item_labels):
            order = [x[0] for x in self.signin_item_labels]
        self.signin_order_ids = order
        self._refresh_signin_order_listbox()

    def _clear_account_form(self):
        self.current_account_id = None
        self.current_game_cookie = ""
        self.current_miyoushe_cookie = ""
        self.var_name.set("")
        for w in (self.txt_game_cookie, self.txt_miyoushe_cookie):
            w.configure(state=tk.NORMAL)
            w.delete("1.0", tk.END)
        self.var_stuid.set("")
        self.var_stoken.set("")
        self.var_mid.set("")

    # ──────────────────── Save ───────────────────────────────

    def _save_global_settings(self):
        try:
            mws = max(0, int(self.var_mod_wait_seconds.get()))
        except Exception:
            mws = 6
        gui_bindings.save_settings(
            bettergi_enabled=self.var_bettergi_enabled.get(),
            bettergi_path=self.var_bettergi_path.get(),
            bettergi_onedragon_enabled=self.var_bettergi_onedragon_enabled.get(),
            bettergi_onedragon_config=self.var_bettergi_onedragon_config.get(),
            bettergi_onedragon_config_2=self.var_bettergi_onedragon_config_2.get(),
            genshin_path=self.var_genshin_path.get(),
            external_launcher_mode=self.var_external_launcher_mode.get(),
            external_launcher_path=self.var_external_launcher_path.get(),
            external_launcher_args=self.var_external_launcher_args.get(),
            external_launcher_wait_seconds=max(0, int(self.var_external_launcher_wait_seconds.get())),
            mod_enabled=self.var_mod_enabled.get(),
            mod_path=self.var_mod_path.get(),
            mod_wait_seconds=mws,
            signin_order=self.signin_order_ids,
            daily_signin_once=self.var_daily_signin_once.get(),
            skip_captcha_items_today=self.var_skip_captcha_items_today.get(),
        )
        messagebox.showinfo("成功", "设置保存成功")

    # ──────────────────── Account actions ────────────────────

    def _on_select_account(self, event):
        sel = self.account_listbox.curselection()
        if not sel:
            return
        acc = self.accounts[sel[0]]
        self.current_account_id = acc["id"]
        self.var_name.set(acc["name"])
        self.current_game_cookie = acc.get("game_cookie", "") or acc.get("cookie", "")
        self.current_miyoushe_cookie = acc.get("miyoushe_cookie", "") or acc.get("cookie", "")
        self.var_stuid.set(acc.get("stuid", ""))
        self.var_stoken.set(acc.get("stoken", ""))
        self.var_mid.set(acc.get("mid", ""))
        self.var_show_cookie.set(False)
        self._update_cookie_display()
        self.var_genshin.set(acc.get("enable_genshin", True))
        self.var_starrail.set(acc.get("enable_starrail", True))
        self.var_zzz.set(acc.get("enable_zzz", True))
        self.var_miyoushe.set(acc.get("enable_miyoushe", True))
        self.var_bbs_read.set(acc.get("enable_bbs_read", True))
        self.var_bbs_like.set(acc.get("enable_bbs_like", True))
        self.var_bbs_share.set(acc.get("enable_bbs_share", True))

    def _add_account(self):
        name = simpledialog.askstring("新建账号", "请输入账号备注名:")
        if name:
            if account_manager.add_account(name):
                self._load_data()
                self.account_listbox.selection_clear(0, tk.END)
                self.account_listbox.selection_set(tk.END)
                self._on_select_account(None)
            else:
                messagebox.showerror("错误", "创建账号失败")

    def _delete_account(self):
        if not self.current_account_id:
            return
        if messagebox.askyesno("确认", "确定要删除该账号吗？"):
            account_manager.delete_account(self.current_account_id)
            self.current_account_id = None
            self._load_data()

    def _save_current_account(self):
        if not self.current_account_id:
            return
        if self.var_show_cookie.get():
            self.current_game_cookie = self.txt_game_cookie.get("1.0", tk.END).strip()
            self.current_miyoushe_cookie = self.txt_miyoushe_cookie.get("1.0", tk.END).strip()
        account_manager.update_account(
            self.current_account_id,
            name=self.var_name.get(),
            game_cookie=self.current_game_cookie,
            miyoushe_cookie=self.current_miyoushe_cookie,
            stuid=self.var_stuid.get(),
            stoken=self.var_stoken.get(),
            mid=self.var_mid.get(),
            enable_genshin=self.var_genshin.get(),
            enable_starrail=self.var_starrail.get(),
            enable_zzz=self.var_zzz.get(),
            enable_miyoushe=self.var_miyoushe.get(),
            enable_bbs_read=self.var_bbs_read.get(),
            enable_bbs_like=self.var_bbs_like.get(),
            enable_bbs_share=self.var_bbs_share.get(),
        )
        messagebox.showinfo("成功", "保存成功")
        self._load_data()
        self._on_select_account(None)

    # ──────────────────── Cookie helpers ─────────────────────

    def _toggle_cookie_visibility(self):
        self._update_cookie_display()

    def _update_cookie_display(self):
        show = self.var_show_cookie.get()
        for txt, cookie in [
            (self.txt_game_cookie, self.current_game_cookie),
            (self.txt_miyoushe_cookie, self.current_miyoushe_cookie),
        ]:
            txt.configure(state=tk.NORMAL)
            txt.delete("1.0", tk.END)
            if show:
                txt.insert("1.0", cookie)
            else:
                txt.insert("1.0", "●●●●●●●● (已隐藏)" if cookie else "")
                txt.configure(state=tk.DISABLED)

        show_str = "" if show else "*"
        self.ent_stuid.configure(show=show_str)
        self.ent_stoken.configure(show=show_str)
        self.ent_mid.configure(show=show_str)

    def _on_cookie_modified(self, event, cookie_type):
        txt = self.txt_game_cookie if cookie_type == "game" else self.txt_miyoushe_cookie
        if txt.edit_modified():
            if self.var_show_cookie.get():
                val = txt.get("1.0", tk.END).strip()
                if cookie_type == "game":
                    self.current_game_cookie = val
                else:
                    self.current_miyoushe_cookie = val
            txt.edit_modified(False)

    def _auto_get_cookie(self, cookie_type="game"):
        if not self.current_account_id:
            messagebox.showwarning("提示", "请先选择或创建一个账号！")
            return
        if cookie_type == "miyoushe":
            self._get_cookie_from_qr(cookie_type)
        else:
            self._get_cookie_from_web(cookie_type)

    def _get_cookie_from_qr(self, cookie_type):
        win = tk.Toplevel(self.root)
        win.title("扫码获取 stoken")
        win.geometry("420x560")
        win.configure(bg=BG)
        win.attributes("-topmost", True)
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x = win.winfo_screenwidth() // 2 - w // 2
        y = win.winfo_screenheight() // 2 - h // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        status_var = tk.StringVar(value="正在生成二维码...")
        tk.Label(win, textvariable=status_var, bg=BG, fg=ACCENT, font=("Microsoft YaHei UI", 10)).pack(pady=10)
        img_label = tk.Label(win, bg=BG)
        img_label.pack()

        txt = tk.Text(win, height=12, width=48, bg=SURFACE, fg=FG2, relief=tk.FLAT, font=("Consolas", 9))
        txt.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        txt.insert("1.0", "请使用米游社 App 扫码并确认登录。\n\n")
        txt.configure(state=tk.DISABLED)

        holder = {"photo": None}

        def close():
            if win.winfo_exists():
                win.destroy()

        StyledButton(win, "取消", command=close).pack(pady=8)

        def task():
            try:
                from PIL import ImageTk

                # 注意：修正导入路径（与根目录 gui.py 不同）
                from autostarter.qr_login_handler import (
                    build_miyoushe_cookie,
                    build_qr_image_and_ascii,
                    create_qr_session,
                    get_stoken_by_game_token,
                    poll_qr_login,
                )

                qr_url, app_id, ticket, device = create_qr_session()
                image, ascii_qr = build_qr_image_and_ascii(qr_url)
                image = image.resize((300, 300))

                def set_qr():
                    if not win.winfo_exists():
                        return
                    photo = ImageTk.PhotoImage(image)
                    holder["photo"] = photo
                    img_label.configure(image=photo)
                    txt.configure(state=tk.NORMAL)
                    txt.insert(tk.END, ascii_qr)
                    txt.see(tk.END)
                    txt.configure(state=tk.DISABLED)
                    status_var.set("等待扫码")

                self.root.after(0, set_qr)

                def on_status(s):
                    self.root.after(0, lambda: status_var.set(s) if win.winfo_exists() else None)

                uid, game_token = poll_qr_login(app_id, ticket, device, status_callback=on_status)
                mid, stoken = get_stoken_by_game_token(uid, game_token)
                cookie_str = build_miyoushe_cookie(uid, mid, stoken)
                self.root.after(0, lambda: (close(), self._on_auto_cookie_success(cookie_str, cookie_type)))
            except Exception as e:
                err = str(e)
                self.root.after(0, lambda: (close(), messagebox.showerror("失败", f"扫码获取失败: {err}")))

        threading.Thread(target=task, daemon=True).start()

    def _get_cookie_from_web(self, cookie_type):
        if not messagebox.askokcancel("提示", "即将打开浏览器获取国服 Cookie。\n请确保已安装 Chrome 浏览器。\n点击确定开始..."):
            return

        def task():
            try:
                cookie = gui_bindings.auto_get_cookie()
                if cookie:
                    self.root.after(0, lambda: self._on_auto_cookie_success(cookie, cookie_type))
                else:
                    messagebox.showwarning("失败", "未能获取 Cookie")
            except Exception as e:
                messagebox.showerror("错误", f"获取过程中出错: {e}")

        threading.Thread(target=task).start()

    def _on_auto_cookie_success(self, cookie, cookie_type):
        if cookie_type == "game":
            self.current_game_cookie = cookie
        else:
            self.current_miyoushe_cookie = cookie
        self.var_show_cookie.set(True)
        self._update_cookie_display()
        self._apply_parsed_cookie(cookie, silent=True)
        if messagebox.askyesno("成功", "Cookie 获取成功！是否立即保存？"):
            self._save_current_account()

    def _manual_fill_cookie(self, cookie_type="game"):
        title = "手动填入游戏 Cookie" if cookie_type == "game" else "手动填入含 Stoken 的 Cookie"
        s = simpledialog.askstring(title, "请粘贴完整的 Cookie 内容:")
        if s:
            s = s.strip()
            if cookie_type == "game":
                self.current_game_cookie = s
            else:
                self.current_miyoushe_cookie = s
            self.var_show_cookie.set(True)
            self._update_cookie_display()
            if cookie_type == "miyoushe":
                self._apply_parsed_cookie(s)

    def _apply_parsed_cookie(self, cookie_str, silent=False):
        if not cookie_str:
            if not silent:
                messagebox.showwarning("解析失败", "Cookie 内容为空")
            return
        fields = account_manager.parse_cookie(cookie_str)
        if not fields:
            if not silent:
                messagebox.showwarning("解析失败", "未能从提供的字符串中解析出有效信息。")
            return
        if "stuid" in fields:
            self.var_stuid.set(fields["stuid"])
        if "stoken" in fields:
            self.var_stoken.set(fields["stoken"])
        if "mid" in fields:
            self.var_mid.set(fields["mid"])
        if (("ltoken" in fields) or ("cookie_token" in fields)) and not self.current_game_cookie:
            self.current_game_cookie = cookie_str
            self.var_show_cookie.set(True)
            self._update_cookie_display()
        if cookie_str and len(cookie_str) > 10 and not self.current_miyoushe_cookie:
            self.current_miyoushe_cookie = cookie_str
            self.var_show_cookie.set(True)
            self._update_cookie_display()
        if not silent:
            messagebox.showinfo("解析成功", f"已填入字段：{', '.join(fields.keys())}")

    # ──────────────────── Signin order ───────────────────────

    def _refresh_signin_order_listbox(self):
        mapping = dict(self.signin_item_labels)
        self.lst_signin_order.delete(0, tk.END)
        for item in self.signin_order_ids:
            self.lst_signin_order.insert(tk.END, f"  {mapping.get(item, item)}")

    def _move_signin_order(self, delta):
        sel = self.lst_signin_order.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= len(self.signin_order_ids):
            return
        self.signin_order_ids[i], self.signin_order_ids[j] = (self.signin_order_ids[j], self.signin_order_ids[i])
        self._refresh_signin_order_listbox()
        self.lst_signin_order.selection_set(j)

    def _reset_signin_order(self):
        self.signin_order_ids = [x[0] for x in self.signin_item_labels]
        self._refresh_signin_order_listbox()

    # ──────────────────── Run signin ─────────────────────────

    def _run_signin(self):
        top = tk.Toplevel(self.root)
        top.title("签到进度")
        top.geometry("460x340")
        top.configure(bg=BG)

        tk.Label(top, text="正在签到...", bg=BG, fg=ACCENT, font=("Microsoft YaHei UI", 11, "bold")).pack(
            pady=(12, 4)
        )

        txt_log = tk.Text(top, bg=SURFACE, fg=FG, relief=tk.FLAT, font=("Microsoft YaHei UI", 9))
        txt_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        def log(msg):
            txt_log.insert(tk.END, msg + "\n")
            txt_log.see(tk.END)

        def task():
            accounts = account_manager.get_accounts()
            if not accounts:
                log("没有配置账号！")
                return
            settings = account_manager.get_settings()
            order = settings.get("signin_order") or ["genshin", "starrail", "zzz", "miyoushe"]
            item_labels = {"genshin": "原神", "starrail": "崩坏：星穹铁道", "zzz": "绝区零", "miyoushe": "米游社"}
            captcha_hits = []
            for item in order:
                log(f"== {item_labels.get(item, item)} ==")
                for acc in accounts:
                    log(f"正在处理: {acc['name']}...")
                    results = mihoyo_client.sign_in_item(acc, item)
                    joined = "\n".join(results) if isinstance(results, list) else str(results)
                    if "验证码" in joined or "触发验证码" in joined:
                        captcha_hits.append((acc.get("name", ""), item_labels.get(item, item)))
                    for r in (results if isinstance(results, list) else [results]):
                        log(f"  {r}")
                log("-" * 20)
            account_manager.update_settings(last_signin_date=datetime.date.today().isoformat())
            log("执行完毕！")
            if captcha_hits:

                def notify():
                    unique, seen = [], set()
                    for name, lbl in captcha_hits:
                        if (name, lbl) not in seen:
                            seen.add((name, lbl))
                            unique.append(f"{name} - {lbl}")
                    messagebox.showwarning("需要验证码", "检测到需要验证码的任务：\n" + "\n".join(unique) + "\n\n请在米游社 App/网页完成验证后重试。")

                top.after(0, notify)

        threading.Thread(target=task).start()


def main():
    _set_dpi_awareness()
    root = tk.Tk()
    AutoStarterGUI(root)
    root.mainloop()


__all__ = ["AutoStarterGUI", "main", "_set_dpi_awareness"]
