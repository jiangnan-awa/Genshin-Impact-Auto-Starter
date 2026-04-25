from __future__ import annotations
import re
from typing import Any, Dict
_SENSITIVE_KEY_PATTERN = re.compile(r"(cookie|stoken|token|mid|stuid)", re.IGNORECASE)
_MODULE_ZH = {
    "Flow": "流程",
    "Launcher": "启动器",
    "Config": "配置",
    "ConfigPaths": "配置",
    "AccountManager": "账号管理",
    "FlowPresets": "预设",
    "Preset": "预设",
    "GUI": "界面",
    "GUI": "界面",
}
_STATUS_ZH = {
    "start": "开始",
    "ok": "成功",
    "skip": "跳过",
    "fail": "失败",
}
_KEY_ZH = {
    "reason": "原因",
    "count": "数量",
    "file": "文件",
    "from_file": "源文件",
    "to_file": "目标文件",
    "steps_count": "步骤数",
    "presets_count": "预设数",
    "seconds": "秒数",
    "preset_id": "预设ID",
}
_REASON_ZH = {
    "src_missing": "源文件不存在",
    "dst_exists": "目标已存在",
    "save_failed": "保存失败",
    "write_settings_failed": "写入设置文件失败",
    "backup_accounts_failed": "备份账号文件失败",
    "rewrite_accounts_failed": "重写账号文件失败",
    "account_not_found": "未找到账号",
    "not_available": "不可用",
    "no_onedragon": "已跳过一条龙",
    "skipped": "已跳过",
    "exception": "发生异常",
}
_ACTION_ZH = {
    "external_launcher": "外置启动器",
    "mod": "Mod",
    "bettergi": "BetterGI",
    "onedragon": "一条龙",
    "genshin_direct": "直接启动原神",
    "wait": "等待",
    "migrate_file": "迁移配置文件",
    "save": "保存",
    "update_flow": "更新流程",
    "upgrade": "升级预设",
    "run_preset": "一键启动预设",
    "create_shortcut": "生成桌面快捷方式",
}
def _normalize_spaces(s: str) -> str:
    return s.replace(" ", "_")
def _format_value(key: str, value: Any) -> str:
    if _SENSITIVE_KEY_PATTERN.search(key):
        return "masked"
    if isinstance(value, bool):
        return "true" if value else "false"
    return _normalize_spaces(str(value))
def _translate_value(key: str, value: Any) -> Any:
    key_s = str(key or "")
    key_norm = key_s.strip().lower()
    if key_norm in {"reason", "原因"}:
        if isinstance(value, str):
            v = value.strip()
            return _REASON_ZH.get(v, value)
    return value
def format_action_line(module: str, action: str, status: str, **kv: Any) -> str:
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
        k_raw = str(k)
        k_show = _KEY_ZH.get(k_raw, k_raw)
        v_translated = _translate_value(k_raw, items[k])
        key_s = _normalize_spaces(str(k_show))
        val_s = _format_value(k_raw, v_translated)
        parts.append(f"{key_s}={val_s}")
    return base + " " + " ".join(parts)
def log_action(module: str, action: str, status: str, **kv: Any) -> str:
    from .loghelper import log  # pylint: disable=import-outside-toplevel
    line = format_action_line(module=module, action=action, status=status, **kv)
    if status == "fail":
        log.error(line)
    else:
        log.info(line)
    return line
