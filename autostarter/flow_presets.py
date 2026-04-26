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
    "signin",
    "external_launcher",
    "mod",
    "bettergi",
    "genshin_direct",
    "onedragon",
}
class FlowPresetManager:
    def __init__(self, base_path: Optional[str] = None):
        paths = config_paths.get_config_paths(base_path)
        self.base_path = paths.base_path
        self.file_path = paths.presets_file
        self.data: Dict[str, Any] = {
            "version": 2,
            "active_preset_id": "",
            "presets": [],
        }
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
        return out
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
        self.data.update(obj)
        self._normalize()
        if int(self.data.get("version") or 0) != 2:
            self.data = {"version": 2, "active_preset_id": "", "presets": []}
            return
        for p in self.list():
            if isinstance(p, dict):
                p["flow"] = self._sanitize_flow(p.get("flow"))
    def save(self) -> None:
        presets = self.list()
        total_steps = 0
        for p in presets:
            flow = p.get("flow")
            if isinstance(flow, list):
                total_steps += len(flow)
        log_action("FlowPresets", "save", "start", presets_count=len(presets), total_steps_count=int(total_steps))
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
                total_steps_count=int(total_steps),
                reason=str(e),
            )
            raise
        log_action("FlowPresets", "save", "ok", presets_count=len(presets), total_steps_count=int(total_steps))
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
        log_action("FlowPresets", "update_flow", "ok", preset_id=str(preset_id), preset_steps_count=len(sanitized))
    def delete(self, preset_id: str) -> None:
        presets = self.list()
        new_presets = [p for p in presets if p.get("id") != preset_id]
        self.data["presets"] = new_presets
        if self.data.get("active_preset_id") == preset_id:
            self.data["active_preset_id"] = new_presets[0].get("id", "") if new_presets else ""
    def set_active(self, preset_id: str) -> None:
        self.get(preset_id)
        self.data["active_preset_id"] = preset_id
