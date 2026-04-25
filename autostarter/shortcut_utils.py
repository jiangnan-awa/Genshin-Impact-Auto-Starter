from __future__ import annotations
import base64
import os
import re
import subprocess
from typing import Callable
def sanitize_windows_filename(name: str) -> str:
    s = (name or "").strip()
    s = re.sub(r'[<>:"/\\\\|?*\x00-\x1f]', "", s)
    s = s.rstrip(" .")
    return s or "Preset"
def resolve_autostarter_target_exe(
    *,
    base_path: str,
    current_executable: str,
    exists_func: Callable[[str], bool] = os.path.exists,
) -> str:
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
    return sanitize_windows_filename(preset_name)
def build_powershell_create_shortcut_command(
    *,
    lnk_path: str,
    target_path: str,
    arguments: str,
    working_dir: str,
) -> list[str]:
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
    import win32com.client  # type: ignore
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(lnk_path)
    shortcut.TargetPath = target_path
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = working_dir
    shortcut.Save()
def run_powershell_hidden(cmd: list[str]):
    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        creationflags=creationflags,
    )
