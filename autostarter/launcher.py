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

    def launch(self, force_mod: bool = False, no_onedragon: bool = False, settings: dict | None = None):
        """根据配置启动游戏"""
        if settings is None:
            settings = account_manager.get_settings()
        
        # 1. 启动 Mod
        self._launch_mod(settings, force_mod=force_mod)
        
        # 2. 启动外置启动器，并等待指定秒数
        external_mode = settings.get("external_launcher_mode", False)
        if external_mode:
            self._launch_external_launcher(settings)
            wait_seconds = settings.get("external_launcher_wait_seconds", 5)
            try:
                wait_seconds = int(wait_seconds)
            except Exception:
                wait_seconds = 5
            if wait_seconds > 0:
                log_action("Launcher", "external_launcher_wait", "start", seconds=int(wait_seconds))
                try:
                    time.sleep(wait_seconds)
                except Exception as e:
                    log_action("Launcher", "external_launcher_wait", "fail", seconds=int(wait_seconds), reason=str(e))
                    raise
                log_action("Launcher", "external_launcher_wait", "ok", seconds=int(wait_seconds))

        # 3. 启动 BetterGI 或 直接启动原神
        if settings.get('bettergi_enabled', True):
            self._launch_bettergi(settings, no_onedragon=no_onedragon)
        elif not external_mode:
            self._launch_genshin(settings)

    def _launch_mod(self, settings, force_mod: bool = False):
        enabled = bool(settings.get("mod_enabled", False) or force_mod)
        if not enabled:
            log_action("Launcher", "Mod", "skip", reason="disabled", method="cmdline", force_mod=bool(force_mod))
            return
        mod_path = (settings.get("mod_path") or "").strip()
        if not mod_path:
            log_action("Launcher", "Mod", "skip", reason="path_empty", method="cmdline", force_mod=bool(force_mod))
            return
        if not os.path.exists(mod_path):
            log_action("Launcher", "Mod", "skip", reason="path_not_exists", method="cmdline", force_mod=bool(force_mod))
            return
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
            # 使用 DETACHED_PROCESS 标志来彻底隔离进程，防止其继承主进程的控制台句柄，从而锁住 _MEI 临时目录
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

    def _launch_bettergi(self, settings, no_onedragon: bool = False):
        onedragon_enabled = settings.get('bettergi_onedragon_enabled', False) and not no_onedragon
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
        """实际执行启动逻辑 (Detached 模式，不阻塞)"""
        # 注意：不记录完整路径与配置内容，避免泄露敏感信息/可识别信息
        log_action(
            "Launcher",
            "BetterGI",
            "start",
            method="cmdline" if (bettergi_path and os.path.exists(bettergi_path)) else "urlscheme",
            onedragon=bool(onedragon_enabled),
            has_path=bool(bettergi_path),
            has_config=bool((config_name or "").strip()),
        )

        # 关键行为：当用户指定了一条龙“配置名称”时，必须通过 BetterGI.exe 命令行启动，
        # 否则回退 URL Scheme 会导致运行 BetterGI 页面“当前选中配置”，与用户预期不符。
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
        
        # 优先使用可执行文件命令行启动
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
                # 使用 Popen 启动并彻底隔离，不阻塞主进程，且主进程退出后不影响子进程
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
                # 当指定了配置名称时，不允许回退 URL Scheme（会运行错误的配置）
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
        
        # 命令行启动失败或无路径，尝试 URL Scheme 启动
        return self._try_launch_via_url(onedragon_enabled, config_name)

    def _run_and_wait_for_next(self, bettergi_path, config_1, config_2):
        """运行第一个配置，并在输出中检测到结束标志时启动第二个配置"""
        process = None
        try:
            cmd = [bettergi_path, "startOneDragon"]
            if config_1:
                cmd.append(config_1)
            
            log_action("Launcher", "BetterGI", "start", method="cmdline", onedragon=True, mode="two_stage")
            
            # 为了能读到输出，不使用 DETACHED_PROCESS
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
                
                # 实时打印 BetterGI 的输出供用户调试
                print(f"[BetterGI] {line.strip()}")
                
                if "一条龙和配置组任务结束" in line:
                    log_action("Launcher", "BetterGI", "ok", method="cmdline", onedragon=True, mode="two_stage")
                    break
            
            # 第一个配置结束，启动第二个配置
            log_action("Launcher", "BetterGI", "start", method="cmdline", onedragon=True, phase="terminate_for_next")
            
            if process:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            # 彻底杀死可能残留在后台的 BetterGI 进程，确保第二个配置能正常启动
            try:
                subprocess.run(["taskkill", "/F", "/IM", os.path.basename(bettergi_path), "/T"], 
                               capture_output=True, creationflags=0x08000000)
            except Exception:
                pass
            
            # 等待一秒确保进程彻底释放
            time.sleep(1)

            log_action("Launcher", "BetterGI", "start", method="cmdline", onedragon=True, mode="two_stage", stage="second")
            # 使用统一的启动方法，优先使用命令行
            self._do_launch_bettergi(bettergi_path, True, config_2)
            
            log_action("Launcher", "BetterGI", "ok", method="cmdline", onedragon=True, mode="two_stage", stage="second")
        except Exception as e:
            log_action("Launcher", "BetterGI", "fail", method="cmdline", onedragon=True, mode="two_stage", reason=str(e))
        finally:
            if process and process.poll() is None:
                process.terminate()

    def wait_for_launcher(self, timeout=None):
        """等待切换任务线程完成"""
        if self._launcher_thread and self._launcher_thread.is_alive():
            # 这里不需要 join 太久，因为 _run_and_wait_for_next 完成后主程序就可以退出了
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
            log_action("Launcher", "Genshin", "skip", reason="path_empty", method="cmdline")
            return
        if not os.path.exists(genshin_path):
            log_action("Launcher", "Genshin", "skip", reason="path_not_exists", method="cmdline")
            return
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
            log_action("Launcher", "external_launcher", "skip", reason="path_empty", method="cmdline")
            return
        if not os.path.exists(launcher_path):
            log_action("Launcher", "external_launcher", "skip", reason="path_not_exists", method="cmdline")
            return

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
