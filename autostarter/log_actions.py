"""
统一动作日志格式化与输出工具。

注意：本模块在 import 时不应触发任何副作用（例如初始化日志系统、创建目录等）。
"""

from __future__ import annotations

import re
from typing import Any, Dict


_SENSITIVE_KEY_PATTERN = re.compile(r"(cookie|stoken|token|mid|stuid)", re.IGNORECASE)

# 日志显示层的中文映射（调用侧仍可使用英文标识，便于代码内部统一）
_MODULE_ZH = {
    "Flow": "流程",
    "Launcher": "启动器",
    "Config": "配置",
    "ConfigPaths": "配置",
    "AccountManager": "账号管理",
    "FlowPresets": "预设",
    "Preset": "预设",
    "GUI": "界面",
    "GUIv2": "界面",
}

_STATUS_ZH = {
    "start": "开始",
    "ok": "成功",
    "skip": "跳过",
    "fail": "失败",
}

# 常见动作名的中文映射（仅做显示，不影响调用方）
_ACTION_ZH = {
    # flow steps
    "external_launcher": "外置启动器",
    "mod": "Mod",
    "bettergi": "BetterGI",
    "onedragon": "一条龙",
    "genshin_direct": "直接启动原神",
    "wait": "等待",
    # misc
    "migrate_file": "迁移配置文件",
    "save": "保存",
    "update_flow": "更新流程",
    "upgrade": "升级预设",
    "run_preset": "一键启动预设",
    "create_shortcut": "生成桌面快捷方式",
}


def _normalize_spaces(s: str) -> str:
    # 日志中避免出现空格导致解析困难：将空格替换为下划线
    return s.replace(" ", "_")


def _format_value(key: str, value: Any) -> str:
    if _SENSITIVE_KEY_PATTERN.search(key):
        return "masked"
    if isinstance(value, bool):
        return "true" if value else "false"
    return _normalize_spaces(str(value))


def format_action_line(module: str, action: str, status: str, **kv: Any) -> str:
    """
    输出格式：
      "[module][action] status key=value key=value ..."

    规则：
    - kv 按 key 排序
    - bool 输出 true/false（小写）
    - 空格替换为下划线
    - 敏感 key（包含 cookie/stoken/token/mid/stuid，大小写不敏感）输出 masked
    """
    # 显示层：模块/状态中文化（key 仍保持英文，便于检索）
    mod_in = str(module)
    act_in = str(action)
    st_in = str(status)

    mod = _normalize_spaces(_MODULE_ZH.get(mod_in, mod_in))
    act = _normalize_spaces(_ACTION_ZH.get(act_in, act_in))
    st = _normalize_spaces(_STATUS_ZH.get(st_in, st_in))

    base = f"[{mod}][{act}] {st}"
    if not kv:
        return base

    items: Dict[str, Any] = dict(kv)
    parts = []
    for k in sorted(items.keys(), key=lambda x: str(x)):
        key_s = _normalize_spaces(str(k))
        val_s = _format_value(str(k), items[k])
        parts.append(f"{key_s}={val_s}")
    return base + " " + " ".join(parts)


def log_action(module: str, action: str, status: str, **kv: Any) -> str:
    """
    记录动作日志：
    - status == "fail" 使用 log.error
    - 其他使用 log.info
    """
    # 重要：避免 import 时触发 loghelper.setup_logging() 的副作用
    from .loghelper import log  # pylint: disable=import-outside-toplevel

    line = format_action_line(module=module, action=action, status=status, **kv)
    if status == "fail":
        log.error(line)
    else:
        log.info(line)
    return line
