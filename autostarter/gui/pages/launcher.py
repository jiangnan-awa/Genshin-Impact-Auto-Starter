"""
autostarter.gui.pages.launcher

从根目录 gui.py 拆出的页面构建代码：
- build_launch_page()
- build_mod_page()

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
        Label=_DummyWidget,
        Spinbox=_DummyWidget,
        BOTH="both",
        X="x",
        Y="y",
        LEFT="left",
        RIGHT="right",
        TOP="top",
        END="end",
        FLAT="flat",
    )

from autostarter.gui.style import (
    ACCENT,
    BG,
    BORDER,
    FG,
    SURFACE,
    SURFACE2,
    browse_btn,
    entry,
    label,
    section_title,
    sep,
)
from autostarter.gui.widgets.buttons import StyledButton
from autostarter.gui.widgets.toggles import ToggleSwitch


def build_launch_page(gui) -> None:
    # ──────────────────── Page: Launch ───────────────────────
    page = tk.Frame(gui.content_area, bg=BG)
    gui._pages["launch"] = page

    tk.Label(page, text="启动设置", bg=BG, fg=FG, font=("Microsoft YaHei UI", 14, "bold")).pack(
        anchor="w", padx=20, pady=(16, 4)
    )

    canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(page, orient="vertical", command=canvas.yview)
    sf = tk.Frame(canvas, bg=BG)
    sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    cw = canvas.create_window((0, 0), window=sf, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=8)
    sb.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

    # BetterGI
    section_title(sf, "BetterGI 设置")

    row1 = tk.Frame(sf, bg=BG)
    row1.pack(fill=tk.X, pady=4)
    gui.var_bettergi_enabled = tk.BooleanVar()
    ToggleSwitch(row1, text="启用 BetterGI 启动", variable=gui.var_bettergi_enabled).pack(side=tk.LEFT, padx=(0, 24))
    gui.var_bettergi_onedragon_enabled = tk.BooleanVar()
    ToggleSwitch(row1, text="启用一条龙模式", variable=gui.var_bettergi_onedragon_enabled).pack(side=tk.LEFT)

    def _path_row(parent, lbl_text, var_attr, filetypes=None):
        r = tk.Frame(parent, bg=BG)
        r.pack(fill=tk.X, pady=4)
        label(r, lbl_text).pack(side=tk.LEFT, padx=(0, 8))
        setattr(gui, var_attr, tk.StringVar())
        entry(r, getattr(gui, var_attr), width=36).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        browse_btn(r, getattr(gui, var_attr), filetypes=filetypes).pack(side=tk.LEFT)

    _path_row(sf, "BetterGI 路径 (.exe):", "var_bettergi_path")

    def _text_row(parent, lbl_text, var_attr):
        r = tk.Frame(parent, bg=BG)
        r.pack(fill=tk.X, pady=4)
        label(r, lbl_text).pack(side=tk.LEFT, padx=(0, 8))
        setattr(gui, var_attr, tk.StringVar())
        entry(r, getattr(gui, var_attr), width=36).pack(side=tk.LEFT, fill=tk.X, expand=True)

    _text_row(sf, "一条龙配置名称:", "var_bettergi_onedragon_config")
    _text_row(sf, "第二个一条龙配置:", "var_bettergi_onedragon_config_2")
    label(sf, "提示: 填写第二个配置后，将在第一个任务结束后自动切换。留空则使用 BetterGI 当前选定的配置。", secondary=True).pack(
        anchor="w", pady=2
    )

    sep(sf)

    # Direct Genshin
    section_title(sf, "直接启动原神")
    _path_row(sf, "游戏路径 (Genshin Impact.exe):", "var_genshin_path")
    label(sf, "提示: 仅在禁用 BetterGI 且未使用外置启动器时生效。", secondary=True).pack(anchor="w", pady=2)

    sep(sf)

    # External launcher
    section_title(sf, "外置启动器模式")
    gui.var_external_launcher_mode = tk.BooleanVar()
    ToggleSwitch(sf, text="启用外置启动器", variable=gui.var_external_launcher_mode).pack(anchor="w", pady=4)
    _path_row(sf, "外置启动器路径:", "var_external_launcher_path")

    ext_r = tk.Frame(sf, bg=BG)
    ext_r.pack(fill=tk.X, pady=4)
    label(ext_r, "启动参数:").pack(side=tk.LEFT, padx=(0, 8))
    gui.var_external_launcher_args = tk.StringVar()
    entry(ext_r, gui.var_external_launcher_args, width=36).pack(side=tk.LEFT, fill=tk.X, expand=True)
    ext_wait_row = tk.Frame(sf, bg=BG)
    ext_wait_row.pack(fill=tk.X, pady=4)
    label(ext_wait_row, "启动后等待 (秒):").pack(side=tk.LEFT, padx=(0, 8))
    gui.var_external_launcher_wait_seconds = tk.IntVar(value=5)
    tk.Spinbox(
        ext_wait_row,
        from_=0,
        to=300,
        textvariable=gui.var_external_launcher_wait_seconds,
        width=8,
        bg=SURFACE,
        fg=FG,
        buttonbackground=SURFACE2,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=BORDER,
        font=("Microsoft YaHei UI", 10),
    ).pack(side=tk.LEFT)
    label(sf, "提示: 启用后，先启动外置启动器，等待指定秒数后再继续启动 BetterGI/原神。", secondary=True).pack(
        anchor="w", pady=2
    )

    sep(sf)
    StyledButton(sf, "💾 保存启动设置", command=gui._save_global_settings, primary=True, width=120).pack(
        anchor="e", pady=(4, 20)
    )

    gui._launch_sf = sf  # keep ref for partial path row builder


def build_mod_page(gui) -> None:
    # ──────────────────── Page: Mod ──────────────────────────
    page = tk.Frame(gui.content_area, bg=BG)
    gui._pages["mod"] = page

    tk.Label(page, text="Mod 设置", bg=BG, fg=FG, font=("Microsoft YaHei UI", 14, "bold")).pack(
        anchor="w", padx=20, pady=(16, 4)
    )

    sf = tk.Frame(page, bg=BG)
    sf.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

    section_title(sf, "Mod 启动模式")
    gui.var_mod_enabled = tk.BooleanVar()
    ToggleSwitch(sf, text="启用 Mod 启动模式", variable=gui.var_mod_enabled).pack(anchor="w", pady=4)

    mod_path_row = tk.Frame(sf, bg=BG)
    mod_path_row.pack(fill=tk.X, pady=4)
    label(mod_path_row, "Mod 程序路径:").pack(side=tk.LEFT, padx=(0, 8))
    gui.var_mod_path = tk.StringVar()
    entry(mod_path_row, gui.var_mod_path, width=36).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
    browse_btn(mod_path_row, gui.var_mod_path).pack(side=tk.LEFT)

    wait_row = tk.Frame(sf, bg=BG)
    wait_row.pack(fill=tk.X, pady=4)
    label(wait_row, "启动后等待 (秒):").pack(side=tk.LEFT, padx=(0, 8))
    gui.var_mod_wait_seconds = tk.IntVar(value=6)
    tk.Spinbox(
        wait_row,
        from_=0,
        to=120,
        textvariable=gui.var_mod_wait_seconds,
        width=8,
        bg=SURFACE,
        fg=FG,
        buttonbackground=SURFACE2,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=BORDER,
        font=("Microsoft YaHei UI", 10),
    ).pack(side=tk.LEFT)

    label(sf, "说明: 在启动其他程序前，先以 --auto-launch 参数运行该 Mod 程序，并等待指定秒数。", secondary=True).pack(
        anchor="w", pady=4
    )
    label(sf, "提示: 也可在命令行加 --mod-mode 临时启用。", secondary=True).pack(anchor="w")

    sep(sf)
    StyledButton(sf, "💾 保存 Mod 设置", command=gui._save_global_settings, primary=True, width=120).pack(
        anchor="e", pady=(4, 20)
    )


__all__ = ["build_launch_page", "build_mod_page"]
