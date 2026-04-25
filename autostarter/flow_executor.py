from __future__ import annotations
import datetime
import sys
import time
from typing import Any, Callable, Mapping
from .launcher import game_launcher as _default_game_launcher
from .account_manager import account_manager as _default_account_manager
from .mihoyo_api import mihoyo_client as _default_mihoyo_client
game_launcher = _default_game_launcher
account_manager = _default_account_manager
mihoyo_client = _default_mihoyo_client
def run_flow(
    flow: list[dict[str, Any]] | None,
    settings: dict[str, Any] | None,
    force_mod: bool = False,
    no_onedragon: bool = False,
    hooks: Mapping[str, Callable[..., Any]] | None = None,
    sleep_func: Callable[[int], Any] = time.sleep,
) -> None:
    steps = flow if isinstance(flow, list) else []
    cfg = settings if isinstance(settings, dict) else {}
    from .log_actions import log_action  # pylint: disable=import-outside-toplevel
    def call_hook(step_type: str, *args: Any) -> None:
        if not hooks:
            return
        fn = hooks.get(step_type)
        if callable(fn):
            fn(*args)
    def _summarize_status(text: str) -> str:
        if not text:
            return "失败"
        if "跳过" in text or "已完成" in text:
            return "跳过"
        if "验证码" in text or "触发验证码" in text:
            return "需要验证码"
        if "失败" in text or "错误" in text or "无效" in text:
            return "失败"
        if "已签" in text or "已签到" in text:
            return "已签到"
        return "成功"
    def _run_signin() -> dict[str, Any]:
        settings = cfg
        today = datetime.date.today().isoformat()
        daily_once = bool(settings.get("daily_signin_once", True))
        last_date = str(settings.get("last_signin_date", "") or "")
        if daily_once and last_date == today:
            return {"lines": ["今日已签到，跳过。"], "has_error": False, "skipped": True}
        accounts = account_manager.get_accounts()
        if not accounts:
            return {"lines": ["未配置账号，跳过签到。"], "has_error": False, "skipped": True}
        item_labels = {
            "genshin": "原神",
            "starrail": "崩坏：星穹铁道",
            "zzz": "绝区零",
            "miyoushe": "米游社",
        }
        order = settings.get("signin_order") or ["genshin", "starrail", "zzz", "miyoushe"]
        order = [str(x) for x in order] if isinstance(order, list) else ["genshin", "starrail", "zzz", "miyoushe"]
        lines: list[str] = []
        has_error = False
        for item in order:
            label = item_labels.get(item, item)
            parts: list[str] = []
            for acc in accounts:
                try:
                    results = mihoyo_client.sign_in_item(acc, item)
                    text = "\n".join(results) if isinstance(results, list) else str(results)
                    status = _summarize_status(text)
                    if status in {"失败", "需要验证码"}:
                        has_error = True
                    parts.append(f"[{acc.get('name')}] {status}")
                except Exception:
                    has_error = True
                    parts.append(f"[{acc.get('name')}] 失败")
            lines.append(f"{label}: " + " | ".join(parts))
        if not has_error:
            try:
                account_manager.update_settings(last_signin_date=today)
            except Exception:
                pass
        return {"lines": lines, "has_error": has_error, "skipped": False}
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_type = step.get("type")
        if not isinstance(step_type, str) or not step_type:
            continue
        if step_type == "signin":
            log_action("Flow", "signin", "start")
            call_hook("signin", "start")
            try:
                result = _run_signin()
                call_hook("signin", result)
                if bool(result.get("has_error")):
                    try:
                        print("\n".join(result.get("lines") or []), file=sys.stderr)
                    except Exception:
                        pass
                    log_action("Flow", "signin", "fail", reason="has_error")
                elif bool(result.get("skipped")):
                    log_action("Flow", "signin", "skip", reason="skipped")
                else:
                    log_action("Flow", "signin", "ok")
            except Exception as e:
                log_action("Flow", "signin", "fail", reason=str(e))
                raise
            continue
        if step_type == "wait":
            seconds = step.get("seconds", 0)
            try:
                seconds_int = int(seconds)
            except Exception:
                seconds_int = 0
            if seconds_int < 0:
                seconds_int = 0
            log_action("Flow", "wait", "start", seconds=seconds_int)
            call_hook("wait", seconds_int)
            try:
                sleep_func(seconds_int)
            except Exception as e:
                log_action("Flow", "wait", "fail", seconds=seconds_int, reason=str(e))
                raise
            log_action("Flow", "wait", "ok", seconds=seconds_int)
            continue
        if step_type == "external_launcher":
            log_action("Flow", "external_launcher", "start")
            call_hook("external_launcher")
            try:
                game_launcher._launch_external_launcher(cfg)
                wait_seconds = cfg.get("external_launcher_wait_seconds", 5)
                try:
                    wait_seconds_int = int(wait_seconds)
                except Exception:
                    wait_seconds_int = 5
                if wait_seconds_int > 0:
                    log_action("Flow", "external_launcher_wait", "start", seconds=int(wait_seconds_int))
                    try:
                        sleep_func(int(wait_seconds_int))
                    except Exception as e:
                        log_action("Flow", "external_launcher_wait", "fail", seconds=int(wait_seconds_int), reason=str(e))
                        raise
                    log_action("Flow", "external_launcher_wait", "ok", seconds=int(wait_seconds_int))
            except Exception as e:
                log_action("Flow", "external_launcher", "fail", reason=str(e))
                raise
            log_action("Flow", "external_launcher", "ok")
            continue
        if step_type == "mod":
            log_action("Flow", "mod", "start")
            call_hook("mod")
            try:
                game_launcher._launch_mod(cfg, force_mod=True)
            except Exception as e:
                log_action("Flow", "mod", "fail", reason=str(e))
                raise
            log_action("Flow", "mod", "ok")
            continue
        if step_type == "bettergi":
            log_action("Flow", "bettergi", "start")
            call_hook("bettergi")
            try:
                ok = game_launcher._launch_bettergi(cfg, onedragon=False, no_onedragon=bool(no_onedragon))
                if ok is False:
                    raise RuntimeError("启动 BetterGI 失败（bettergi step）")
            except Exception as e:
                log_action("Flow", "bettergi", "fail", reason=str(e))
                raise
            log_action("Flow", "bettergi", "ok")
            continue
        if step_type == "onedragon":
            if no_onedragon:
                log_action("Flow", "onedragon", "skip", reason="no_onedragon")
                continue
            log_action("Flow", "onedragon", "start")
            call_hook("onedragon")
            try:
                ok = game_launcher._launch_bettergi(cfg, onedragon=True, no_onedragon=False)
                if ok is False:
                    raise RuntimeError("启动 BetterGI 一条龙失败（onedragon step）")
            except Exception as e:
                log_action("Flow", "onedragon", "fail", reason=str(e))
                raise
            log_action("Flow", "onedragon", "ok")
            continue
        if step_type == "genshin_direct":
            log_action("Flow", "genshin_direct", "start")
            call_hook("genshin_direct")
            try:
                game_launcher._launch_genshin(cfg)
            except Exception as e:
                log_action("Flow", "genshin_direct", "fail", reason=str(e))
                raise
            log_action("Flow", "genshin_direct", "ok")
            continue
