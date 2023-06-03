import argparse
from asyncio import get_event_loop, run
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.Runner import run_galtransl
from GalTransl import (
    PROGRAM_SPLASH,
    TRANSLATOR_SUPPORTED,
    CORE_VERSION,
    AUTHOR,
    CONTRIBUTORS,
    LOGGER,
)


def main() -> int:
    parser = argparse.ArgumentParser("GalTransl")
    parser.add_argument("--project_dir", "-p", help="project folder", required=True)
    parser.add_argument(
        "--translator",
        "-t",
        choices=TRANSLATOR_SUPPORTED.keys(),
        help="choose which Translator to use",
        required=True,
    )
    args = parser.parse_args()

    print(PROGRAM_SPLASH)
    print(f"GalTransl Core version: {CORE_VERSION}")
    print(f"Author: {AUTHOR}")
    print(f"Contributors: {CONTRIBUTORS}")

    cfg = CProjectConfig(args.project_dir)

    loop = get_event_loop()
    try:
        run(run_galtransl(cfg, args.translator))
    except KeyboardInterrupt:
        LOGGER.info("正在等待现有请求返回...")
        loop.stop()
        LOGGER.info("Goodbye.")
    finally:
        loop.close()
        return 0


if __name__ == "__main__":
    main()
