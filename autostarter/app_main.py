import sys
import time
import threading
import datetime
import ctypes
from .account_manager import account_manager
from .mihoyo_api import mihoyo_client
from .launcher import game_launcher
from .loghelper import log
from .flow_executor import run_flow
from .flow_presets import FlowPresetManager

def _collect_signin_results(accounts):
    lines = []
    has_error = False
    item_labels = {
        "genshin": "原神",
        "starrail": "崩坏：星穹铁道",
        "zzz": "绝区零",
        "miyoushe": "米游社",
    }
    settings = account_manager.get_settings()
    order = settings.get("signin_order") or ["genshin", "starrail", "zzz", "miyoushe"]

    def summarize(text: str) -> str:
        if not text:
            return "失败"
        # 优先识别跳过逻辑，即使跳过原因中含有“验证码”字样，也应该被归类为“跳过”
        if "跳过" in text or "已完成" in text:
            return "跳过"
        if "验证码" in text or "触发验证码" in text:
            return "需要验证码"
        if "失败" in text or "错误" in text or "无效" in text:
            return "失败"
        if "已签" in text or "已签到" in text:
            return "已签到"
        return "成功"

    if not accounts:
        lines.append("未配置账号，跳过签到。")
        return lines, False, True

    for item in order:
        label = item_labels.get(item, item)
        parts = []
        for acc in accounts:
            try:
                results = mihoyo_client.sign_in_item(acc, item)
                text = "\n".join(results) if isinstance(results, list) else str(results)
                status = summarize(text)
                if status == "失败":
                    has_error = True
                parts.append(f"[{acc['name']}] {status}")
            except Exception as e:
                has_error = True
                parts.append(f"[{acc['name']}] 失败")
        lines.append(f"{label}: " + " | ".join(parts))
    if not has_error:
        today = datetime.date.today().isoformat()
        account_manager.update_settings(last_signin_date=today)
    return lines, has_error, (not has_error)

def _set_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def _show_result_popup(lines, has_error, auto_close_ms=5000):
    _set_dpi_awareness()
    try:
        import tkinter as tk
        from tkinter import ttk
    except ModuleNotFoundError:
        # 无 GUI 环境（例如 Linux 容器 / 纯命令行），退化为直接输出到 stderr。
        try:
            print("\n".join(lines), file=sys.stderr)
        except Exception:
            pass
        return
    root = tk.Tk()
    root.withdraw()
    top = tk.Toplevel(root)
    top.title("签到结果")
    top.geometry("550x250")
    top.attributes("-topmost", True)
    
    # 使用 Label 显示，看起来更像提示框
    frame = ttk.Frame(top, padding="10")
    frame.pack(fill=tk.BOTH, expand=True)
    
    text_area = tk.Text(frame, wrap=tk.WORD, font=("微软雅黑", 10), bg="#f0f0f0", relief=tk.FLAT)
    text_area.pack(fill=tk.BOTH, expand=True)
    
    content = "\n".join(lines)
    text_area.insert(tk.END, content)
    text_area.config(state=tk.DISABLED)

    def close_all():
        if top.winfo_exists():
            top.destroy()
        if root.winfo_exists():
            root.destroy()

    top.protocol("WM_DELETE_WINDOW", close_all)
    
    # 如果没有错误，则定时关闭
    if not has_error:
        top.after(auto_close_ms, close_all)
        ttk.Label(frame, text=f"{auto_close_ms//1000} 秒后自动关闭", foreground="gray").pack(pady=5)
    else:
        top.title("签到异常 (需手动关闭)")
        ttk.Button(frame, text="确 定", command=close_all).pack(pady=5)
    
    root.mainloop()


def _parse_cli(argv: list[str]) -> dict:
    """
    解析命令行参数（尽量保持兼容现有“无 argparse”实现）。

    支持：
    - --mod / --mod-mode
    - --signin-only / -s
    - --no-onedragon / --skip-onedragon
    - --preset <id> 或 --preset=<id>
    """
    force_mod = False
    signin_only = False
    no_onedragon = False
    preset_id: str | None = None

    i = 0
    while i < len(argv):
        a_raw = argv[i]
        a = (a_raw or "").strip()
        a_low = a.lower()

        if a_low in {"--mod", "--mod-mode"}:
            force_mod = True
            i += 1
            continue
        if a_low in {"--signin-only", "-s"}:
            signin_only = True
            i += 1
            continue
        if a_low in {"--no-onedragon", "--skip-onedragon"}:
            no_onedragon = True
            i += 1
            continue

        if a_low == "--preset":
            if i + 1 < len(argv):
                preset_id = str(argv[i + 1]).strip()
                i += 2
                continue
            # 参数缺失：保留为 None（后续走默认逻辑/报错提示）
            i += 1
            continue
        if a_low.startswith("--preset="):
            preset_id = a.split("=", 1)[1].strip()
            i += 1
            continue

        i += 1

    return {
        "force_mod": force_mod,
        "signin_only": signin_only,
        "no_onedragon": no_onedragon,
        "preset_id": preset_id or None,
    }


