from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from ..state import AppState
def _import_customtkinter():
    try:
        import customtkinter as ctk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("customtkinter 未安装或不可用，无法创建 Presets 页面") from e
    return ctk
def build_page(parent: object, state: Optional[AppState] = None) -> object:
    ctk = _import_customtkinter()
    import os
    import re
    import subprocess
    import sys
    import threading
    import time
    import tkinter as tk
    from tkinter import messagebox, simpledialog
    import autostarter.flow_executor as FlowExecutor
    from autostarter.account_manager import account_manager
    from autostarter.flow_presets import FlowPresetManager
    from autostarter.log_actions import log_action
    from .. import bindings as b
    from ..widgets import forms
    state = state or AppState()
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
            try:
                toast_cb(msg)  # type: ignore[misc]
            except Exception:
                return
        except Exception:
            return
    pm = FlowPresetManager()
    try:
        pm.load()
    except Exception:
        pass
    def _list_presets() -> List[Dict[str, Any]]:
        return pm.list()
    def _get_current_preset_id() -> str:
        presets = _list_presets()
        active_id = str(pm.data.get("active_preset_id") or "")
        if active_id and any(str(p.get("id") or "") == active_id for p in presets):
            return active_id
        if presets:
            return str(presets[0].get("id") or "")
        return ""
    def _get_preset(preset_id: str) -> Optional[Dict[str, Any]]:
        if not preset_id:
            return None
        try:
            p = pm.get(preset_id)
            return p if isinstance(p, dict) else None
        except Exception:
            return None
    def is_shortcut_available() -> bool:
        return bool(sys.platform == "win32" and getattr(sys, "frozen", False))
    def sanitize_filename(name: str) -> str:
        s = (name or "").strip()
        s = re.sub(r'[<>:"/\\\\|?*\x00-\x1f]', "", s)
        s = s.rstrip(" .")
        return s or "Preset"
    def _ps_single_quote(val: str) -> str:
        return "'" + (val or "").replace("'", "''") + "'"
    STEP_LABELS: Dict[str, str] = {
        "signin": "签到",
        "external_launcher": "外置启动器",
        "mod": "Mod",
        "bettergi": "BetterGI",
        "onedragon": "一条龙",
        "genshin_direct": "直接启动原神",
        "wait": "等待",
    }
    ACTION_STEP_TYPES: List[Tuple[str, str]] = [
        ("signin", STEP_LABELS["signin"]),
        ("external_launcher", STEP_LABELS["external_launcher"]),
        ("mod", STEP_LABELS["mod"]),
        ("bettergi", STEP_LABELS["bettergi"]),
        ("onedragon", STEP_LABELS["onedragon"]),
        ("genshin_direct", STEP_LABELS["genshin_direct"]),
    ]
    frame = ctk.CTkFrame(master=parent, corner_radius=0)
    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(master=frame, text="流程编辑器", font=ctk.CTkFont(size=18, weight="bold")).grid(
        row=0, column=0, padx=16, pady=(16, 10), sticky="w"
    )
    actions = ctk.CTkFrame(master=frame, fg_color="transparent")
    actions.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="ew")
    actions.grid_columnconfigure(0, weight=1)
    actions.grid_columnconfigure(1, weight=0)
    left_bar = ctk.CTkFrame(master=actions, fg_color="transparent")
    left_bar.grid(row=0, column=0, sticky="ew")
    right_bar = ctk.CTkFrame(master=actions, fg_color="transparent")
    right_bar.grid(row=0, column=1, sticky="e")
    scroll = ctk.CTkScrollableFrame(master=frame, corner_radius=8)
    scroll.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="nsew")
    try:
        scroll.grid_columnconfigure(0, weight=1)  # type: ignore[attr-defined]
    except Exception:
        pass
    def _safe_save() -> bool:
        try:
            pm.save()
            return True
        except Exception as e:
            toast(f"保存预设失败：{e}", 2200)
            return False
    selected_preset_id_var = tk.StringVar(value=_get_current_preset_id())
    preset_label_to_id: Dict[str, str] = {}
    def _refresh_preset_selector() -> None:
        nonlocal preset_label_to_id
        preset_label_to_id = {}
        values: List[str] = []
        for p in _list_presets():
            pid = str(p.get("id") or "")
            name = str(p.get("name") or pid)
            label = f"{name}  ({pid[:6]})" if pid else name
            preset_label_to_id[label] = pid
            values.append(label)
        if not values:
            values = ["（暂无预设）"]
            preset_label_to_id[values[0]] = ""
        try:
            opt.configure(values=values)  # type: ignore[name-defined]
        except Exception:
            pass
        cur_id = str(selected_preset_id_var.get() or "")
        for label, pid in preset_label_to_id.items():
            if pid == cur_id:
                try:
                    opt.set(label)  # type: ignore[name-defined]
                except Exception:
                    pass
                return
        cur_id2 = _get_current_preset_id()
        selected_preset_id_var.set(cur_id2)
        for label, pid in preset_label_to_id.items():
            if pid == cur_id2:
                try:
                    opt.set(label)  # type: ignore[name-defined]
                except Exception:
                    pass
                return
    def _update_flow(preset_id: str, new_flow: List[Dict[str, Any]]) -> None:
        if not preset_id:
            return
        try:
            pm.update_flow(preset_id, new_flow)
            if _safe_save():
                toast("已保存流程")
        except Exception as e:
            toast(f"保存流程失败：{e}", 2400)
    def _refresh_flow_list() -> None:
        content = getattr(scroll, "_scrollable_frame", scroll)
        try:
            for child in list(content.winfo_children()):  # type: ignore[attr-defined]
                child.destroy()
        except Exception:
            pass
        preset_id = str(selected_preset_id_var.get() or "")
        preset = _get_preset(preset_id)
        if not preset:
            ctk.CTkLabel(
                master=content,
                text="暂无预设。请先“新建预设”。",
                anchor="w",
                justify="left",
                wraplength=760,
                text_color=("gray35", "gray70"),
            ).pack(anchor="w", pady=(6, forms.SECTION_GAP_Y))
            return
        name = str(preset.get("name") or preset_id)
        active_id = str(pm.data.get("active_preset_id") or "")
        header = f"{name}（默认）" if preset_id and preset_id == active_id else name
        forms.make_section_title(content, f"当前预设：{header}").pack(anchor="w", pady=(0, forms.ROW_GAP_Y))
        flow = preset.get("flow")
        steps: List[Dict[str, Any]] = list(flow) if isinstance(flow, list) else []
        if not steps:
            ctk.CTkLabel(
                master=content,
                text="此预设还没有步骤。你可以添加动作步骤或等待步骤。",
                anchor="w",
                justify="left",
                wraplength=760,
                text_color=("gray35", "gray70"),
            ).pack(anchor="w", pady=(6, forms.SECTION_GAP_Y))
            return
        def _move(i: int, delta: int) -> None:
            if i < 0 or i >= len(steps):
                return
            j = i + delta
            if j < 0 or j >= len(steps):
                return
            steps[i], steps[j] = steps[j], steps[i]
            _update_flow(preset_id, steps)
            _refresh_flow_list()
        def _delete(i: int) -> None:
            if i < 0 or i >= len(steps):
                return
            del steps[i]
            _update_flow(preset_id, steps)
            _refresh_flow_list()
        def _commit_wait(i: int, entry: object) -> None:
            try:
                s = int(str(entry.get() or "0").strip())  # type: ignore[attr-defined]
            except Exception:
                s = 0
            if s < 0:
                s = 0
            if s > 3000:
                s = 3000
            try:
                step = steps[i]
            except Exception:
                return
            if not isinstance(step, dict) or step.get("type") != "wait":
                return
            step["seconds"] = s
            _update_flow(preset_id, steps)
        for i, step in enumerate(steps):
            t = step.get("type") if isinstance(step, dict) else None
            t = str(t) if isinstance(t, str) else ""
            row = ctk.CTkFrame(master=content)
            row.pack(fill="x", pady=(0, forms.ROW_GAP_Y))
            row.grid_columnconfigure(1, weight=1)
            idx_label = ctk.CTkLabel(master=row, text=f"{i+1}.", width=34, anchor="e")
            idx_label.grid(row=0, column=0, padx=(10, 0), pady=10, sticky="w")
            body = ctk.CTkFrame(master=row, fg_color="transparent")
            body.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
            body.grid_columnconfigure(2, weight=1)
            if t == "wait":
                ctk.CTkLabel(master=body, text=STEP_LABELS["wait"], anchor="w").grid(
                    row=0, column=0, padx=(0, 8), pady=4, sticky="w"
                )
                ctk.CTkLabel(master=body, text="秒", anchor="w").grid(row=0, column=2, padx=(6, 0), pady=4, sticky="w")
                e = forms.make_entry(body, placeholder="秒数", width=90)
                try:
                    e.insert(0, str(int(step.get("seconds", 0))))  # type: ignore[attr-defined]
                except Exception:
                    try:
                        e.insert(0, "0")  # type: ignore[attr-defined]
                    except Exception:
                        pass
                e.grid(row=0, column=1, padx=(0, 0), pady=4, sticky="w")
                try:
                    e.bind("<Return>", lambda _ev, _i=i, _e=e: _commit_wait(_i, _e))
                    e.bind("<FocusOut>", lambda _ev, _i=i, _e=e: _commit_wait(_i, _e))
                except Exception:
                    pass
            else:
                ctk.CTkLabel(master=body, text=STEP_LABELS.get(t, t or "未知"), anchor="w").grid(
                    row=0, column=0, padx=(0, 8), pady=6, sticky="w"
                )
            btns = ctk.CTkFrame(master=row, fg_color="transparent")
            btns.grid(row=0, column=2, padx=10, pady=8, sticky="e")
            up_btn = forms.make_button(btns, "上移", command=lambda _i=i: _move(_i, -1), width=56)
            down_btn = forms.make_button(btns, "下移", command=lambda _i=i: _move(_i, +1), width=56)
            del_btn = forms.make_button(btns, "删除", command=lambda _i=i: _delete(_i), width=56)
            up_btn.pack(side="left", padx=4)
            down_btn.pack(side="left", padx=4)
            del_btn.pack(side="left", padx=4)
            if i == 0:
                try:
                    up_btn.configure(state="disabled")  # type: ignore[attr-defined]
                except Exception:
                    pass
            if i == len(steps) - 1:
                try:
                    down_btn.configure(state="disabled")  # type: ignore[attr-defined]
                except Exception:
                    pass
    def _create_preset() -> None:
        name = simpledialog.askstring("新建预设", "预设名称：", initialvalue=f"新预设 {time.strftime('%H%M%S')}")
        if not name:
            return
        try:
            pid = pm.create(name=str(name).strip(), flow=[])
            pm.set_active(pid)
            if _safe_save():
                toast("已创建预设")
            selected_preset_id_var.set(pid)
            _refresh_preset_selector()
            _refresh_flow_list()
        except Exception as e:
            toast(f"创建失败：{e}", 2200)
    def _rename_preset() -> None:
        pid = str(selected_preset_id_var.get() or "")
        p = _get_preset(pid)
        if not p:
            return
        old_name = str(p.get("name") or pid)
        new_name = simpledialog.askstring("重命名预设", "新名称：", initialvalue=old_name)
        if not new_name:
            return
        try:
            pm.rename(pid, str(new_name).strip())
            if _safe_save():
                toast("已重命名预设")
            _refresh_preset_selector()
            _refresh_flow_list()
        except Exception as e:
            toast(f"重命名失败：{e}", 2200)
    def _delete_preset() -> None:
        pid = str(selected_preset_id_var.get() or "")
        p = _get_preset(pid)
        if not p:
            return
        name = str(p.get("name") or pid)
        ok = messagebox.askyesno("删除预设", f"确定删除预设“{name}”吗？\n此操作不可撤销。")
        if not ok:
            return
        try:
            pm.delete(pid)
            if _safe_save():
                toast("已删除预设")
            selected_preset_id_var.set(_get_current_preset_id())
            _refresh_preset_selector()
            _refresh_flow_list()
        except Exception as e:
            toast(f"删除失败：{e}", 2200)
    def _set_active_preset() -> None:
        pid = str(selected_preset_id_var.get() or "")
        if not pid:
            return
        try:
            pm.set_active(pid)
            if _safe_save():
                toast("已设为默认预设")
            _refresh_preset_selector()
            _refresh_flow_list()
        except Exception as e:
            toast(f"设为默认失败：{e}", 2200)
    def _create_shortcut() -> None:
        pid = str(selected_preset_id_var.get() or "")
        p = _get_preset(pid)
        if not pid or not p:
            return
        name = str(p.get("name") or pid)
        if not is_shortcut_available():
            log_action("GUI", "create_shortcut", "skip", preset_id=pid, reason="not_available")
            toast("仅 Windows 打包版支持生成桌面快捷方式", 2200)
            return
        from autostarter.shortcut_utils import build_shortcut_basename, resolve_autostarter_target_exe
        base_path = os.path.dirname(sys.executable)
        target_exe = resolve_autostarter_target_exe(base_path=base_path, current_executable=sys.executable)
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        safe_name = build_shortcut_basename(
            preset_name=name,
            preset_id=pid,
            desktop_dir=desktop_dir,
        )
        flow = p.get("flow") if isinstance(p, dict) else None
        steps = flow if isinstance(flow, list) else []
        log_action("GUI", "create_shortcut", "start", preset_id=pid, steps_count=len(steps))
        def _worker() -> None:
            try:
                from autostarter.shortcut_utils import (
                    build_powershell_create_shortcut_command,
                    create_windows_shortcut,
                )
                lnk_path = os.path.join(desktop_dir, safe_name + ".lnk")
                try:
                    create_windows_shortcut(
                        lnk_path=lnk_path,
                        target_path=target_exe,
                        arguments=f"--preset {pid}",
                        working_dir=base_path,
                    )
                except Exception:
                    ps = build_powershell_create_shortcut_command(
                        lnk_path=lnk_path,
                        target_path=target_exe,
                        arguments=f"--preset {pid}",
                        working_dir=base_path,
                    )
                    from autostarter.shortcut_utils import run_powershell_hidden
                    proc = run_powershell_hidden(ps)
                    if proc.returncode != 0:
                        err = (proc.stderr or proc.stdout or "").strip()
                        raise RuntimeError(err or f"PowerShell 返回码 {proc.returncode}")
                log_action("GUI", "create_shortcut", "ok", preset_id=pid, file=f"{safe_name}.lnk")
                toast(f"已生成桌面快捷方式：{safe_name}.lnk", 2200)
            except Exception as e:
                log_action("GUI", "create_shortcut", "fail", preset_id=pid, reason=str(e))
                toast(f"生成快捷方式失败：{e}", 2600)
        threading.Thread(target=_worker, daemon=True).start()
    def _add_wait_step() -> None:
        pid = str(selected_preset_id_var.get() or "")
        p = _get_preset(pid)
        if not pid or not p:
            return
        flow = p.get("flow")
        steps: List[Dict[str, Any]] = list(flow) if isinstance(flow, list) else []
        steps.append({"type": "wait", "seconds": 5})
        _update_flow(pid, steps)
        _refresh_flow_list()
    def _add_action_step(step_type: str) -> None:
        pid = str(selected_preset_id_var.get() or "")
        p = _get_preset(pid)
        if not pid or not p:
            return
        flow = p.get("flow")
        steps: List[Dict[str, Any]] = list(flow) if isinstance(flow, list) else []
        steps.append({"type": step_type})
        _update_flow(pid, steps)
        _refresh_flow_list()
    def _show_add_action_menu(anchor_widget: object) -> None:
        pid = str(selected_preset_id_var.get() or "")
        p = _get_preset(pid)
        if not pid or not p:
            toast("请先新建或选择一个预设")
            return
        try:
            flow = p.get("flow")
            steps: List[Dict[str, Any]] = list(flow) if isinstance(flow, list) else []
            existing = {str(s.get("type") or "") for s in steps if isinstance(s, dict)}
            top = frame.winfo_toplevel()
            m = tk.Menu(top, tearoff=0)
            for step_type, label in ACTION_STEP_TYPES:
                state = "disabled" if step_type in existing else "normal"
                m.add_command(label=label, command=lambda _t=step_type: _add_action_step(_t), state=state)
        except Exception as e:
            toast(f"打开菜单失败：{e}")
            return
        def _popup() -> None:
            try:
                try:
                    x = int(anchor_widget.winfo_rootx())  # type: ignore[attr-defined]
                    y = int(anchor_widget.winfo_rooty() + anchor_widget.winfo_height())  # type: ignore[attr-defined]
                except Exception:
                    x = int(frame.winfo_pointerx())
                    y = int(frame.winfo_pointery())
                try:
                    m.update_idletasks()
                    mw = int(m.winfo_reqwidth())
                    mh = int(m.winfo_reqheight())
                    sw = int(top.winfo_screenwidth())
                    sh = int(top.winfo_screenheight())
                    if x + mw > sw - 4:
                        x = max(0, sw - mw - 4)
                    if y + mh > sh - 4:
                        y2 = y - mh - int(getattr(anchor_widget, "winfo_height", lambda: 0)())
                        if y2 >= 0:
                            y = y2
                        else:
                            y = max(0, sh - mh - 4)
                except Exception:
                    pass
                m.tk_popup(x, y)
            except Exception as e:
                toast(f"打开菜单失败：{e}")
            finally:
                try:
                    m.grab_release()
                except Exception:
                    pass
        try:
            frame.after(0, _popup)  # type: ignore[attr-defined]
        except Exception:
            _popup()
    def _show_more_menu(anchor_widget: object) -> None:
        pid = str(selected_preset_id_var.get() or "")
        p = _get_preset(pid)
        if not pid or not p:
            toast("请先新建或选择一个预设")
            return
        try:
            top = frame.winfo_toplevel()
            m = tk.Menu(top, tearoff=0)
            m.add_command(label="设为默认", command=_set_active_preset)
            if is_shortcut_available():
                m.add_command(label="生成桌面快捷方式", command=_create_shortcut)
            else:
                m.add_command(label="生成桌面快捷方式", command=_create_shortcut, state="disabled")
        except Exception as e:
            toast(f"打开菜单失败：{e}")
            return
        def _popup() -> None:
            try:
                try:
                    x = int(anchor_widget.winfo_rootx())  # type: ignore[attr-defined]
                    y = int(anchor_widget.winfo_rooty() + anchor_widget.winfo_height())  # type: ignore[attr-defined]
                except Exception:
                    x = int(frame.winfo_pointerx())
                    y = int(frame.winfo_pointery())
                try:
                    m.update_idletasks()
                    mw = int(m.winfo_reqwidth())
                    mh = int(m.winfo_reqheight())
                    sw = int(top.winfo_screenwidth())
                    sh = int(top.winfo_screenheight())
                    if x + mw > sw - 4:
                        x = max(0, sw - mw - 4)
                    if y + mh > sh - 4:
                        y2 = y - mh - int(getattr(anchor_widget, "winfo_height", lambda: 0)())
                        if y2 >= 0:
                            y = y2
                        else:
                            y = max(0, sh - mh - 4)
                except Exception:
                    pass
                m.tk_popup(x, y)
            except Exception as e:
                toast(f"打开菜单失败：{e}")
            finally:
                try:
                    m.grab_release()
                except Exception:
                    pass
        try:
            frame.after(0, _popup)  # type: ignore[attr-defined]
        except Exception:
            _popup()
    def _run_current_flow() -> None:
        pid = str(selected_preset_id_var.get() or "")
        p = _get_preset(pid)
        if not pid or not p:
            return
        name = str(p.get("name") or pid)
        flow = p.get("flow") if isinstance(p, dict) else None
        steps = flow if isinstance(flow, list) else []
        def _worker() -> None:
            try:
                log_action("GUI", "run_preset", "start", preset_id=pid, steps_count=len(steps))
                toast(f"正在执行流程：{name} ...", 1800)
                FlowExecutor.run_flow(steps, account_manager.get_settings())
                log_action("GUI", "run_preset", "ok", preset_id=pid, steps_count=len(steps))
                toast(f"已发送启动指令：{name}", 1800)
            except Exception as e:
                log_action("GUI", "run_preset", "fail", preset_id=pid, steps_count=len(steps), reason=str(e))
                toast(f"启动失败：{e}", 2500)
        threading.Thread(target=_worker, daemon=True).start()
    ctk.CTkLabel(master=left_bar, text="预设：").pack(side="left", padx=(0, 6))
    opt = ctk.CTkOptionMenu(master=left_bar, values=["（加载中）"], width=220)
    opt.pack(side="left", padx=(0, 10))
    def _on_preset_change(label: str) -> None:
        pid = preset_label_to_id.get(label, "")
        selected_preset_id_var.set(pid)
        _refresh_flow_list()
    try:
        opt.configure(command=_on_preset_change)
    except Exception:
        pass
    forms.make_button(left_bar, "新建预设", command=_create_preset, width=90).pack(side="left", padx=(0, 8))
    forms.make_button(left_bar, "重命名", command=_rename_preset, width=70).pack(side="left", padx=(0, 8))
    forms.make_button(left_bar, "删除", command=_delete_preset, width=56).pack(side="left", padx=(0, 8))
    add_btn = forms.make_button(right_bar, "添加动作步骤 ▾", command=lambda: _show_add_action_menu(add_btn), width=120)
    more_btn = forms.make_button(right_bar, "更多 ▾", command=lambda: _show_more_menu(more_btn), width=72)
    more_btn.pack(side="left", padx=(0, 8))
    add_btn.pack(side="left", padx=(0, 8))
    forms.make_button(right_bar, "添加等待", command=_add_wait_step, width=90).pack(side="left", padx=(0, 8))
    forms.make_button(right_bar, "▶ 一键启动", command=_run_current_flow, width=90).pack(side="left")
    _refresh_preset_selector()
    _refresh_flow_list()
    _ = tk
    return frame
