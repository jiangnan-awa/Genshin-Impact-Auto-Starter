import os
import sys


def _use_legacy(argv) -> bool:
    # 环境变量优先（便于在打包环境或快捷方式里切换）
    if os.environ.get("AUTOSTARTER_GUI", "").strip().lower() == "legacy":
        return True
    # 其次支持命令行参数
    return any(str(a).strip().lower() == "--legacy" for a in (argv or []))


if __name__ == "__main__":
    argv = sys.argv[1:]
    if _use_legacy(argv):
        from autostarter.gui.app import main as legacy_main

        legacy_main()
    else:
        from autostarter.gui_v2.app import main as v2_main

        v2_main(argv=argv)
