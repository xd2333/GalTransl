import argparse, traceback
from asyncio import get_event_loop, run
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.Runner import run_galtransl
from GalTransl import (
    PROGRAM_SPLASH,
    TRANSLATOR_SUPPORTED,
    GALTRANSL_VERSION,
    AUTHOR,
    CONTRIBUTORS,
    LOGGER,
    DEBUG_LEVEL,
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
    parser.add_argument(
        "--debug-level",
        "-l",
        choices=DEBUG_LEVEL.keys(),
        help="debug level",
        default="info",
    )
    args = parser.parse_args()
    # logging level
    LOGGER.setLevel(DEBUG_LEVEL[args.debug_level])

    print(PROGRAM_SPLASH)
    print(f"GalTransl Core version: {GALTRANSL_VERSION}")
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
    except RuntimeError as ex:
        LOGGER.error("程序遇到问题，即将退出（诊断信息：%s）", ex)
    except BaseException as ex:
        print(ex)
        traceback.print_exception(type(ex), ex, ex.__traceback__)
    finally:
        loop.close()
        return 0


if __name__ == "__main__":
    main()
