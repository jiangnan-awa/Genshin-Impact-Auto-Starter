import sys
import time
import threading
import datetime
import ctypes
from .account_manager import account_manager
from .mihoyo_api import mihoyo_client
from .launcher import game_launcher
from .loghelper import log
from .presets import PresetManager

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

def main():
    try:
        cli = _parse_cli([a for a in sys.argv[1:] if isinstance(a, str)])
        force_mod = bool(cli["force_mod"])
        signin_only = bool(cli["signin_only"])
        no_onedragon = bool(cli["no_onedragon"])
        preset_id = cli.get("preset_id")

        # 未传 preset：Windows 下提供一次性临时开关弹窗
        if not preset_id:
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

        suppress_popup = bool(preset_id)
        preset_settings = None
        if preset_id:
            pm = PresetManager()
            pm.load()
            try:
                preset = pm.get(preset_id)
                preset_settings = preset.get("settings") if isinstance(preset, dict) else None
                if not isinstance(preset_settings, dict):
                    preset_settings = {}
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
            # 传入 preset 时使用预设 settings 启动，并且不弹窗
            game_launcher.launch(
                settings=preset_settings,
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