def _windows_toggle_popup(*, force_mod: bool, signin_only: bool, no_onedragon: bool) -> dict | None:
    """
    Windows 下弹出简易弹窗让用户选择本次临时开关。
    非 Windows 或无 tkinter 时返回 None（不弹窗）。
    """
    if sys.platform != "win32":
        return None

    _set_dpi_awareness()
    try:
        import tkinter as tk
        from tkinter import ttk
    except ModuleNotFoundError:
        return None

    root = tk.Tk()
    root.withdraw()
    win = tk.Toplevel(root)
    win.title("启动选项")
    win.geometry("360x200")
    win.attributes("-topmost", True)

    frame = ttk.Frame(win, padding="12")
    frame.pack(fill=tk.BOTH, expand=True)

    v_signin_only = tk.BooleanVar(value=bool(signin_only))
    v_no_onedragon = tk.BooleanVar(value=bool(no_onedragon))
    v_force_mod = tk.BooleanVar(value=bool(force_mod))

    ttk.Label(frame, text="选择本次运行的临时开关（不会写入配置）").pack(anchor="w", pady=(0, 8))
    ttk.Checkbutton(frame, text="仅签到（不启动游戏）", variable=v_signin_only).pack(anchor="w", pady=2)
    ttk.Checkbutton(frame, text="跳过一条龙", variable=v_no_onedragon).pack(anchor="w", pady=2)
    ttk.Checkbutton(frame, text="强制 Mod", variable=v_force_mod).pack(anchor="w", pady=2)

    result: dict | None = None

    def on_ok():
        nonlocal result
        result = {
            "signin_only": bool(v_signin_only.get()),
            "no_onedragon": bool(v_no_onedragon.get()),
            "force_mod": bool(v_force_mod.get()),
        }
        try:
            win.destroy()
            root.destroy()
        except Exception:
            pass

    def on_cancel():
        nonlocal result
        result = None
        try:
            win.destroy()
            root.destroy()
        except Exception:
            pass

    btns = ttk.Frame(frame)
    btns.pack(fill=tk.X, pady=(12, 0))
    ttk.Button(btns, text="确 定", command=on_ok).pack(side=tk.RIGHT, padx=(6, 0))
    ttk.Button(btns, text="取 消", command=on_cancel).pack(side=tk.RIGHT)

    win.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()
    return result


def _windows_preset_select_popup(*, presets: list[dict], active_preset_id: str = "") -> str | None:
    """
    Windows 下弹出“选择预设”窗口（仅选择已有预设）。
    非 Windows 或无 tkinter 时返回 None（不弹窗）。
    """
    if sys.platform != "win32":
        return None

    if not isinstance(presets, list) or not presets:
        return None

    _set_dpi_awareness()
    try:
        import tkinter as tk
        from tkinter import ttk
    except ModuleNotFoundError:
        return None

    # 生成 label -> id 映射；若重名则用短 id 区分显示
    items: list[tuple[str, str]] = []
    name_count: dict[str, int] = {}
    for p in presets:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        if not pid:
            continue
        name = str(p.get("name") or pid).strip() or pid
        name_count[name] = name_count.get(name, 0) + 1
        items.append((name, pid))

    if not items:
        return None

    labels: list[str] = []
    label_to_id: dict[str, str] = {}
    for name, pid in items:
        label = name
        if name_count.get(name, 0) > 1:
            label = f"{name} ({pid[:6]})"
        # 极端情况：label 仍冲突（例如同名同前 6 位），再追加完整 id
        if label in label_to_id:
            label = f"{label} ({pid})"
        labels.append(label)
        label_to_id[label] = pid

    root = tk.Tk()
    root.withdraw()
    win = tk.Toplevel(root)
    win.title("选择预设")
    win.geometry("420x190")
    win.attributes("-topmost", True)

    frame = ttk.Frame(win, padding="12")
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="请选择要执行的流程预设：").pack(anchor="w", pady=(0, 8))

    v_label = tk.StringVar(value="")
    combo = ttk.Combobox(frame, textvariable=v_label, values=labels, state="readonly")
    combo.pack(fill=tk.X, pady=(0, 8))

    # 默认选中 active preset（若存在），否则选第一个
    default_label = labels[0]
    if active_preset_id:
        for label, pid in label_to_id.items():
            if pid == active_preset_id:
                default_label = label
                break
    v_label.set(default_label)

    result: str | None = None

    def on_ok():
        nonlocal result
        sel = str(v_label.get() or "")
        result = label_to_id.get(sel)
        try:
            win.destroy()
            root.destroy()
        except Exception:
            pass

    def on_cancel():
        nonlocal result
        result = None
        try:
            win.destroy()
            root.destroy()
        except Exception:
            pass

    btns = ttk.Frame(frame)
    btns.pack(fill=tk.X, pady=(12, 0))
    ttk.Button(btns, text="开 始", command=on_ok).pack(side=tk.RIGHT, padx=(6, 0))
    ttk.Button(btns, text="取 消", command=on_cancel).pack(side=tk.RIGHT)

    win.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()
    return result

