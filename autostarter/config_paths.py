from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from typing import Optional
def detect_base_path() -> str:
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
