import time
import os
import sys
import ctypes
try:
    import winreg  # type: ignore
except ModuleNotFoundError:  # 非 Windows 环境
    winreg = None  # type: ignore
try:
    import tkinter as tk  # type: ignore
    from tkinter import messagebox  # type: ignore
except ModuleNotFoundError:  # 无图形环境 / 未安装 tkinter
    tk = None  # type: ignore
    messagebox = None  # type: ignore
try:
    from selenium import webdriver  # type: ignore
    from selenium.webdriver.common.by import By  # type: ignore
    from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
    from selenium.webdriver.support import expected_conditions as EC  # type: ignore
    from selenium.webdriver.edge.service import Service as EdgeService  # type: ignore
    from selenium.webdriver.edge.options import Options as EdgeOptions  # type: ignore
    from selenium.webdriver.chrome.service import Service as ChromeService  # type: ignore
    from selenium.webdriver.chrome.options import Options as ChromeOptions  # type: ignore
    from selenium.webdriver.firefox.service import Service as FirefoxService  # type: ignore
    from selenium.webdriver.firefox.options import Options as FirefoxOptions  # type: ignore
except ModuleNotFoundError:
    webdriver = None  # type: ignore
    By = WebDriverWait = EC = None  # type: ignore
    EdgeService = EdgeOptions = None  # type: ignore
    ChromeService = ChromeOptions = None  # type: ignore
    FirefoxService = FirefoxOptions = None  # type: ignore
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
from .driver_downloader import auto_setup_driver
import webbrowser
def _require_gui_and_selenium():
    if tk is None:
        raise RuntimeError("当前环境缺少 tkinter，无法进行图形化 Cookie 登录。")
    if webdriver is None:
        raise RuntimeError("当前环境缺少 selenium，无法进行自动化 Cookie 登录。")
def get_default_browser_type():
    if winreg is None:
        return None
    try:
        key_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            if not prog_id:
                return None
            prog_id = prog_id.lower()
            if "chrome" in prog_id:
                return 'chrome'
    except Exception:
        pass
    return None
def show_manual_download_window(browser_name, download_url, driver_name):
    if tk is None:
        raise RuntimeError("当前环境缺少 tkinter，无法显示下载引导窗口。")
    root = tk.Tk()
    root.title("驱动下载协助")
    root.attributes('-topmost', True)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    width, height = 500, 250
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.configure(bg='#333333')
    label_title = tk.Label(root, text="自动下载驱动失败", bg='#333333', fg='#f44336', 
                          font=("Microsoft YaHei", 14, "bold"))
    label_title.pack(pady=(20, 10))
    msg = f"由于网络限制，程序无法自动下载 {browser_name} 驱动。\n请点击下方按钮手动下载，并将解压后的\n {driver_name} 放入程序目录。"
    label_msg = tk.Label(root, text=msg, bg='#333333', fg='white', 
                        font=("Microsoft YaHei", 10), justify=tk.CENTER)
    label_msg.pack(pady=10)
    def open_link():
        webbrowser.open(download_url)
    btn_open = tk.Button(root, text="一键打开下载链接", command=open_link,
                        bg="#2196F3", fg="white", font=("Microsoft YaHei", 10, "bold"),
                        padx=20, pady=8, bd=0, cursor="hand2")
    btn_open.pack(pady=10)
    btn_close = tk.Button(root, text="我知道了", command=root.destroy,
                         bg="#666666", fg="white", font=("Microsoft YaHei", 10),
                         padx=15, pady=5, bd=0, cursor="hand2")
    btn_close.pack(pady=5)
    root.mainloop()
def create_driver(browser_type, status_win=None):
    _require_gui_and_selenium()
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    try:
        if browser_type == 'chrome':
            options = ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            driver_path = os.path.join(base_path, "chromedriver.exe")
            if not os.path.exists(driver_path):
                if not auto_setup_driver('chrome', status_callback=lambda msg: update_status(status_win, msg)):
                    from .driver_downloader import get_chrome_version, get_chrome_download_url
                    ver = get_chrome_version()
                    url = get_chrome_download_url(ver) if ver else "https://googlechromelabs.github.io/chrome-for-testing/"
                    if ver and int(ver.split('.')[0]) >= 115:
                        url = "https://googlechromelabs.github.io/chrome-for-testing/"
                        msg_tip = (
                            "您的 Chrome 版本较新 (Canary/Dev)，自动下载因网络原因失败。\n\n"
                            "请尝试以下方案：\n"
                            "1. (推荐) 访问 chrome.dashgame.com 搜索 '143' 下载\n"
                            "2. (备选) 访问 googlechromelabs.github.io (需魔法)\n\n"
                            "下载后将 chromedriver.exe 解压到程序同级目录即可。"
                        )
                        messagebox.showinfo("手动下载提示", msg_tip)
                    if status_win: status_win.destroy()
                    show_manual_download_window("Chrome", url, "chromedriver.exe")
                    return None
            if os.path.exists(driver_path):
                service = ChromeService(executable_path=driver_path)
                return webdriver.Chrome(service=service, options=options)
            try:
                update_status(status_win, "正在尝试调用系统内置驱动管理...")
                return webdriver.Chrome(options=options)
            except Exception as se:
                raise Exception("无法启动 Chrome 浏览器。请检查网络连接或手动下载 chromedriver.exe 放在程序目录下。")
        raise Exception("当前版本仅支持 Chrome 浏览器获取 Cookie")
    except Exception as e:
        raise e
    return None
