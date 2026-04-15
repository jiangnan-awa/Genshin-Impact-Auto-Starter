import sys
import time
import threading
import datetime
import ctypes
from .account_manager import account_manager
from .mihoyo_api import mihoyo_client
from .launcher import game_launcher
from .loghelper import log

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

def main():
    try:
        args = [a.strip().lower() for a in sys.argv[1:] if isinstance(a, str)]
        force_mod = any(a in {"--mod", "--mod-mode"} for a in args)
        signin_only = any(a in {"--signin-only", "-s"} for a in args)
        no_onedragon = any(a in {"--no-onedragon", "--skip-onedragon"} for a in args)
        
        accounts = account_manager.get_accounts()
        settings = account_manager.get_settings()
        
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
            game_launcher.launch(force_mod=force_mod, no_onedragon=no_onedragon)
        
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
            
        _show_result_popup(result_holder["lines"], result_holder["has_error"], auto_close_ms=5000)
        
    except Exception as e:
        _show_result_popup([f"运行出错: {e}"], True, auto_close_ms=5000)
        time.sleep(1)
    finally:
        if not locals().get('signin_only', False):
            log.info("主程序准备退出，检查后台任务...")
            game_launcher.wait_for_launcher()
        sys.exit(0)

if __name__ == "__main__":
    main()
