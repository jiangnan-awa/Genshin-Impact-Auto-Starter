from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from . import config_paths
from .log_actions import log_action


def _utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


BUILTIN_STEP_TYPES = {
    "external_launcher",
    "mod",
    "bettergi",
    "genshin_direct",
    "onedragon",
}


class FlowPresetManager:
    """
    负责读写 config/presets.json（version=2，字段 flow）。

    v2 数据结构：
    {
      "version": 2,
      "active_preset_id": "",
      "presets": [{"id": "...", "name": "...", "flow": [...], ...}]
    }

    兼容 v1（settings 快照）：
    {
      "version": 1,
      "active_preset_id": "",
      "presets": [{"id": "...", "name": "...", "settings": {...}, ...}]
    }
    """

    def __init__(self, base_path: Optional[str] = None):
        paths = config_paths.get_config_paths(base_path)
        # 若用户仍存在根目录 presets.json，则尽量迁移到 config/，避免读取不到
        try:
            config_paths.migrate_root_files_to_config_dir(paths.base_path)
        except Exception:
            pass

        self.base_path = paths.base_path
        self.file_path = paths.presets_file
        self.data: Dict[str, Any] = {
            "version": 2,
            "active_preset_id": "",
            "presets": [],
        }

    # ───────────────────────── normalize / validate ─────────────────────────
    def _normalize(self) -> None:
        if not isinstance(self.data, dict):
            self.data = {"version": 2, "active_preset_id": "", "presets": []}
            return

        v = self.data.get("version")
        if not isinstance(v, int):
            self.data["version"] = 2

        if not isinstance(self.data.get("active_preset_id"), str):
            self.data["active_preset_id"] = ""

        presets = self.data.get("presets")
        if not isinstance(presets, list):
            self.data["presets"] = []

    def _sanitize_flow(self, flow: Any) -> List[Dict[str, Any]]:
        """
        确保：
        - wait 可重复
        - 内置动作步骤不重复（保留第一次出现）
        - 仅保留结构可识别的 step
        """
        if not isinstance(flow, list):
            return []

        out: List[Dict[str, Any]] = []
        seen_builtin: set[str] = set()
        for step in flow:
            if not isinstance(step, dict):
                continue
            t = step.get("type")
            if not isinstance(t, str) or not t:
                continue

            if t == "wait":
                seconds = step.get("seconds", 0)
                try:
                    seconds_int = int(seconds)
                except Exception:
                    seconds_int = 0
                if seconds_int < 0:
                    seconds_int = 0
                if seconds_int > 3000:
                    seconds_int = 3000
                out.append({"type": "wait", "seconds": seconds_int})
                continue

            if t in BUILTIN_STEP_TYPES:
                if t in seen_builtin:
                    continue
                seen_builtin.add(t)
                out.append({"type": t})
                continue

            # 未知类型：忽略（保守策略，避免执行器误识别）
        return out

    # ───────────────────────── load/save ─────────────────────────
    def load(self) -> None:
        if not os.path.exists(self.file_path):
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
        except Exception:
            return

        if not isinstance(obj, dict):
            return

        # 兼容：保留默认字段，避免缺字段
        self.data.update(obj)
        self._normalize()

        upgraded = False
        if int(self.data.get("version") or 0) == 1:
            log_action("FlowPresets", "upgrade", "start", from_version=1, to_version=2)
            self._upgrade_from_v1(include_wait=False)
            upgraded = True

        # v2 下也顺手做一次 flow sanitize，避免手工编辑造成重复内置动作
        if int(self.data.get("version") or 0) == 2:
            for p in self.list():
                if isinstance(p, dict):
                    p["flow"] = self._sanitize_flow(p.get("flow"))

        if upgraded:
            # 尽量落盘：这就是“自动升级”的关键
            try:
                self.save()
                log_action("FlowPresets", "upgrade", "ok", from_version=1, to_version=2)
            except Exception:
                log_action("FlowPresets", "upgrade", "fail", from_version=1, to_version=2, reason="save_failed")
                pass

    def save(self) -> None:
        # steps_count：统计所有 preset 的 flow steps 总数
        presets = self.list()
        total_steps = 0
        for p in presets:
            flow = p.get("flow")
            if isinstance(flow, list):
                total_steps += len(flow)
        log_action("FlowPresets", "save", "start", presets_count=len(presets), steps_count=int(total_steps))
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            tmp_path = self.file_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.file_path)
        except Exception as e:
            log_action(
                "FlowPresets",
                "save",
                "fail",
                presets_count=len(presets),
                steps_count=int(total_steps),
                reason=str(e),
            )
            raise
        log_action("FlowPresets", "save", "ok", presets_count=len(presets), steps_count=int(total_steps))

    # ───────────────────────── CRUD ─────────────────────────
    def list(self) -> List[Dict[str, Any]]:
        presets = self.data.get("presets", [])
        return list(presets) if isinstance(presets, list) else []

    def get(self, preset_id: str) -> Dict[str, Any]:
        for p in self.list():
            if p.get("id") == preset_id:
                return p
        raise KeyError(preset_id)

    def create(self, *, name: str, flow: List[Dict[str, Any]] | None = None) -> str:
        pid = uuid.uuid4().hex
        now = _utc_now_iso()
        preset = {
            "id": pid,
            "name": str(name or "").strip() or pid,
            "flow": self._sanitize_flow(flow or []),
            "created_at": now,
            "updated_at": now,
        }
        self.data.setdefault("presets", []).append(preset)
        if not self.data.get("active_preset_id"):
            self.data["active_preset_id"] = pid
        self.data["version"] = 2
        return pid

    def rename(self, preset_id: str, new_name: str) -> None:
        p = self.get(preset_id)
        p["name"] = str(new_name or "").strip() or p.get("id")
        p["updated_at"] = _utc_now_iso()

    def update_flow(self, preset_id: str, flow: List[Dict[str, Any]] | None) -> None:
        p = self.get(preset_id)
        sanitized = self._sanitize_flow(flow or [])
        p["flow"] = sanitized
        p["updated_at"] = _utc_now_iso()
        log_action("FlowPresets", "update_flow", "ok", preset_id=str(preset_id), steps_count=len(sanitized))

    def delete(self, preset_id: str) -> None:
        presets = self.list()
        new_presets = [p for p in presets if p.get("id") != preset_id]
        self.data["presets"] = new_presets

        if self.data.get("active_preset_id") == preset_id:
            self.data["active_preset_id"] = new_presets[0].get("id", "") if new_presets else ""

    def set_active(self, preset_id: str) -> None:
        self.get(preset_id)
        self.data["active_preset_id"] = preset_id

    # ───────────────────────── v1 -> v2 upgrade ─────────────────────────
    def _upgrade_from_v1(self, *, include_wait: bool = False) -> None:
        """
        将 v1(settings 快照) 升级为 v2(flow)。

        规则（与 docs/superpowers/specs/2026-04-16-flow-presets-and-config-dir-design.md 一致）：
        - 内置动作步骤不允许重复
        - wait 可重复；可选生成但默认不加（include_wait=False）
        """
        old_presets = self.data.get("presets", [])
        if not isinstance(old_presets, list):
            old_presets = []

        new_presets: List[Dict[str, Any]] = []
        for p in old_presets:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id") or uuid.uuid4().hex)
            name = str(p.get("name") or pid)
            settings = p.get("settings")
            if not isinstance(settings, dict):
                settings = {}

            flow = self._build_default_flow_from_settings(settings, include_wait=include_wait)

            now = _utc_now_iso()
            created_at = str(p.get("created_at") or now)
            updated_at = str(p.get("updated_at") or created_at)

            new_presets.append(
                {
                    "id": pid,
                    "name": name,
                    "flow": flow,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

        self.data["version"] = 2
        self.data["presets"] = new_presets
        if not isinstance(self.data.get("active_preset_id"), str):
            self.data["active_preset_id"] = ""

    def _build_default_flow_from_settings(self, settings: Dict[str, Any], *, include_wait: bool) -> List[Dict[str, Any]]:
        flow: List[Dict[str, Any]] = []
        seen: set[str] = set()

        def add_builtin(step_type: str) -> None:
            if step_type not in BUILTIN_STEP_TYPES:
                return
            if step_type in seen:
                return
            seen.add(step_type)
            flow.append({"type": step_type})

        def add_wait(seconds: Any) -> None:
            try:
                s = int(seconds)
            except Exception:
                s = 0
            if s <= 0:
                return
            if s > 3000:
                s = 3000
            flow.append({"type": "wait", "seconds": s})

        # 1) 外置启动器
        if bool(settings.get("external_launcher_mode", False)):
            add_builtin("external_launcher")
            if include_wait:
                add_wait(settings.get("external_launcher_wait_seconds", 5))

        # 2) Mod
        if bool(settings.get("mod_enabled", False)):
            add_builtin("mod")
            if include_wait:
                add_wait(settings.get("mod_wait_seconds", 6))

        # 3) BetterGI / OneDragon
        bettergi_enabled = bool(settings.get("bettergi_enabled", True))
        onedragon_enabled = bool(settings.get("bettergi_onedragon_enabled", False))

        if bettergi_enabled or onedragon_enabled:
            add_builtin("bettergi")
        if onedragon_enabled:
            add_builtin("onedragon")

        # 4) 直接原神：仅当 BetterGI 未启用且路径存在时
        if (not bettergi_enabled) and str(settings.get("genshin_path") or "").strip():
            add_builtin("genshin_direct")

        return self._sanitize_flow(flow)