def update_status(win, message):
    if win:
        try:
            if win.cancelled:
                raise Exception("用户取消了启动")
            for child in win.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(text=message)
            win.update()
        except Exception as e:
            if "用户取消" in str(e):
                raise e
            pass
def get_driver(status_win=None):
    default_browser = get_default_browser_type()
    update_status(status_win, f"检测到默认浏览器: {default_browser if default_browser else '未知'}\n正在准备启动...")
    priority = ['chrome']
    last_error = ""
    for browser in priority:
        try:
            update_status(status_win, f"正在尝试启动 {browser} 浏览器...")
            driver = create_driver(browser, status_win)
            if driver:
                update_status(status_win, f"成功启动 {browser} 浏览器")
                return driver
        except Exception as e:
            last_error = str(e)
            update_status(status_win, f"启动 {browser} 失败，正在尝试下一个...")
    raise Exception(f"所有浏览器启动尝试均失败。最后一次错误: {last_error}")
def show_confirm_window(title, message, button_text):
    root = tk.Tk()
    root.title(title)
    root.attributes('-topmost', True)
    root.overrideredirect(True)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    width = int(screen_width * 0.8)
    height = 60
    x = (screen_width - width) // 2
    y = screen_height - height - 40
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.configure(bg='#333333')
    frame = tk.Frame(root, bg='#333333')
    frame.pack(fill=tk.BOTH, expand=True, padx=20)
    label = tk.Label(frame, text=message, fg="white", bg='#333333', 
                    font=("Microsoft YaHei", 11))
    label.pack(side=tk.LEFT, pady=10)
    result = {"status": "pending"}
    def on_confirm():
        result["status"] = "confirmed"
        root.destroy()
    def on_cancel():
        result["status"] = "cancelled"
        root.destroy()
    btn_confirm = tk.Button(frame, text=button_text, command=on_confirm, 
                           bg="#4CAF50", fg="white", font=("Microsoft YaHei", 10, "bold"),
                           padx=20, pady=5, bd=0, cursor="hand2")
    btn_confirm.pack(side=tk.RIGHT, padx=10, pady=10)
    btn_cancel = tk.Button(frame, text="取消获取", command=on_cancel, 
                          bg="#f44336", fg="white", font=("Microsoft YaHei", 10),
                          padx=15, pady=5, bd=0, cursor="hand2")
    btn_cancel.pack(side=tk.RIGHT, padx=10, pady=10)
    def start_move(event):
        root.x = event.x
        root.y = event.y
    def stop_move(event):
        root.x = None
        root.y = None
    def on_move(event):
        deltax = event.x - root.x
        deltay = event.y - root.y
        x = root.winfo_x() + deltax
        y = root.winfo_y() + deltay
        root.geometry(f"+{x}+{y}")
    root.bind("<ButtonPress-1>", start_move)
    root.bind("<ButtonRelease-1>", stop_move)
    root.bind("<B1-Motion>", on_move)
    root.mainloop()
    return result["status"] == "confirmed"
def show_status_window(message):
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    width, height = 500, 160
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.configure(bg='#333333')
    root.cancelled = False
    def on_cancel():
        root.cancelled = True
        root.destroy()
    label = tk.Label(root, text=message, bg='#333333', fg='white', 
                    font=("Microsoft YaHei", 11), wraplength=460)
    label.pack(expand=True, padx=20, pady=(20, 10))
    btn_cancel = tk.Button(root, text="取消启动", command=on_cancel,
                          bg="#f44336", fg="white", font=("Microsoft YaHei", 10),
                          padx=20, pady=5, bd=0, cursor="hand2")
    btn_cancel.pack(pady=(0, 20))
    root.update()
    return root
def get_cookie_auto():
    driver = None
    status_win = None
    try:
        status_win = show_status_window("正在准备浏览器环境，请稍候...")
        driver = get_driver(status_win)
        if status_win:
            status_win.destroy()
            status_win = None
        cookie_dict = {}
        driver.get("https://bbs.mihoyo.com/ys/")
        if not show_confirm_window(
            "登录引导 - 步骤 1/2",
            "第一步：在米游社网页完成登录后，点击“已完成”。",
            "已完成"
        ):
            return None
        driver.get("https://user.mihoyo.com/")
        if not show_confirm_window(
            "登录引导 - 步骤 2/2",
            "第二步：在米哈游通行证网页确认已登录后，点击“获取 Cookie”。",
            "获取 Cookie"
        ):
            return None
        time.sleep(2)
        for c in driver.get_cookies():
            cookie_dict[c['name']] = c['value']
        if cookie_dict:
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            return cookie_str
        return None
    except Exception as e:
        if "用户取消" not in str(e):
            logger.error(f"自动化过程出错: {e}")
            messagebox.showerror("启动失败", f"无法启动浏览器驱动，请检查网络或手动安装驱动。\n错误信息: {e}")
        return None
    finally:
        if status_win:
            try:
                status_win.destroy()
            except:
                pass
        if driver:
            try:
                driver.quit()
            except:
                pass
if __name__ == "__main__":
    print(get_cookie_auto())
