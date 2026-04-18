import sys


if __name__ == "__main__":
    argv = sys.argv[1:]
    from autostarter.gui_v2.app import main as v2_main

    v2_main(argv=argv)
