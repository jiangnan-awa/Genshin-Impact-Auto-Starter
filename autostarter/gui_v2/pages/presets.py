"""
Presets page (GUI v2): 启动预设管理。

导入无副作用：
- 不在 import 阶段创建任何 GUI 组件/线程
- customtkinter/tkinter/业务模块均延迟导入

功能（v2 预设页）：
- 预设列表（可滚动）
- 新建 / 从当前 settings.json 生成 / 复制 / 重命名 / 删除
- 设为默认（active）
- ▶ 一键启动：game_launcher.launch(settings=preset_settings)（后台线程 + toast）
- 生成桌面快捷方式：仅 win32 且 sys.frozen（PowerShell + WScript.Shell）
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..state import AppState


def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法创建 Presets 页面") from e
    return ctk


def build_page(parent: object, state: Optional[AppState] = None) -> object:
    ctk = _import_customtkinter()
    import copy
    import os
    import re
    import subprocess
    import sys
    import threading
    import time
    import tkinter as tk
    from tkinter import messagebox, simpledialog

    from autostarter.launcher import game_launcher
    from autostarter.presets import PresetManager

    from .. import bindings as b
    from ..widgets import forms

    state = state or AppState()

    # toast 注入：允许 app 通过 state.data 传入一个线程安全回调
    toast_cb: Optional[Callable[..., None]] = None
    if isinstance(getattr(state, "data", None), dict):
        maybe = state.data.get("toast") or state.data.get("toast_cb") or state.data.get("toast_callback")
        if callable(maybe):
            toast_cb = maybe  # type: ignore[assignment]

    def toast(msg: str, ms: int = 1800) -> None:
        if toast_cb is None:
            return
        try:
            toast_cb(msg, ms)  # type: ignore[misc]
        except TypeError:
            # 兼容只接收一个参数的回调
            try:
                toast_cb(msg)  # type: ignore[misc]
            except Exception:
                return
        except Exception:
            return

    # ───────────────────────── Data ─────────────────────────
    pm = PresetManager()
    try:
        pm.load()
    except Exception:
        # 读取失败：仍允许用户创建新预设覆盖保存
        pass

    def is_shortcut_available() -> bool:
        return bool(sys.platform == "win32" and getattr(sys, "frozen", False))

    def sanitize_filename(name: str) -> str:
        """
        Windows 文件名净化：
        - 移除 <>:"/\\|?* 与控制字符
        - 去除尾部空格/点
        """
        s = (name or "").strip()
        s = re.sub(r'[<>:"/\\\\|?*\\x00-\\x1f]', "", s)
        s = s.rstrip(" .")
        return s or "Preset"

    def _ps_single_quote(val: str) -> str:
        """PowerShell 单引号字符串转义：' -> ''"""
        return "'" + (val or "").replace("'", "''") + "'"

    # ───────────────────────── UI Layout ─────────────────────────
    frame = ctk.CTkFrame(master=parent, corner_radius=0)
    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(master=frame, text="预设", font=ctk.CTkFont(size=18, weight="bold")).grid(
        row=0, column=0, padx=16, pady=(16, 10), sticky="w"
    )

    # 顶部操作栏
    actions = ctk.CTkFrame(master=frame, fg_color="transparent")
    actions.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="ew")
    actions.grid_columnconfigure(0, weight=1)

    btn_row = ctk.CTkFrame(master=actions, fg_color="transparent")
    btn_row.grid(row=0, column=0, sticky="ew")

    # 列表滚动区域
    scroll = ctk.CTkScrollableFrame(master=frame, corner_radius=8)
    scroll.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="nsew")
    try:
        scroll.grid_columnconfigure(0, weight=1)  # type: ignore[attr-defined]
    except Exception:
        pass

    # ───────────────────────── Helpers ─────────────────────────
    def _safe_save() -> bool:
        try:
            pm.save()
            return True
        except Exception as e:
            toast(f"保存预设失败：{e}", 2200)
            return False

    def refresh_list() -> None:
        # 清空原有子控件并重建
        content = getattr(scroll, "_scrollable_frame", scroll)
        try:
            for child in list(content.winfo_children()):  # type: ignore[attr-defined]
                child.destroy()
        except Exception:
            pass

        presets = pm.list()
        active_id = str(pm.data.get("active_preset_id") or "")

        if not presets:
            empty_hint2 = ctk.CTkLabel(
                master=content,
                text="暂无预设。你可以从当前配置生成一个，或新建空白预设。",
                anchor="w",
                justify="left",
                wraplength=760,
                text_color=("gray35", "gray70"),
            )
            empty_hint2.pack(anchor="w", pady=(6, forms.SECTION_GAP_Y))
            return

        forms.make_section_title(content, "预设列表").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))

        for p in presets:
            pid = str(p.get("id") or "")
            name = str(p.get("name") or pid)
            settings = p.get("settings") if isinstance(p, dict) else {}
            if not isinstance(settings, dict):
                settings = {}

            row = ctk.CTkFrame(master=content)
            row.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
            row.grid_columnconfigure(0, weight=1)

            title = name
            if pid and pid == active_id:
                title = f"▶ {title}（默认）"

            ctk.CTkLabel(master=row, text=title, anchor="w").grid(row=0, column=0, padx=10, pady=10, sticky="w")

            btns = ctk.CTkFrame(master=row, fg_color="transparent")
            btns.grid(row=0, column=1, padx=10, pady=8, sticky="e")

            def _mk_launch(s: Dict[str, Any], preset_name: str) -> Callable[[], None]:
                def _run() -> None:
                    payload = copy.deepcopy(s)

                    def _worker() -> None:
                        try:
                            toast(f"正在启动：{preset_name} ...", 1800)
                            game_launcher.launch(settings=payload)
                            toast(f"已发送启动指令：{preset_name}", 1800)
                        except Exception as e:
                            toast(f"启动失败：{e}", 2500)

                    threading.Thread(target=_worker, daemon=True).start()

                return _run

            def _mk_set_active(preset_id: str) -> Callable[[], None]:
                def _run() -> None:
                    try:
                        pm.set_active(preset_id)
                        if _safe_save():
                            toast("已设为默认预设")
                        refresh_list()
                    except Exception as e:
                        toast(f"设为默认失败：{e}", 2200)

                return _run

            def _mk_copy(preset_obj: Dict[str, Any], source_settings: Dict[str, Any]) -> Callable[[], None]:
                def _run() -> None:
                    base_name = str(preset_obj.get("name") or "预设")
                    new_name = simpledialog.askstring("复制预设", "新预设名称：", initialvalue=f"{base_name} - 副本")
                    if not new_name:
                        return
                    try:
                        pm.create(name=str(new_name).strip(), settings=copy.deepcopy(source_settings))
                        if _safe_save():
                            toast(f"已复制预设：{new_name}")
                        refresh_list()
                    except Exception as e:
                        toast(f"复制失败：{e}", 2200)

                return _run

            def _mk_rename(preset_id: str, old_name: str) -> Callable[[], None]:
                def _run() -> None:
                    new_name = simpledialog.askstring("重命名预设", "新名称：", initialvalue=old_name)
                    if not new_name:
                        return
                    try:
                        pm.rename(preset_id, str(new_name).strip())
                        if _safe_save():
                            toast("已重命名预设")
                        refresh_list()
                    except Exception as e:
                        toast(f"重命名失败：{e}", 2200)

                return _run

            def _mk_delete(preset_id: str, preset_name: str) -> Callable[[], None]:
                def _run() -> None:
                    ok = messagebox.askyesno("删除预设", f"确定删除预设“{preset_name}”吗？\n此操作不可撤销。")
                    if not ok:
                        return
                    try:
                        pm.delete(preset_id)
                        if _safe_save():
                            toast("已删除预设")
                        refresh_list()
                    except Exception as e:
                        toast(f"删除失败：{e}", 2200)

                return _run

            def _mk_shortcut(preset_id: str, preset_name: str) -> Callable[[], None]:
                def _run() -> None:
                    if not is_shortcut_available():
                        toast("仅 Windows 打包版支持生成桌面快捷方式", 2200)
                        return

                    safe_name = sanitize_filename(preset_name)
                    target_exe = sys.executable
                    base_path = os.path.dirname(sys.executable)

                    def _worker() -> None:
                        try:
                            ps = [
                                "powershell",
                                "-NoProfile",
                                "-ExecutionPolicy",
                                "Bypass",
                                "-Command",
                                (
                                    "$desk=[Environment]::GetFolderPath('Desktop');"
                                    f"$lnk=Join-Path $desk {_ps_single_quote(safe_name + '.lnk')};"
                                    "$ws=New-Object -ComObject WScript.Shell;"
                                    "$s=$ws.CreateShortcut($lnk);"
                                    f"$s.TargetPath={_ps_single_quote(target_exe)};"
                                    f"$s.Arguments='--preset {preset_id}';"
                                    f"$s.WorkingDirectory={_ps_single_quote(base_path)};"
                                    "$s.Save();"
                                ),
                            ]
                            proc = subprocess.run(ps, capture_output=True, text=True, check=False)
                            if proc.returncode != 0:
                                err = (proc.stderr or proc.stdout or "").strip()
                                raise RuntimeError(err or f"PowerShell 返回码 {proc.returncode}")
                            toast(f"已生成桌面快捷方式：{safe_name}.lnk", 2200)
                        except Exception as e:
                            toast(f"生成快捷方式失败：{e}", 2600)

                    threading.Thread(target=_worker, daemon=True).start()

                return _run

            # 按钮（顺序：启动/默认/复制/重命名/删除/快捷方式）
            forms.make_button(btns, "▶ 一键启动", command=_mk_launch(settings, name), width=90).pack(side="left", padx=4)
            forms.make_button(btns, "设为默认", command=_mk_set_active(pid), width=80).pack(side="left", padx=4)
            forms.make_button(btns, "复制", command=_mk_copy(p, settings), width=56).pack(side="left", padx=4)
            forms.make_button(btns, "重命名", command=_mk_rename(pid, name), width=70).pack(side="left", padx=4)
            forms.make_button(btns, "删除", command=_mk_delete(pid, name), width=56).pack(side="left", padx=4)

            if is_shortcut_available():
                forms.make_button(btns, "生成桌面快捷方式", command=_mk_shortcut(pid, name), width=130).pack(
                    side="left", padx=4
                )

    # ───────────────────────── Top actions ─────────────────────────
    def create_empty_preset() -> None:
        name = simpledialog.askstring("新建预设", "预设名称：", initialvalue=f"新预设 {time.strftime('%H%M%S')}")
        if not name:
            return
        try:
            pm.create(name=str(name).strip(), settings={})
            if _safe_save():
                toast("已创建预设")
            refresh_list()
        except Exception as e:
            toast(f"创建失败：{e}", 2200)

    def create_from_current_settings() -> None:
        default_name = f"当前配置 {time.strftime('%Y-%m-%d %H:%M')}"
        name = simpledialog.askstring("从当前配置生成预设", "预设名称：", initialvalue=default_name)
        if not name:
            return
        try:
            settings = b.load_settings()
        except Exception as e:
            toast(f"读取 settings.json 失败：{e}", 2400)
            settings = {}
        try:
            pm.create(name=str(name).strip(), settings=settings if isinstance(settings, dict) else {})
            if _safe_save():
                toast("已从当前配置生成预设")
            refresh_list()
        except Exception as e:
            toast(f"生成失败：{e}", 2200)

    def reload_presets() -> None:
        try:
            pm.load()
            toast("已重新加载预设")
        except Exception as e:
            toast(f"重新加载失败：{e}", 2200)
        refresh_list()

    forms.make_button(btn_row, "从当前配置生成预设", command=create_from_current_settings, width=150).pack(
        side="left", padx=(0, 8)
    )
    forms.make_button(btn_row, "新建空白预设", command=create_empty_preset, width=120).pack(side="left", padx=(0, 8))
    forms.make_button(btn_row, "重新加载", command=reload_presets, width=90).pack(side="left")

    # 首次渲染
    refresh_list()

    # 避免未使用的 tkinter 变量警告（仅保证导入阶段无副作用）
    _ = tk
    return frame
