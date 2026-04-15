"""
autostarter.gui.pages.accounts

从根目录 gui.py 拆出的页面构建代码：
- build_accounts_page()
- build_signin_page()

约束：导入时不得创建 Tk，也不得调用 mainloop。
"""

from __future__ import annotations

from types import SimpleNamespace
try:
    import tkinter as tk
except ModuleNotFoundError:  # pragma: no cover
    class _DummyWidget:
        def __init__(self, *_args, **_kwargs):
            pass

        def pack(self, *_args, **_kwargs):
            pass

        def pack_propagate(self, *_args, **_kwargs):
            pass

        def bind(self, *_args, **_kwargs):
            pass

        def grid(self, *_args, **_kwargs):
            pass

        def configure(self, *_args, **_kwargs):
            pass

        config = configure

        def create_window(self, *_args, **_kwargs):
            return 0

        def itemconfig(self, *_args, **_kwargs):
            pass

        def bbox(self, *_args, **_kwargs):
            return (0, 0, 0, 0)

        def yview_scroll(self, *_args, **_kwargs):
            pass

        def yview(self, *_args, **_kwargs):
            pass

    tk = SimpleNamespace(  # type: ignore
        Frame=_DummyWidget,
        Canvas=_DummyWidget,
        Scrollbar=_DummyWidget,
        Listbox=_DummyWidget,
        Label=_DummyWidget,
        Text=_DummyWidget,
        BOTH="both",
        X="x",
        Y="y",
        LEFT="left",
        RIGHT="right",
        TOP="top",
        END="end",
        WORD="word",
        FLAT="flat",
    )

from autostarter.gui.style import (
    ACCENT,
    BG,
    BORDER,
    FG,
    FG2,
    SURFACE,
    SURFACE2,
    entry,
    label,
    section_title,
    sep,
)
from autostarter.gui.widgets.buttons import NavButton, StyledButton
from autostarter.gui.widgets.toggles import ToggleSwitch


