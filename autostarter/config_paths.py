from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Optional


def detect_base_path() -> str:
    """
    探测应用的 base_path：
    - frozen（PyInstaller 等打包）环境：取 sys.executable 所在目录
    - 非 frozen：取当前模块所在目录（与旧版 account_manager 行为一致）
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


@dataclass(frozen=True)
class ConfigPaths:
    base_path: str
    config_dir: str
    accounts_file: str
    settings_file: str
    presets_file: str


def get_config_paths(base_path: Optional[str] = None) -> ConfigPaths:
    bp = base_path or detect_base_path()
    cfg_dir = os.path.join(bp, "config")
    return ConfigPaths(
        base_path=bp,
        config_dir=cfg_dir,
        accounts_file=os.path.join(cfg_dir, "accounts.json"),
        settings_file=os.path.join(cfg_dir, "settings.json"),
        presets_file=os.path.join(cfg_dir, "presets.json"),
    )


def migrate_root_files_to_config_dir(base_path: str) -> None:
    """
    将旧版“根目录”配置文件迁移到 config/ 目录下（move，不拷贝）：
      - accounts.json
      - settings.json
      - presets.json
      - accounts.json.bak

    迁移策略：
    - 仅当 src 存在 且 dst 不存在时才迁移
    - 不覆盖已存在的目标文件（dst 已存在则跳过，保留 src）
    """
    paths = get_config_paths(base_path)
    candidates = [
        "accounts.json",
        "settings.json",
        "presets.json",
        "accounts.json.bak",
    ]

    for filename in candidates:
        src = os.path.join(paths.base_path, filename)
        dst = os.path.join(paths.config_dir, filename)
        # 统一动作日志（注意：log_action 内部导入 loghelper，避免 import 副作用）
        from .log_actions import log_action  # pylint: disable=import-outside-toplevel

        if not os.path.exists(src):
            log_action("ConfigPaths", "migrate_file", "skip", file=filename, reason="src_missing")
            continue
        if os.path.exists(dst):
            # 不覆盖：保留 src
            log_action("ConfigPaths", "migrate_file", "skip", file=filename, reason="dst_exists")
            continue
        try:
            log_action("ConfigPaths", "migrate_file", "start", file=filename)
            os.makedirs(paths.config_dir, exist_ok=True)
            shutil.move(src, dst)
            log_action("ConfigPaths", "migrate_file", "ok", file=filename)
        except Exception:
            # 迁移失败：尽量不影响后续启动
            log_action("ConfigPaths", "migrate_file", "fail", file=filename, reason="exception")
            continue
