from __future__ import annotations

import time
from typing import Any, Callable, Mapping

from .launcher import game_launcher as _default_game_launcher

# 允许测试用例通过 monkeypatch 覆盖（tests/test_flow_executor.py 会用到）
game_launcher = _default_game_launcher


def run_flow(
    flow: list[dict[str, Any]] | None,
    settings: dict[str, Any] | None,
    force_mod: bool = False,
    no_onedragon: bool = False,
    hooks: Mapping[str, Callable[..., Any]] | None = None,
    sleep_func: Callable[[int], Any] = time.sleep,
) -> None:
    """
    严格按 flow 顺序执行启动步骤（Flow 是唯一顺序来源）。

    支持的 step types:
    - external_launcher: game_launcher._launch_external_launcher(settings)
    - mod: game_launcher._launch_mod(settings, force_mod=True 或 force_mod 参数)
    - bettergi: 通过 settings 副本强制 bettergi_onedragon_enabled=False 后调用 _launch_bettergi
    - onedragon: no_onedragon=True 时跳过；否则通过 settings 副本强制 bettergi_onedragon_enabled=True 后调用 _launch_bettergi
    - genshin_direct: game_launcher._launch_genshin(settings)
    - wait: sleep_func(seconds)
    """
    steps = flow if isinstance(flow, list) else []
    cfg = settings if isinstance(settings, dict) else {}

    # 统一动作日志（注意：log_action 内部导入 loghelper，避免 import 副作用）
    from .log_actions import log_action  # pylint: disable=import-outside-toplevel

    def call_hook(step_type: str, *args: Any) -> None:
        if not hooks:
            return
        fn = hooks.get(step_type)
        if callable(fn):
            fn(*args)

    for step in steps:
        if not isinstance(step, dict):
            continue
        step_type = step.get("type")
        if not isinstance(step_type, str) or not step_type:
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
            except Exception as e:
                log_action("Flow", "external_launcher", "fail", reason=str(e))
                raise
            log_action("Flow", "external_launcher", "ok")
            continue

        if step_type == "mod":
            log_action("Flow", "mod", "start")
            call_hook("mod")
            try:
                # flow 中出现 mod step 表示“本次流程需要尝试启动 mod”；
                # 因此这里直接以 force_mod=True 调用（即使 settings.mod_enabled 为 False 也会尝试启动）。
                # 参数 force_mod 仍保留在 run_flow 接口中，便于 app_main 透传“强制 Mod”语义。
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
                cfg2 = dict(cfg)
                cfg2["bettergi_onedragon_enabled"] = False
                ok = game_launcher._launch_bettergi(cfg2, no_onedragon=bool(no_onedragon))
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
                cfg2 = dict(cfg)
                cfg2["bettergi_onedragon_enabled"] = True
                ok = game_launcher._launch_bettergi(cfg2, no_onedragon=False)
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

        # 未知类型：忽略（保守策略）
