import os
import shlex
import subprocess
import time
import threading
from .loghelper import log
from .account_manager import account_manager

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
                log.info(f"外置启动器已启动，等待 {wait_seconds} 秒...")
                time.sleep(wait_seconds)

        # 3. 启动 BetterGI 或 直接启动原神
        if settings.get('bettergi_enabled', True):
            self._launch_bettergi(settings, no_onedragon=no_onedragon)
        elif not external_mode:
            self._launch_genshin(settings)

    def _launch_mod(self, settings, force_mod: bool = False):
        if not (settings.get("mod_enabled", False) or force_mod):
            return
        mod_path = (settings.get("mod_path") or "").strip()
        if not mod_path or not os.path.exists(mod_path):
            return
        wait_seconds = settings.get("mod_wait_seconds", 6)
        try:
            wait_seconds = int(wait_seconds)
        except Exception:
            wait_seconds = 6
        if wait_seconds < 0:
            wait_seconds = 0
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
        except Exception:
            return

    def _launch_bettergi(self, settings, no_onedragon: bool = False):
        onedragon_enabled = settings.get('bettergi_onedragon_enabled', False) and not no_onedragon
        onedragon_config_1 = (settings.get('bettergi_onedragon_config') or "").strip()
        onedragon_config_2 = (settings.get('bettergi_onedragon_config_2') or "").strip()
        bettergi_path = settings.get('bettergi_path')

        if not onedragon_enabled:
            self._do_launch_bettergi(bettergi_path, False, "")
            return

        if onedragon_config_2 and bettergi_path and os.path.exists(bettergi_path):
            self._launcher_thread = threading.Thread(
                target=self._run_and_wait_for_next, 
                args=(bettergi_path, onedragon_config_1, onedragon_config_2), 
                daemon=False
            )
            self._launcher_thread.start()
        else:
            self._do_launch_bettergi(bettergi_path, True, onedragon_config_1)

    def _do_launch_bettergi(self, bettergi_path, onedragon_enabled, config_name):
        """实际执行启动逻辑 (Detached 模式，不阻塞)"""
        log.info(f"正在启动 BetterGI: 路径={bettergi_path}, 一条龙={onedragon_enabled}, 配置={config_name}")
        
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
                
                log.info(f"正在通过命令行启动 BetterGI: {' '.join(cmd)}")
                # 使用 Popen 启动并彻底隔离，不阻塞主进程，且主进程退出后不影响子进程
                subprocess.Popen(cmd, cwd=os.path.dirname(bettergi_path), close_fds=True,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
                time.sleep(2)
                log.info("BetterGI 已成功通过命令行拉起")
                return True
            except Exception as e:
                log.error(f"通过命令行启动 BetterGI 失败: {e}")
        
        # 命令行启动失败或无路径，尝试 URL Scheme 启动
        log.info("尝试通过 URL Scheme 启动 BetterGI")
        return self._try_launch_via_url(onedragon_enabled, config_name)

    def _run_and_wait_for_next(self, bettergi_path, config_1, config_2):
        """运行第一个配置，并在输出中检测到结束标志时启动第二个配置"""
        process = None
        try:
            cmd = [bettergi_path, "startOneDragon"]
            if config_1:
                cmd.append(config_1)
            
            log.info(f"正在启动 BetterGI 并监听第一个任务: {' '.join(cmd)}")
            
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
                    log.info("检测到 BetterGI 结束标志: '一条龙和配置组任务结束'")
                    break
            
            # 第一个配置结束，启动第二个配置
            log.info(f"第一个任务已结束，正在关闭当前 BetterGI 实例...")
            
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

            log.info(f"准备启动第二个配置: {config_2}")
            # 使用统一的启动方法，优先使用命令行
            self._do_launch_bettergi(bettergi_path, True, config_2)
            
            log.info("BetterGI 切换流程已完成，主程序即将退出")
        except Exception as e:
            log.error(f"监听 BetterGI 过程出错: {e}")
        finally:
            if process and process.poll() is None:
                process.terminate()

    def wait_for_launcher(self, timeout=None):
        """等待切换任务线程完成"""
        if self._launcher_thread and self._launcher_thread.is_alive():
            # 这里不需要 join 太久，因为 _run_and_wait_for_next 完成后主程序就可以退出了
            self._launcher_thread.join(timeout=timeout)

    def _try_launch_via_url(self, onedragon_enabled: bool, config_name: str = None) -> bool:
        try:
            if onedragon_enabled:
                url = "bettergi://startOneDragon"
                if config_name:
                    url += f"?config={config_name}"
                os.startfile(url)
            else:
                os.startfile("bettergi://start")
            time.sleep(5)
            return True
        except Exception as e:
            log.warning(f"URL Scheme 启动失败: {e}")
            return False

    def _launch_genshin(self, settings):
        genshin_path = settings.get('genshin_path')
        if genshin_path and os.path.exists(genshin_path):
            try:
                subprocess.Popen([genshin_path], cwd=os.path.dirname(genshin_path), close_fds=True,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
                time.sleep(5)
            except Exception:
                pass

    def _launch_external_launcher(self, settings):
        launcher_path = (settings.get("external_launcher_path") or "").strip()
        if not launcher_path or not os.path.exists(launcher_path):
            return

        args_str = (settings.get("external_launcher_args") or "").strip()
        args = []
        if args_str:
            try:
                args = shlex.split(args_str, posix=True)
            except Exception:
                args = args_str.split()

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
        except Exception:
            return

game_launcher = GameLauncher()
