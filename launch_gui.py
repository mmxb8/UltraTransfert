import sys


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        from ultra.smoke import write_report
        return write_report(sys.argv[2])
    from ultra.startup import launch_safely
    return launch_safely()

if __name__ == "__main__":
    raise SystemExit(main())
