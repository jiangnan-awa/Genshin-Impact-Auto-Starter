import sys
if __name__ == "__main__":
    argv = sys.argv[1:]
    from autostarter.gui.app import main
    main(argv=argv)
