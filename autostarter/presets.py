from __future__ import annotations

import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional


def _default_base_path() -> str:
    """
    与 autostarter/account_manager.py 的 base_path 规则保持一致：
    - frozen（打包）环境：取 sys.executable 所在目录
    - 非 frozen：取当前模块所在目录
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class PresetManager:
    """
    负责读写 presets.json（与 accounts.json/settings.json 同目录）。

    数据结构（version=1）：
    {
      "version": 1,
      "active_preset_id": "",
      "presets": [{"id": "...", "name": "...", "settings": {...}, ...}]
    }
    """

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or _default_base_path()
        self.file_path = os.path.join(self.base_path, "presets.json")
        self.data: Dict[str, Any] = {
            "version": 1,
            "active_preset_id": "",
            "presets": [],
        }

    def _normalize(self) -> None:
        if not isinstance(self.data, dict):
            self.data = {"version": 1, "active_preset_id": "", "presets": []}
            return
        if not isinstance(self.data.get("version"), int):
            self.data["version"] = 1
        if not isinstance(self.data.get("active_preset_id"), str):
            self.data["active_preset_id"] = ""
        presets = self.data.get("presets")
        if not isinstance(presets, list):
            self.data["presets"] = []

    def load(self) -> None:
        if not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                self.data.update(obj)
                self._normalize()
        except Exception:
            # 读取失败则保持默认结构
            return

    def save(self) -> None:
        os.makedirs(self.base_path, exist_ok=True)
        tmp_path = self.file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.file_path)

    def list(self) -> List[Dict[str, Any]]:
        presets = self.data.get("presets", [])
        return list(presets) if isinstance(presets, list) else []

    def get(self, preset_id: str) -> Dict[str, Any]:
        for p in self.list():
            if p.get("id") == preset_id:
                return p
        raise KeyError(preset_id)

    def create(self, *, name: str, settings: Dict[str, Any]) -> str:
        pid = uuid.uuid4().hex
        now = _utc_now_iso()
        preset = {
            "id": pid,
            "name": name,
            "settings": settings if isinstance(settings, dict) else {},
            "created_at": now,
            "updated_at": now,
        }
        self.data.setdefault("presets", []).append(preset)
        if not self.data.get("active_preset_id"):
            self.data["active_preset_id"] = pid
        return pid

    def rename(self, preset_id: str, new_name: str) -> None:
        p = self.get(preset_id)
        p["name"] = new_name
        p["updated_at"] = _utc_now_iso()

    def delete(self, preset_id: str) -> None:
        presets = self.list()
        new_presets = [p for p in presets if p.get("id") != preset_id]
        self.data["presets"] = new_presets

        if self.data.get("active_preset_id") == preset_id:
            self.data["active_preset_id"] = new_presets[0].get("id", "") if new_presets else ""

    def set_active(self, preset_id: str) -> None:
        # 确保 preset 存在
        self.get(preset_id)
        self.data["active_preset_id"] = preset_id

