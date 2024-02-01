import argparse, traceback
from asyncio import get_event_loop, run, new_event_loop, set_event_loop
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


def worker(project_dir: str, config_file_name: str, translator: str, show_banner=True):
    if show_banner:
        print(PROGRAM_SPLASH)
        print(f"GalTransl Core version: {GALTRANSL_VERSION}")
        print(f"Author: {AUTHOR}")
        print(f"Contributors: {CONTRIBUTORS}")

    cfg = CProjectConfig(project_dir, config_file_name)
    try:
        loop = get_event_loop()
    except RuntimeError:
        loop = new_event_loop()
        set_event_loop(loop)

    try:
        run(run_galtransl(cfg, translator))
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
        return True


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

    return worker(args.project_dir, "config.yaml", args.translator)


if __name__ == "__main__":
    main()