def main():
    try:
        cli = _parse_cli([a for a in sys.argv[1:] if isinstance(a, str)])
        force_mod = bool(cli["force_mod"])
        signin_only = bool(cli["signin_only"])
        no_onedragon = bool(cli["no_onedragon"])
        preset_id_cli = cli.get("preset_id")
        preset_id = preset_id_cli
        preset_from_cli = bool(preset_id_cli)

        pm_for_selected: FlowPresetManager | None = None

        # 未传 preset：优先弹出“选择预设”窗口；若没有任何预设则回退旧的“临时开关”窗口
        if not preset_id:
            try:
                pm0 = FlowPresetManager()
                pm0.load()
                presets = pm0.list()
            except Exception:
                presets = []
                pm0 = None  # type: ignore[assignment]

            if presets:
                chosen = _windows_preset_select_popup(
                    presets=presets,
                    active_preset_id=str(getattr(pm0, "data", {}).get("active_preset_id") or ""),
                )
                if not chosen:
                    # 用户取消：直接退出，不继续启动
                    sys.exit(0)
                preset_id = str(chosen)
                preset_from_cli = False
                pm_for_selected = pm0
            else:
                overrides = _windows_toggle_popup(
                    force_mod=force_mod,
                    signin_only=signin_only,
                    no_onedragon=no_onedragon,
                )
                if isinstance(overrides, dict):
                    force_mod = bool(overrides.get("force_mod", force_mod))
                    signin_only = bool(overrides.get("signin_only", signin_only))
                    no_onedragon = bool(overrides.get("no_onedragon", no_onedragon))
        
        accounts = account_manager.get_accounts()
        settings = account_manager.get_settings()

        suppress_popup = bool(preset_from_cli)
        preset_flow = None
        if preset_id:
            pm = pm_for_selected or FlowPresetManager()
            pm.load()
            try:
                preset = pm.get(preset_id)
                preset_flow = preset.get("flow") if isinstance(preset, dict) else None
                if not isinstance(preset_flow, list):
                    preset_flow = []
            except KeyError:
                raise RuntimeError(f"未找到预设: {preset_id}")
        
        # 检查今天是否已经签到过
        today = datetime.date.today().isoformat()
        last_date = settings.get("last_signin_date", "")
        daily_once = settings.get("daily_signin_once", True)
        
        skip_signin = False
        if daily_once and last_date == today and not signin_only:
            skip_signin = True

        done_event = threading.Event()
        result_holder = {"lines": [], "has_error": False, "quiet": False, "skipped": skip_signin}

        def signin_task():
            try:
                if skip_signin:
                    result_holder["quiet"] = True
                    return
                lines, has_error, quiet = _collect_signin_results(accounts)
                result_holder["lines"] = lines
                result_holder["has_error"] = has_error
                result_holder["quiet"] = quiet
            except Exception as e:
                result_holder["lines"] = [f"签到过程出错: {e}"]
                result_holder["has_error"] = True
                result_holder["quiet"] = False
            finally:
                done_event.set()

        threading.Thread(target=signin_task, daemon=True).start()
        
        if not signin_only:
            if preset_id:
                # preset：按 flow 执行（顺序由 preset.flow 唯一决定），且不弹窗
                run_flow(
                    preset_flow or [],
                    settings,
                    force_mod=force_mod,
                    no_onedragon=no_onedragon,
                )
            else:
                # 无 preset：保留旧版“根据 settings 自动决定启动顺序”的逻辑
                game_launcher.launch(
                    settings=None,
                    force_mod=force_mod,
                    no_onedragon=no_onedragon,
                )
        
        if skip_signin:
            # 如果跳过签到，不需要等待或显示弹窗
            if not signin_only:
                log.info("正在等待一条龙切换任务完成...")
                game_launcher.wait_for_launcher()
            sys.exit(0)
            
        done_event.wait()
        
        if result_holder["quiet"] and not result_holder["has_error"]:
            if not signin_only:
                log.info("正在等待一条龙切换任务完成...")
                game_launcher.wait_for_launcher()
            sys.exit(0)

        if suppress_popup:
            # preset 模式：不弹窗。仅在异常时输出到 stderr 便于排查。
            if result_holder["has_error"]:
                try:
                    print("\n".join(result_holder["lines"]), file=sys.stderr)
                except Exception:
                    pass
            if not signin_only:
                log.info("正在等待一条龙切换任务完成...")
                game_launcher.wait_for_launcher()
            sys.exit(0)

        _show_result_popup(result_holder["lines"], result_holder["has_error"], auto_close_ms=5000)
        
    except Exception as e:
        # preset 模式/无 GUI 时不应强制弹窗；保持兼容，尽量退化为 stderr 输出。
        try:
            suppress = bool(locals().get("preset_id"))
        except Exception:
            suppress = False
        if suppress:
            try:
                print(f"运行出错: {e}", file=sys.stderr)
            except Exception:
                pass
        else:
            _show_result_popup([f"运行出错: {e}"], True, auto_close_ms=5000)
            time.sleep(1)
    finally:
        if not locals().get('signin_only', False):
            log.info("主程序准备退出，检查后台任务...")
            game_launcher.wait_for_launcher()
        sys.exit(0)

if __name__ == "__main__":
    main()
