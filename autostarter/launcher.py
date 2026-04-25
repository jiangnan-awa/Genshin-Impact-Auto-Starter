import os
import shlex
import subprocess
import time
import threading
from .account_manager import account_manager
from .log_actions import log_action
class GameLauncher:
    def __init__(self):
        self._launcher_thread = None
    def _launch_mod(self, settings, force_mod: bool = False):
        mod_path = (settings.get("mod_path") or "").strip()
        if not mod_path:
            log_action("Launcher", "Mod", "fail", reason="path_empty", method="cmdline", force_mod=bool(force_mod))
            raise RuntimeError("未配置 Mod 程序路径")
        if not os.path.exists(mod_path):
            log_action(
                "Launcher",
                "Mod",
                "fail",
                reason="path_not_exists",
                method="cmdline",
                force_mod=bool(force_mod),
            )
            raise RuntimeError("Mod 程序路径不存在")
        wait_seconds = settings.get("mod_wait_seconds", 6)
        try:
            wait_seconds = int(wait_seconds)
        except Exception:
            wait_seconds = 6
        if wait_seconds < 0:
            wait_seconds = 0
        log_action(
            "Launcher",
            "Mod",
            "start",
            method="cmdline",
            file=os.path.basename(mod_path),
            wait_seconds=int(wait_seconds),
            force_mod=bool(force_mod),
        )
        try:
            ext = os.path.splitext(mod_path)[1].lower()
            cwd = os.path.dirname(mod_path)
            if ext in {".bat", ".cmd"}:
                subprocess.Popen(["cmd.exe", "/c", f"\"{mod_path}\" --auto-launch"], cwd=cwd, close_fds=True, 
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen([mod_path, "--auto-launch"], cwd=cwd, close_fds=True,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
            time.sleep(wait_seconds)
            log_action(
                "Launcher",
                "Mod",
                "ok",
                method="cmdline",
                file=os.path.basename(mod_path),
                wait_seconds=int(wait_seconds),
                force_mod=bool(force_mod),
            )
        except Exception:
            log_action(
                "Launcher",
                "Mod",
                "fail",
                method="cmdline",
                file=os.path.basename(mod_path),
                wait_seconds=int(wait_seconds),
                force_mod=bool(force_mod),
                reason="exception",
            )
            return
    def _launch_bettergi(self, settings, *, onedragon: bool = False, no_onedragon: bool = False):
        onedragon_enabled = bool(onedragon) and (not bool(no_onedragon))
        onedragon_config_1 = (settings.get('bettergi_onedragon_config') or "").strip()
        onedragon_config_2 = (settings.get('bettergi_onedragon_config_2') or "").strip()
        bettergi_path = settings.get('bettergi_path')
        if not onedragon_enabled:
            return self._do_launch_bettergi(bettergi_path, False, "")
        if onedragon_config_2 and bettergi_path and os.path.exists(bettergi_path):
            log_action(
                "Launcher",
                "BetterGI",
                "start",
                method="cmdline",
                onedragon=True,
                mode="two_stage",
                has_config2=True,
            )
            self._launcher_thread = threading.Thread(
                target=self._run_and_wait_for_next, 
                args=(bettergi_path, onedragon_config_1, onedragon_config_2), 
                daemon=False
            )
            self._launcher_thread.start()
            log_action(
                "Launcher",
                "BetterGI",
                "ok",
                method="cmdline",
                onedragon=True,
                mode="two_stage",
                has_config2=True,
            )
            return True
        else:
            return self._do_launch_bettergi(bettergi_path, True, onedragon_config_1)
    def _do_launch_bettergi(self, bettergi_path, onedragon_enabled, config_name):
        log_action(
            "Launcher",
            "BetterGI",
            "start",
            method="cmdline" if (bettergi_path and os.path.exists(bettergi_path)) else "urlscheme",
            onedragon=bool(onedragon_enabled),
            has_path=bool(bettergi_path),
            has_config=bool((config_name or "").strip()),
        )
        if onedragon_enabled and (config_name or "").strip():
            if not bettergi_path or not os.path.exists(bettergi_path):
                log_action(
                    "Launcher",
                    "BetterGI",
                    "fail",
                    method="cmdline",
                    onedragon=True,
                    reason="bettergi_path_invalid_for_config",
                )
                try:
                    import sys
                    print(
                        "已指定一条龙配置名称，但 BetterGI 路径无效/未设置："
                        "无法执行 `BetterGI.exe startOneDragon <配置名称>`，已中止启动（不会回退 URL Scheme）。",
                        file=sys.stderr,
                    )
                except Exception:
                    pass
                return False
        if bettergi_path and os.path.exists(bettergi_path):
            try:
                cmd = [bettergi_path]
                if onedragon_enabled:
                    cmd.append("startOneDragon")
                    if config_name:
                        cmd.append(config_name)
                else:
                    cmd.append("start")
                log_action(
                    "Launcher",
                    "BetterGI",
                    "start",
                    method="cmdline",
                    onedragon=bool(onedragon_enabled),
                    has_config=bool((config_name or "").strip()),
                )
                subprocess.Popen(cmd, cwd=os.path.dirname(bettergi_path), close_fds=True,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
                time.sleep(2)
                log_action(
                    "Launcher",
                    "BetterGI",
                    "ok",
                    method="cmdline",
                    onedragon=bool(onedragon_enabled),
                    has_config=bool((config_name or "").strip()),
                )
                return True
            except Exception as e:
                log_action(
                    "Launcher",
                    "BetterGI",
                    "fail",
                    method="cmdline",
                    onedragon=bool(onedragon_enabled),
                    reason=str(e),
                )
                if onedragon_enabled and (config_name or "").strip():
                    log_action(
                        "Launcher",
                        "BetterGI",
                        "fail",
                        method="cmdline",
                        onedragon=True,
                        reason="cmdline_failed_and_config_forbids_fallback",
                    )
                    return False
        return self._try_launch_via_url(onedragon_enabled, config_name)
    def _run_and_wait_for_next(self, bettergi_path, config_1, config_2):
        process = None
        try:
            cmd = [bettergi_path, "startOneDragon"]
            if config_1:
                cmd.append(config_1)
            log_action("Launcher", "BetterGI", "start", method="cmdline", onedragon=True, mode="two_stage")
            process = subprocess.Popen(
                cmd, 
                cwd=os.path.dirname(bettergi_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='gbk', 
                errors='ignore',
                creationflags=0x08000000 # CREATE_NO_WINDOW
            )
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                print(f"[BetterGI] {line.strip()}")
                if "一条龙和配置组任务结束" in line:
                    log_action("Launcher", "BetterGI", "ok", method="cmdline", onedragon=True, mode="two_stage")
                    break
            log_action("Launcher", "BetterGI", "start", method="cmdline", onedragon=True, phase="terminate_for_next")
            if process:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            try:
                subprocess.run(["taskkill", "/F", "/IM", os.path.basename(bettergi_path), "/T"], 
                               capture_output=True, creationflags=0x08000000)
            except Exception:
                pass
            time.sleep(1)
            log_action("Launcher", "BetterGI", "start", method="cmdline", onedragon=True, mode="two_stage", stage="second")
            self._do_launch_bettergi(bettergi_path, True, config_2)
            log_action("Launcher", "BetterGI", "ok", method="cmdline", onedragon=True, mode="two_stage", stage="second")
        except Exception as e:
            log_action("Launcher", "BetterGI", "fail", method="cmdline", onedragon=True, mode="two_stage", reason=str(e))
        finally:
            if process and process.poll() is None:
                process.terminate()
    def wait_for_launcher(self, timeout=None):
        if self._launcher_thread and self._launcher_thread.is_alive():
            self._launcher_thread.join(timeout=timeout)
    def _try_launch_via_url(self, onedragon_enabled: bool, config_name: str = None) -> bool:
        log_action(
            "Launcher",
            "BetterGI",
            "start",
            method="urlscheme",
            onedragon=bool(onedragon_enabled),
            has_config=bool((config_name or "").strip()),
        )
        try:
            if onedragon_enabled:
                url = "bettergi://startOneDragon"
                if config_name:
                    url += f"?config={config_name}"
                os.startfile(url)
            else:
                os.startfile("bettergi://start")
            time.sleep(5)
            log_action(
                "Launcher",
                "BetterGI",
                "ok",
                method="urlscheme",
                onedragon=bool(onedragon_enabled),
                has_config=bool((config_name or "").strip()),
            )
            return True
        except Exception as e:
            log_action(
                "Launcher",
                "BetterGI",
                "fail",
                method="urlscheme",
                onedragon=bool(onedragon_enabled),
                has_config=bool((config_name or "").strip()),
                reason=str(e),
            )
            return False
    def _launch_genshin(self, settings):
        genshin_path = settings.get('genshin_path')
        if not genshin_path:
            log_action("Launcher", "Genshin", "fail", reason="path_empty", method="cmdline")
            raise RuntimeError("未配置游戏路径（Genshin Impact.exe）")
        if not os.path.exists(genshin_path):
            log_action("Launcher", "Genshin", "fail", reason="path_not_exists", method="cmdline")
            raise RuntimeError("游戏路径不存在（Genshin Impact.exe）")
        log_action("Launcher", "Genshin", "start", method="cmdline", file=os.path.basename(genshin_path))
        try:
            subprocess.Popen([genshin_path], cwd=os.path.dirname(genshin_path), close_fds=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
            time.sleep(5)
            log_action("Launcher", "Genshin", "ok", method="cmdline", file=os.path.basename(genshin_path))
        except Exception as e:
            log_action("Launcher", "Genshin", "fail", method="cmdline", file=os.path.basename(genshin_path), reason=str(e))
            return
    def _launch_external_launcher(self, settings):
        launcher_path = (settings.get("external_launcher_path") or "").strip()
        if not launcher_path:
            log_action("Launcher", "external_launcher", "fail", reason="path_empty", method="cmdline")
            raise RuntimeError("未配置外部启动器路径")
        if not os.path.exists(launcher_path):
            log_action("Launcher", "external_launcher", "fail", reason="path_not_exists", method="cmdline")
            raise RuntimeError("外部启动器路径不存在")
        args_str = (settings.get("external_launcher_args") or "").strip()
        args = []
        if args_str:
            try:
                args = shlex.split(args_str, posix=True)
            except Exception:
                args = args_str.split()
        log_action(
            "Launcher",
            "external_launcher",
            "start",
            method="cmdline",
            file=os.path.basename(launcher_path),
            has_args=bool(args_str),
        )
        try:
            ext = os.path.splitext(launcher_path)[1].lower()
            cwd = os.path.dirname(launcher_path)
            if ext in {".bat", ".cmd"}:
                if args_str:
                    subprocess.Popen(["cmd.exe", "/c", f"\"{launcher_path}\" {args_str}"], cwd=cwd, close_fds=True,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
                else:
                    subprocess.Popen(["cmd.exe", "/c", f"\"{launcher_path}\""], cwd=cwd, close_fds=True,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen([launcher_path] + args, cwd=cwd, close_fds=True,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
            time.sleep(1)
            log_action(
                "Launcher",
                "external_launcher",
                "ok",
                method="cmdline",
                file=os.path.basename(launcher_path),
                has_args=bool(args_str),
            )
        except Exception as e:
            log_action(
                "Launcher",
                "external_launcher",
                "fail",
                method="cmdline",
                file=os.path.basename(launcher_path),
                has_args=bool(args_str),
                reason=str(e),
            )
            return
game_launcher = GameLauncher()
