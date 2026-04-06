import tkinter as tk
from tkinter import simpledialog, messagebox
from account_manager import account_manager
from mihoyo_api import mihoyo_client
from cookie_login import get_cookie_auto
import threading
import datetime
from PIL import ImageTk


# ─────────────────────────────────────────────
#  Color palette  (dark + amber/gold accent)
# ─────────────────────────────────────────────
BG        = "#1a1a2e"      # deepest bg
SURFACE   = "#16213e"      # card / panel bg
SURFACE2  = "#0f3460"      # secondary surface
ACCENT    = "#e2a44a"      # gold amber
ACCENT_HV = "#f0c070"      # hover highlight
FG        = "#e8e8e8"      # primary text
FG2       = "#a0a0b0"      # secondary text
BORDER    = "#2a2a4a"      # subtle border
DANGER    = "#e05c5c"      # red
SUCCESS   = "#5cba7e"      # green

NAV_W = 200                # Sidebar width increased
WIN_W = 1920               # Initial window width
WIN_H = 1080               # Initial window height


def draw_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Helper to draw a rounded rectangle on a canvas."""
    points = [
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)


class StyledButton(tk.Canvas):
    """Modern rounded button."""
    def __init__(self, master, text, command=None, primary=False, danger=False, width=80, height=34, **kw):
        bg = kw.pop('bg', BG)
        self._width = width
        super().__init__(master, bg=bg, width=width, height=height, highlightthickness=0, cursor="hand2", **kw)
        self._main_color = ACCENT if primary else (DANGER if danger else SURFACE2)
        self._hv_color   = ACCENT_HV if primary else (DANGER + "aa" if danger else "#2a4a7a")
        self._fg         = "#111" if primary else FG
        self._cmd = command
        self._text = text
        self._width = width

        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>",  lambda e: self._draw(True))
        self.bind("<Leave>",  lambda e: self._draw(False))
        self.bind("<Button-1>", lambda e: self._on_click())

    def _draw(self, hover=False):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10: return
        color = self._hv_color if hover else self._main_color
        draw_rounded_rect(self, 0, 0, w, h, 16, fill=color)
        self.create_text(w/2, h/2, text=self._text, fill=self._fg, font=("Microsoft YaHei UI", 9, "bold"))

    def _on_click(self):
        if self._cmd: self._cmd()


class NavButton(tk.Canvas):
    """Sidebar navigation button with rounded highlight."""
    def __init__(self, master, text, command=None, **kw):
        super().__init__(master, bg=SURFACE, height=48, highlightthickness=0, cursor="hand2", **kw)
        self._cmd = command
        self._text = text
        self._active = False
        self.bind("<Enter>",  lambda e: self._draw(hover=True))
        self.bind("<Leave>",  lambda e: self._draw(hover=False))
        self.bind("<Button-1>", lambda e: self._on_click())
        self.bind("<Configure>", lambda e: self._draw())

    def set_active(self, active: bool):
        self._active = active
        self._draw()

    def _draw(self, hover=False):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10: return
        
        if self._active:
            # Rounded highlight 'pill'
            draw_rounded_rect(self, 8, 4, w-8, h-4, 18, fill=SURFACE2)
            fg = ACCENT
            font = ("Microsoft YaHei UI", 10, "bold")
        elif hover:
            draw_rounded_rect(self, 8, 4, w-8, h-4, 18, fill=BORDER)
            fg = FG
            font = ("Microsoft YaHei UI", 10)
        else:
            fg = FG2
            font = ("Microsoft YaHei UI", 10)

        self.create_text(24, h/2, text=self._text, fill=fg, font=font, anchor="w")

    def _on_click(self):
        if self._cmd: self._cmd()

class ToggleSwitch(tk.Frame):
    """Modern pill-shaped toggle switch drawn on Canvas."""
    W, H = 46, 24        # pill dimensions
    PAD  = 3             # thumb padding inside pill

    def __init__(self, master, text="", variable=None, command=None, bg=None, **kw):
        _bg = bg or BG
        super().__init__(master, bg=_bg, cursor="hand2", **kw)
        self._var = variable or tk.BooleanVar(value=False)
        self._cmd = command
        self._animating = False

        # Canvas for the pill + thumb
        self._cv = tk.Canvas(self, width=self.W, height=self.H,
                             bg=_bg, highlightthickness=0, cursor="hand2")
        self._cv.pack(side=tk.LEFT)

        # Label text next to toggle
        if text:
            tk.Label(self, text=text, bg=_bg, fg=FG,
                     font=("Microsoft YaHei UI", 10),
                     cursor="hand2").pack(side=tk.LEFT, padx=(8, 0))

        self._draw()
        # Trace variable changes (e.g. from _load_data)
        self._var.trace_add("write", lambda *_: self._draw())

        for w in self.winfo_children() + [self]:
            w.bind("<Button-1>", self._toggle)
        self._cv.bind("<Button-1>", self._toggle)

    def _draw(self):
        """Render the pill and thumb at their current (resting) state."""
        cv = self._cv
        cv.delete("all")
        on = self._var.get()
        pill_color = ACCENT if on else "#3a3a5a"
        r = self.H // 2
        # Pill background (perfect arcs)
        cv.create_arc(0, 0, self.H, self.H, start=90, extent=180, fill=pill_color, outline="")
        cv.create_arc(self.W - self.H, 0, self.W, self.H, start=270, extent=180, fill=pill_color, outline="")
        cv.create_rectangle(r, 0, self.W - r, self.H, fill=pill_color, outline="")
        # Thumb
        thumb_x = self.W - self.H + self.PAD if on else self.PAD
        d = self.H - 2 * self.PAD
        cv.create_oval(thumb_x, self.PAD, thumb_x + d, self.PAD + d,
                       fill="#ffffff", outline="")

    def _toggle(self, _=None):
        self._var.set(not self._var.get())
        if self._cmd:
            self._cmd()

    def get(self):
        return self._var.get()

    def set(self, value: bool):
        self._var.set(value)


def sep(parent, pady=8):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=pady)


def section_title(parent, text):
    tk.Label(parent, text=text, bg=BG, fg=ACCENT,
             font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", pady=(12, 4))


def label(parent, text, secondary=False):
    return tk.Label(parent, text=text, bg=BG,
                    fg=FG2 if secondary else FG,
                    font=("Microsoft YaHei UI", 9 if secondary else 10))


def entry(parent, textvariable, show="", width=40):
    # Wrapped in a frame for rounded effect simul (just border/padx)
    e = tk.Entry(parent, textvariable=textvariable, show=show,
                 bg=SURFACE, fg=FG, insertbackground=ACCENT,
                 relief=tk.FLAT, bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT,
                 font=("Microsoft YaHei UI", 10), width=width)
    return e


def browse_btn(parent, var, filetypes=None):
    if filetypes is None:
        filetypes = [("Executable Files", "*.exe;*.bat;*.cmd"), ("All Files", "*.*")]

    def _browse():
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="选择文件", filetypes=filetypes)
        if p:
            var.set(p)

    return StyledButton(parent, "浏览", command=_browse, width=60)


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
        tk.Label(topbar, text="  ✦  Genshin Impact Auto-Starter",
                 bg=SURFACE, fg=ACCENT,
                 font=("Microsoft YaHei UI", 13, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Label(topbar, text="配置工具",
                 bg=SURFACE, fg=FG2,
                 font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)

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
            ("launch",   "🚀  启动设置"),
            ("mod",      "🎮  Mod 设置"),
            ("signin",   "📋  签到设置"),
        ]
        for key, txt in nav_items:
            btn = NavButton(self.sidebar, txt, command=lambda k=key: self._navigate(k))
            btn.pack(fill=tk.X)
            self._nav_buttons[key] = btn

        # Content area
        self.content_area = tk.Frame(body, bg=BG)
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._pages = {}
        self._build_accounts_page()
        self._build_launch_page()
        self._build_mod_page()
        self._build_signin_page()

    def _navigate(self, key: str):
        for k, btn in self._nav_buttons.items():
            btn.set_active(k == key)
        for k, page in self._pages.items():
            if k == key:
                page.pack(fill=tk.BOTH, expand=True)
            else:
                page.pack_forget()
        self._current_page = key

    # ──────────────────── Page: Accounts ─────────────────────

    def _build_accounts_page(self):
        page = tk.Frame(self.content_area, bg=BG)
        self._pages["accounts"] = page

        # Title
        hdr = tk.Frame(page, bg=BG)
        hdr.pack(fill=tk.X, padx=20, pady=(16, 4))
        tk.Label(hdr, text="账号管理", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 14, "bold")).pack(side=tk.LEFT)

        body = tk.Frame(page, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        # ─ Left: account list ─
        left = tk.Frame(body, bg=SURFACE, width=170)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        left.pack_propagate(False)

        tk.Label(left, text="账号列表", bg=SURFACE, fg=FG2,
                 font=("Microsoft YaHei UI", 9)).pack(anchor="w", padx=10, pady=(10, 4))

        self.account_listbox = tk.Listbox(
            left, bg=SURFACE, fg=FG, selectbackground=SURFACE2,
            selectforeground=ACCENT, activestyle="none",
            relief=tk.FLAT, bd=0, highlightthickness=0,
            font=("Microsoft YaHei UI", 10))
        self.account_listbox.pack(fill=tk.BOTH, expand=True, padx=4)
        self.account_listbox.bind("<<ListboxSelect>>", self._on_select_account)

        btn_row = tk.Frame(left, bg=SURFACE)
        btn_row.pack(fill=tk.X, padx=6, pady=8)
        StyledButton(btn_row, "＋ 添加", command=self._add_account, primary=True).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        StyledButton(btn_row, "删除",   command=self._delete_account, danger=True).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # ─ Right: account details (scrollable) ─
        right_wrap = tk.Frame(body, bg=BG)
        right_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(right_wrap, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(right_wrap, orient="vertical", command=canvas.yview)
        self._acc_scroll_frame = tk.Frame(canvas, bg=BG)
        self._acc_scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=self._acc_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        rf = self._acc_scroll_frame

        # Account name
        section_title(rf, "账号信息")
        row = tk.Frame(rf, bg=BG)
        row.pack(fill=tk.X, pady=3)
        label(row, "备注名称:").pack(side=tk.LEFT, padx=(0, 8))
        self.var_name = tk.StringVar()
        entry(row, self.var_name, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Game Cookie
        sep(rf)
        section_title(rf, "游戏 Cookie  (原神 / 崩铁 / 绝区零)")

        cookie_ctrl = tk.Frame(rf, bg=BG)
        cookie_ctrl.pack(fill=tk.X, pady=3)
        self.var_show_cookie = tk.BooleanVar(value=False)
        ToggleSwitch(cookie_ctrl, text="显示明文", variable=self.var_show_cookie,
                     command=self._toggle_cookie_visibility).pack(side=tk.LEFT)
        StyledButton(cookie_ctrl, "自动获取", command=lambda: self._auto_get_cookie("game"), width=70).pack(side=tk.RIGHT, padx=(3, 0))
        StyledButton(cookie_ctrl, "手动填入", command=lambda: self._manual_fill_cookie("game"), width=70).pack(side=tk.RIGHT, padx=(3, 0))

        self.txt_game_cookie = tk.Text(
            rf, height=4, bg=SURFACE, fg=FG,
            insertbackground=ACCENT, relief=tk.FLAT, bd=0,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT, font=("Consolas", 9), wrap=tk.WORD)
        self.txt_game_cookie.pack(fill=tk.X, pady=4)
        self.txt_game_cookie.bind("<<Modified>>", lambda e: self._on_cookie_modified(e, "game"))

        # Miyoushe Cookie
        sep(rf)
        section_title(rf, "米游社 Cookie  (含 Stoken)")

        miy_ctrl = tk.Frame(rf, bg=BG)
        miy_ctrl.pack(fill=tk.X, pady=3)
        StyledButton(miy_ctrl, "扫码获取", command=lambda: self._auto_get_cookie("miyoushe"), width=70).pack(side=tk.RIGHT, padx=(3, 0))
        StyledButton(miy_ctrl, "手动填入", command=lambda: self._manual_fill_cookie("miyoushe"), width=70).pack(side=tk.RIGHT, padx=(3, 0))
        StyledButton(miy_ctrl, "解析填入", command=lambda: self._apply_parsed_cookie(self.current_miyoushe_cookie), width=70).pack(side=tk.RIGHT, padx=(3, 0))

        self.txt_miyoushe_cookie = tk.Text(
            rf, height=4, bg=SURFACE, fg=FG,
            insertbackground=ACCENT, relief=tk.FLAT, bd=0,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT, font=("Consolas", 9), wrap=tk.WORD)
        self.txt_miyoushe_cookie.pack(fill=tk.X, pady=4)
        self.txt_miyoushe_cookie.bind("<<Modified>>", lambda e: self._on_cookie_modified(e, "miyoushe"))

        # Detail fields
        sep(rf)
        section_title(rf, "详细参数  (解析后自动填充)")
        label(rf, "米游币签到必填", secondary=True).pack(anchor="w", pady=(0, 6))

        for lbl_text, var_attr, show in [
            ("Stuid:", "var_stuid", "*"),
            ("Stoken:", "var_stoken", "*"),
            ("Mid:", "var_mid", "*"),
        ]:
            r = tk.Frame(rf, bg=BG)
            r.pack(fill=tk.X, pady=3)
            tk.Label(r, text=lbl_text, bg=BG, fg=FG,
                     font=("Microsoft YaHei UI", 10), width=8, anchor="w").pack(side=tk.LEFT, padx=(0, 8))
            setattr(self, var_attr, tk.StringVar())
            setattr(self, f"ent_{var_attr[4:]}", entry(r, getattr(self, var_attr), show=show))
            getattr(self, f"ent_{var_attr[4:]}").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Signin toggles
        sep(rf)
        section_title(rf, "功能开关")

        self.var_genshin  = tk.BooleanVar()
        self.var_starrail = tk.BooleanVar()
        self.var_zzz      = tk.BooleanVar()
        self.var_miyoushe = tk.BooleanVar()
        self.var_bbs_read  = tk.BooleanVar()
        self.var_bbs_like  = tk.BooleanVar()
        self.var_bbs_share = tk.BooleanVar()

        checks = [
            ("启用 原神 签到",            self.var_genshin),
            ("启用 崩坏：星穹铁道 签到",  self.var_starrail),
            ("启用 绝区零 签到",          self.var_zzz),
            ("启用 米游社 签到",          self.var_miyoushe),
            ("米游社任务: 看贴",          self.var_bbs_read),
            ("米游社任务: 点赞",          self.var_bbs_like),
            ("米游社任务: 分享",          self.var_bbs_share),
        ]
        grid = tk.Frame(rf, bg=BG)
        grid.pack(fill=tk.X, pady=4)
        for i, (txt, var) in enumerate(checks):
            ToggleSwitch(grid, text=txt, variable=var).grid(
                row=i//2, column=i%2, sticky="w", padx=8, pady=6)

        sep(rf)
        save_row = tk.Frame(rf, bg=BG)
        save_row.pack(fill=tk.X, pady=(4, 16))
        StyledButton(save_row, "💾 保存设置", command=self._save_current_account, primary=True, width=110).pack(side=tk.RIGHT, padx=(8, 0))
        StyledButton(save_row, "▶ 立即签到", command=self._run_signin, width=100).pack(side=tk.RIGHT)

    # ──────────────────── Page: Launch ───────────────────────

    def _build_launch_page(self):
        page = tk.Frame(self.content_area, bg=BG)
        self._pages["launch"] = page

        tk.Label(page, text="启动设置", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w", padx=20, pady=(16, 4))

        canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(page, orient="vertical", command=canvas.yview)
        sf = tk.Frame(canvas, bg=BG)
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=8)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

        # BetterGI
        section_title(sf, "BetterGI 设置")

        row1 = tk.Frame(sf, bg=BG)
        row1.pack(fill=tk.X, pady=4)
        self.var_bettergi_enabled = tk.BooleanVar()
        ToggleSwitch(row1, text="启用 BetterGI 启动", variable=self.var_bettergi_enabled).pack(side=tk.LEFT, padx=(0, 24))
        self.var_bettergi_onedragon_enabled = tk.BooleanVar()
        ToggleSwitch(row1, text="启用一条龙模式", variable=self.var_bettergi_onedragon_enabled).pack(side=tk.LEFT)

        def _path_row(parent, lbl_text, var_attr, filetypes=None):
            r = tk.Frame(parent, bg=BG)
            r.pack(fill=tk.X, pady=4)
            label(r, lbl_text).pack(side=tk.LEFT, padx=(0, 8))
            setattr(self, var_attr, tk.StringVar())
            entry(r, getattr(self, var_attr), width=36).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
            browse_btn(r, getattr(self, var_attr), filetypes=filetypes).pack(side=tk.LEFT)

        _path_row(sf, "BetterGI 路径 (.exe):", "var_bettergi_path")

        def _text_row(parent, lbl_text, var_attr):
            r = tk.Frame(parent, bg=BG)
            r.pack(fill=tk.X, pady=4)
            label(r, lbl_text).pack(side=tk.LEFT, padx=(0, 8))
            setattr(self, var_attr, tk.StringVar())
            entry(r, getattr(self, var_attr), width=36).pack(side=tk.LEFT, fill=tk.X, expand=True)

        _text_row(sf, "一条龙配置名称:", "var_bettergi_onedragon_config")
        _text_row(sf, "第二个一条龙配置:", "var_bettergi_onedragon_config_2")
        label(sf, "提示: 填写第二个配置后，将在第一个任务结束后自动切换。留空则使用 BetterGI 当前选定的配置。", secondary=True).pack(anchor="w", pady=2)

        sep(sf)

        # Direct Genshin
        section_title(sf, "直接启动原神")
        _path_row(sf, "游戏路径 (Genshin Impact.exe):", "var_genshin_path")
        label(sf, "提示: 仅在禁用 BetterGI 且未使用外置启动器时生效。", secondary=True).pack(anchor="w", pady=2)

        sep(sf)

        # External launcher
        section_title(sf, "外置启动器模式")
        self.var_external_launcher_mode = tk.BooleanVar()
        ToggleSwitch(sf, text="启用外置启动器", variable=self.var_external_launcher_mode).pack(anchor="w", pady=4)
        _path_row(sf, "外置启动器路径:", "var_external_launcher_path")

        ext_r = tk.Frame(sf, bg=BG)
        ext_r.pack(fill=tk.X, pady=4)
        label(ext_r, "启动参数:").pack(side=tk.LEFT, padx=(0, 8))
        self.var_external_launcher_args = tk.StringVar()
        entry(ext_r, self.var_external_launcher_args, width=36).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ext_wait_row = tk.Frame(sf, bg=BG)
        ext_wait_row.pack(fill=tk.X, pady=4)
        label(ext_wait_row, "启动后等待 (秒):").pack(side=tk.LEFT, padx=(0, 8))
        self.var_external_launcher_wait_seconds = tk.IntVar(value=5)
        tk.Spinbox(ext_wait_row, from_=0, to=300, textvariable=self.var_external_launcher_wait_seconds,
                   width=8, bg=SURFACE, fg=FG, buttonbackground=SURFACE2,
                   relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER,
                   font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        label(sf, "提示: 启用后，先启动外置启动器，等待指定秒数后再继续启动 BetterGI/原神。", secondary=True).pack(anchor="w", pady=2)

        sep(sf)
        StyledButton(sf, "💾 保存启动设置", command=self._save_global_settings, primary=True, width=120).pack(anchor="e", pady=(4, 20))

        self._launch_sf = sf  # keep ref for partial path row builder

    # ──────────────────── Page: Mod ──────────────────────────

    def _build_mod_page(self):
        page = tk.Frame(self.content_area, bg=BG)
        self._pages["mod"] = page

        tk.Label(page, text="Mod 设置", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w", padx=20, pady=(16, 4))

        sf = tk.Frame(page, bg=BG)
        sf.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        section_title(sf, "Mod 启动模式")
        self.var_mod_enabled = tk.BooleanVar()
        ToggleSwitch(sf, text="启用 Mod 启动模式", variable=self.var_mod_enabled).pack(anchor="w", pady=4)

        mod_path_row = tk.Frame(sf, bg=BG)
        mod_path_row.pack(fill=tk.X, pady=4)
        label(mod_path_row, "Mod 程序路径:").pack(side=tk.LEFT, padx=(0, 8))
        self.var_mod_path = tk.StringVar()
        entry(mod_path_row, self.var_mod_path, width=36).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        browse_btn(mod_path_row, self.var_mod_path).pack(side=tk.LEFT)

        wait_row = tk.Frame(sf, bg=BG)
        wait_row.pack(fill=tk.X, pady=4)
        label(wait_row, "启动后等待 (秒):").pack(side=tk.LEFT, padx=(0, 8))
        self.var_mod_wait_seconds = tk.IntVar(value=6)
        tk.Spinbox(wait_row, from_=0, to=120, textvariable=self.var_mod_wait_seconds,
                   width=8, bg=SURFACE, fg=FG, buttonbackground=SURFACE2,
                   relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER,
                   font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)

        label(sf, "说明: 在启动其他程序前，先以 --auto-launch 参数运行该 Mod 程序，并等待指定秒数。", secondary=True).pack(anchor="w", pady=4)
        label(sf, "提示: 也可在命令行加 --mod-mode 临时启用。", secondary=True).pack(anchor="w")

        sep(sf)
        StyledButton(sf, "💾 保存 Mod 设置", command=self._save_global_settings, primary=True, width=120).pack(anchor="e", pady=(4, 20))

    # ──────────────────── Page: Signin ───────────────────────

    def _build_signin_page(self):
        page = tk.Frame(self.content_area, bg=BG)
        self._pages["signin"] = page

        tk.Label(page, text="签到设置", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w", padx=20, pady=(16, 4))

        sf = tk.Frame(page, bg=BG)
        sf.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        # Sign-in order
        section_title(sf, "签到顺序")
        label(sf, "按列表顺序依次执行，拖动按钮调整。", secondary=True).pack(anchor="w", pady=(0, 6))

        self.signin_item_labels = [
            ("genshin",  "原神"),
            ("starrail", "崩坏：星穹铁道"),
            ("zzz",      "绝区零"),
            ("miyoushe", "米游社"),
        ]
        self.signin_order_ids = [x[0] for x in self.signin_item_labels]

        order_frame = tk.Frame(sf, bg=BG)
        order_frame.pack(fill=tk.X, pady=4)

        self.lst_signin_order = tk.Listbox(
            order_frame, height=5, bg=SURFACE, fg=FG,
            selectbackground=SURFACE2, selectforeground=ACCENT,
            activestyle="none", relief=tk.FLAT, bd=0, highlightthickness=1,
            highlightbackground=BORDER, font=("Microsoft YaHei UI", 10))
        self.lst_signin_order.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_col = tk.Frame(order_frame, bg=BG)
        btn_col.pack(side=tk.LEFT, padx=10)
        StyledButton(btn_col, "▲ 上移",  command=lambda: self._move_signin_order(-1), width=80).pack(fill=tk.X, pady=2)
        StyledButton(btn_col, "▼ 下移",  command=lambda: self._move_signin_order(1), width=80).pack(fill=tk.X, pady=2)
        StyledButton(btn_col, "恢复默认", command=self._reset_signin_order, width=80).pack(fill=tk.X, pady=2)

        sep(sf)

        # Risk/Captcha settings
        section_title(sf, "风控设置")
        self.var_daily_signin_once        = tk.BooleanVar()
        self.var_skip_captcha_items_today = tk.BooleanVar()
        for txt, var in [
            ("每天仅在首次启动时执行自动签到", self.var_daily_signin_once),
            ("若今日已触发验证码则跳过相应项", self.var_skip_captcha_items_today),
        ]:
            ToggleSwitch(sf, text=txt, variable=var).pack(anchor="w", pady=6)

        sep(sf)
        StyledButton(sf, "💾 保存签到设置", command=self._save_global_settings, primary=True, width=120).pack(anchor="e", pady=(4, 20))

    # ──────────────────── Data Loading ───────────────────────

    def _load_data(self):
        self.accounts = account_manager.get_accounts()
        self.account_listbox.delete(0, tk.END)
        current_idx = -1
        for i, acc in enumerate(self.accounts):
            self.account_listbox.insert(tk.END, f"  {acc['name']}")
            if acc['id'] == self.current_account_id:
                current_idx = i
        if current_idx >= 0:
            self.account_listbox.selection_set(current_idx)
        elif self.accounts:
            self.account_listbox.selection_set(0)
            self._on_select_account(None)
        else:
            self._clear_account_form()

        settings = account_manager.get_settings()
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
        account_manager.update_settings(
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
        x = win.winfo_screenwidth()//2 - w//2
        y = win.winfo_screenheight()//2 - h//2
        win.geometry(f"{w}x{h}+{x}+{y}")

        status_var = tk.StringVar(value="正在生成二维码...")
        tk.Label(win, textvariable=status_var, bg=BG, fg=ACCENT,
                 font=("Microsoft YaHei UI", 10)).pack(pady=10)
        img_label = tk.Label(win, bg=BG)
        img_label.pack()

        txt = tk.Text(win, height=12, width=48, bg=SURFACE, fg=FG2,
                      relief=tk.FLAT, font=("Consolas", 9))
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
                from qr_login_handler import (
                    create_qr_session, build_qr_image_and_ascii,
                    poll_qr_login, get_stoken_by_game_token, build_miyoushe_cookie,
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
                cookie = get_cookie_auto()
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
        self.signin_order_ids[i], self.signin_order_ids[j] = (
            self.signin_order_ids[j], self.signin_order_ids[i])
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

        tk.Label(top, text="正在签到...", bg=BG, fg=ACCENT,
                 font=("Microsoft YaHei UI", 11, "bold")).pack(pady=(12, 4))

        txt_log = tk.Text(top, bg=SURFACE, fg=FG, relief=tk.FLAT,
                          font=("Microsoft YaHei UI", 9))
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
            item_labels = {"genshin": "原神", "starrail": "崩坏：星穹铁道",
                           "zzz": "绝区零", "miyoushe": "米游社"}
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
                    messagebox.showwarning("需要验证码",
                        "检测到需要验证码的任务：\n" + "\n".join(unique) +
                        "\n\n请在米游社 App/网页完成验证后重试。")
                top.after(0, notify)

        threading.Thread(target=task).start()


def main():
    root = tk.Tk()
    AutoStarterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
