"""
桌面快捷方式相关工具（纯逻辑，无副作用，便于单测）。
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
from typing import Callable


def sanitize_windows_filename(name: str) -> str:
    """
    Windows 文件名净化：
    - 移除 <>:"/\\|?* 与控制字符
    - 去除尾部空格/点
    """
    s = (name or "").strip()
    # 注意：这里必须使用真实的控制字符范围 \x00-\x1f，
    # 不能写成 \\x00-\\x1f，否则会形成错误的字符集范围导致正常字母（如 M/F）被误删。
    s = re.sub(r'[<>:"/\\\\|?*\x00-\x1f]', "", s)
    s = s.rstrip(" .")
    return s or "Preset"


def resolve_autostarter_target_exe(
    *,
    base_path: str,
    current_executable: str,
    exists_func: Callable[[str], bool] = os.path.exists,
) -> str:
    """
    生成桌面快捷方式时，目标应指向主程序 AutoStarter.exe，而不是配置程序 AutoStarterConfig.exe。

    - 在打包版中，配置界面运行时 sys.executable 往往是 AutoStarterConfig.exe。
    - 这里优先返回同目录下的 AutoStarter.exe（若存在）；否则回退 current_executable。
    """
    candidate = os.path.join(base_path, "AutoStarter.exe")
    if exists_func(candidate):
        return candidate
    return current_executable


def build_shortcut_basename(
    *,
    preset_name: str,
    preset_id: str,
    desktop_dir: str,
    exists_func: Callable[[str], bool] = os.path.exists,
) -> str:
    """
    计算 .lnk 文件的“基础名”（不含 .lnk）。

    需求：生成的快捷方式名称应与软件内预设名称一致。
    因此这里**不再**为避免覆盖而追加后缀；同名时直接覆盖旧快捷方式即可。
    """
    return sanitize_windows_filename(preset_name)


def build_powershell_create_shortcut_command(
    *,
    lnk_path: str,
    target_path: str,
    arguments: str,
    working_dir: str,
) -> list[str]:
    """
    构造用于创建 .lnk 的 PowerShell 命令行（使用 -EncodedCommand 避免中文/Unicode 编码问题）。
    """
    # PowerShell 脚本中用单引号字面量，单引号需要翻倍转义
    def _ps_sq(s: str) -> str:
        return "'" + (s or "").replace("'", "''") + "'"

    script = (
        "$ws=New-Object -ComObject WScript.Shell;"
        f"$s=$ws.CreateShortcut({_ps_sq(lnk_path)});"
        f"$s.TargetPath={_ps_sq(target_path)};"
        f"$s.Arguments={_ps_sq(arguments)};"
        f"$s.WorkingDirectory={_ps_sq(working_dir)};"
        "$s.Save();"
    )

    b64 = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        b64,
    ]


def create_windows_shortcut(
    *,
    lnk_path: str,
    target_path: str,
    arguments: str,
    working_dir: str,
) -> None:
    """
    创建 Windows .lnk 快捷方式。

    优先使用 pywin32（win32com）直接调用 WScript.Shell，避免 PowerShell 在少数环境下的编码问题；
    若 win32com 不可用，则由调用方回退到 PowerShell -EncodedCommand 方案。
    """
    import win32com.client  # type: ignore

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(lnk_path)
    shortcut.TargetPath = target_path
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = working_dir
    shortcut.Save()


def run_powershell_hidden(cmd: list[str]):
    """
    运行 PowerShell 命令，并尽可能隐藏控制台窗口（Windows）。
    - 非 Windows 环境下 creationflags 不生效，但也不影响运行/单测。
    """
    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        creationflags=creationflags,
    )