def build_accounts_page(gui) -> None:
    # ──────────────────── Page: Accounts ─────────────────────
    page = tk.Frame(gui.content_area, bg=BG)
    gui._pages["accounts"] = page

    # Title
    hdr = tk.Frame(page, bg=BG)
    hdr.pack(fill=tk.X, padx=20, pady=(16, 4))
    tk.Label(hdr, text="账号管理", bg=BG, fg=FG, font=("Microsoft YaHei UI", 14, "bold")).pack(side=tk.LEFT)

    body = tk.Frame(page, bg=BG)
    body.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

    # ─ Left: account list ─
    left = tk.Frame(body, bg=SURFACE, width=170)
    left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
    left.pack_propagate(False)

    tk.Label(left, text="账号列表", bg=SURFACE, fg=FG2, font=("Microsoft YaHei UI", 9)).pack(
        anchor="w", padx=10, pady=(10, 4)
    )

    gui.account_listbox = tk.Listbox(
        left,
        bg=SURFACE,
        fg=FG,
        selectbackground=SURFACE2,
        selectforeground=ACCENT,
        activestyle="none",
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        font=("Microsoft YaHei UI", 10),
    )
    gui.account_listbox.pack(fill=tk.BOTH, expand=True, padx=4)
    gui.account_listbox.bind("<<ListboxSelect>>", gui._on_select_account)

    btn_row = tk.Frame(left, bg=SURFACE)
    btn_row.pack(fill=tk.X, padx=6, pady=8)
    StyledButton(btn_row, "＋ 添加", command=gui._add_account, primary=True).pack(
        side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3)
    )
    StyledButton(btn_row, "删除", command=gui._delete_account, danger=True).pack(side=tk.LEFT, expand=True, fill=tk.X)

    # ─ Right: account details (scrollable) ─
    right_wrap = tk.Frame(body, bg=BG)
    right_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(right_wrap, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(right_wrap, orient="vertical", command=canvas.yview)
    gui._acc_scroll_frame = tk.Frame(canvas, bg=BG)
    gui._acc_scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    cw = canvas.create_window((0, 0), window=gui._acc_scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb.pack(side=tk.RIGHT, fill=tk.Y)

    rf = gui._acc_scroll_frame

    # Account name
    section_title(rf, "账号信息")
    row = tk.Frame(rf, bg=BG)
    row.pack(fill=tk.X, pady=3)
    label(row, "备注名称:").pack(side=tk.LEFT, padx=(0, 8))
    gui.var_name = tk.StringVar()
    entry(row, gui.var_name, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Game Cookie
    sep(rf)
    section_title(rf, "游戏 Cookie  (原神 / 崩铁 / 绝区零)")

    cookie_ctrl = tk.Frame(rf, bg=BG)
    cookie_ctrl.pack(fill=tk.X, pady=3)
    gui.var_show_cookie = tk.BooleanVar(value=False)
    ToggleSwitch(cookie_ctrl, text="显示明文", variable=gui.var_show_cookie, command=gui._toggle_cookie_visibility).pack(
        side=tk.LEFT
    )
    StyledButton(cookie_ctrl, "自动获取", command=lambda: gui._auto_get_cookie("game"), width=70).pack(
        side=tk.RIGHT, padx=(3, 0)
    )
    StyledButton(cookie_ctrl, "手动填入", command=lambda: gui._manual_fill_cookie("game"), width=70).pack(
        side=tk.RIGHT, padx=(3, 0)
    )

    gui.txt_game_cookie = tk.Text(
        rf,
        height=4,
        bg=SURFACE,
        fg=FG,
        insertbackground=ACCENT,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        font=("Consolas", 9),
        wrap=tk.WORD,
    )
    gui.txt_game_cookie.pack(fill=tk.X, pady=4)
    gui.txt_game_cookie.bind("<<Modified>>", lambda e: gui._on_cookie_modified(e, "game"))

    # Miyoushe Cookie
    sep(rf)
    section_title(rf, "米游社 Cookie  (含 Stoken)")

    miy_ctrl = tk.Frame(rf, bg=BG)
    miy_ctrl.pack(fill=tk.X, pady=3)
    StyledButton(miy_ctrl, "扫码获取", command=lambda: gui._auto_get_cookie("miyoushe"), width=70).pack(
        side=tk.RIGHT, padx=(3, 0)
    )
    StyledButton(miy_ctrl, "手动填入", command=lambda: gui._manual_fill_cookie("miyoushe"), width=70).pack(
        side=tk.RIGHT, padx=(3, 0)
    )
    StyledButton(
        miy_ctrl, "解析填入", command=lambda: gui._apply_parsed_cookie(gui.current_miyoushe_cookie), width=70
    ).pack(side=tk.RIGHT, padx=(3, 0))

    gui.txt_miyoushe_cookie = tk.Text(
        rf,
        height=4,
        bg=SURFACE,
        fg=FG,
        insertbackground=ACCENT,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        font=("Consolas", 9),
        wrap=tk.WORD,
    )
    gui.txt_miyoushe_cookie.pack(fill=tk.X, pady=4)
    gui.txt_miyoushe_cookie.bind("<<Modified>>", lambda e: gui._on_cookie_modified(e, "miyoushe"))

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
        tk.Label(r, text=lbl_text, bg=BG, fg=FG, font=("Microsoft YaHei UI", 10), width=8, anchor="w").pack(
            side=tk.LEFT, padx=(0, 8)
        )
        setattr(gui, var_attr, tk.StringVar())
        setattr(gui, f"ent_{var_attr[4:]}", entry(r, getattr(gui, var_attr), show=show))
        getattr(gui, f"ent_{var_attr[4:]}").pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Signin toggles
    sep(rf)
    section_title(rf, "功能开关")

    gui.var_genshin = tk.BooleanVar()
    gui.var_starrail = tk.BooleanVar()
    gui.var_zzz = tk.BooleanVar()
    gui.var_miyoushe = tk.BooleanVar()
    gui.var_bbs_read = tk.BooleanVar()
    gui.var_bbs_like = tk.BooleanVar()
    gui.var_bbs_share = tk.BooleanVar()

    checks = [
        ("启用 原神 签到", gui.var_genshin),
        ("启用 崩坏：星穹铁道 签到", gui.var_starrail),
        ("启用 绝区零 签到", gui.var_zzz),
        ("启用 米游社 签到", gui.var_miyoushe),
        ("米游社任务: 看贴", gui.var_bbs_read),
        ("米游社任务: 点赞", gui.var_bbs_like),
        ("米游社任务: 分享", gui.var_bbs_share),
    ]
    grid = tk.Frame(rf, bg=BG)
    grid.pack(fill=tk.X, pady=4)
    for i, (txt, var) in enumerate(checks):
        ToggleSwitch(grid, text=txt, variable=var).grid(row=i // 2, column=i % 2, sticky="w", padx=8, pady=6)

    sep(rf)
    save_row = tk.Frame(rf, bg=BG)
    save_row.pack(fill=tk.X, pady=(4, 16))
    StyledButton(save_row, "💾 保存设置", command=gui._save_current_account, primary=True, width=110).pack(
        side=tk.RIGHT, padx=(8, 0)
    )
    StyledButton(save_row, "▶ 立即签到", command=gui._run_signin, width=100).pack(side=tk.RIGHT)


def build_signin_page(gui) -> None:
    # ──────────────────── Page: Signin ───────────────────────
    page = tk.Frame(gui.content_area, bg=BG)
    gui._pages["signin"] = page

    tk.Label(page, text="签到设置", bg=BG, fg=FG, font=("Microsoft YaHei UI", 14, "bold")).pack(
        anchor="w", padx=20, pady=(16, 4)
    )

    sf = tk.Frame(page, bg=BG)
    sf.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

    # Sign-in order
    section_title(sf, "签到顺序")
    label(sf, "按列表顺序依次执行，拖动按钮调整。", secondary=True).pack(anchor="w", pady=(0, 6))

    gui.signin_item_labels = [
        ("genshin", "原神"),
        ("starrail", "崩坏：星穹铁道"),
        ("zzz", "绝区零"),
        ("miyoushe", "米游社"),
    ]
    gui.signin_order_ids = [x[0] for x in gui.signin_item_labels]

    order_frame = tk.Frame(sf, bg=BG)
    order_frame.pack(fill=tk.X, pady=4)

    gui.lst_signin_order = tk.Listbox(
        order_frame,
        height=5,
        bg=SURFACE,
        fg=FG,
        selectbackground=SURFACE2,
        selectforeground=ACCENT,
        activestyle="none",
        relief=tk.FLAT,
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        font=("Microsoft YaHei UI", 10),
    )
    gui.lst_signin_order.pack(side=tk.LEFT, fill=tk.X, expand=True)

    btn_col = tk.Frame(order_frame, bg=BG)
    btn_col.pack(side=tk.LEFT, padx=10)
    StyledButton(btn_col, "▲ 上移", command=lambda: gui._move_signin_order(-1), width=80).pack(fill=tk.X, pady=2)
    StyledButton(btn_col, "▼ 下移", command=lambda: gui._move_signin_order(1), width=80).pack(fill=tk.X, pady=2)
    StyledButton(btn_col, "恢复默认", command=gui._reset_signin_order, width=80).pack(fill=tk.X, pady=2)

    sep(sf)

    # Risk/Captcha settings
    section_title(sf, "风控设置")
    gui.var_daily_signin_once = tk.BooleanVar()
    gui.var_skip_captcha_items_today = tk.BooleanVar()
    for txt, var in [
        ("每天仅在首次启动时执行自动签到", gui.var_daily_signin_once),
        ("若今日已触发验证码则跳过相应项", gui.var_skip_captcha_items_today),
    ]:
        ToggleSwitch(sf, text=txt, variable=var).pack(anchor="w", pady=6)

    sep(sf)
    StyledButton(sf, "💾 保存签到设置", command=gui._save_global_settings, primary=True, width=120).pack(
        anchor="e", pady=(4, 20)
    )


__all__ = ["build_accounts_page", "build_signin_page"]
