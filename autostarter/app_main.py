import sys
from .account_manager import account_manager
from .flow_executor import run_flow
from .flow_presets import FlowPresetManager
from .launcher import game_launcher
from .loghelper import log
def _parse_cli(argv: list[str]) -> dict:
    preset_id: str | None = None
    unsupported: list[str] = []
    i = 0
    while i < len(argv):
        a_raw = argv[i]
        a = (a_raw or "").strip()
        a_low = a.lower()
        if a_low == "--preset":
            if i + 1 < len(argv):
                preset_id = str(argv[i + 1]).strip()
                i += 2
                continue
            i += 1
            continue
        if a_low.startswith("--preset="):
            preset_id = a.split("=", 1)[1].strip()
            i += 1
            continue
        if a_low.startswith("-"):
            unsupported.append(a_raw)
        i += 1
    if unsupported:
        raise ValueError(f"不支持的命令行参数：{' '.join(unsupported)}（仅支持 --preset）")
    if not preset_id:
        raise ValueError("缺少参数：--preset <id>（当前版本仅支持通过预设启动）")
    return {
        "preset_id": preset_id or None,
    }
def main():
    try:
        cli = _parse_cli([a for a in sys.argv[1:] if isinstance(a, str)])
        preset_id = str(cli.get("preset_id") or "").strip()
        pm = FlowPresetManager()
        pm.load()
        preset = pm.get(preset_id)
        preset_flow = preset.get("flow") if isinstance(preset, dict) else None
        if not isinstance(preset_flow, list):
            preset_flow = []
        settings = account_manager.get_settings()
        run_flow(preset_flow, settings, force_mod=False, no_onedragon=False)
        log.info("主程序准备退出，检查后台任务...")
        game_launcher.wait_for_launcher()
        sys.exit(0)
    except Exception as e:
        try:
            print(f"运行出错: {e}", file=sys.stderr)
        except Exception:
            pass
        try:
            log.error(f"运行出错: {e}")
        except Exception:
            pass
        sys.exit(1)
if __name__ == "__main__":
    main()
