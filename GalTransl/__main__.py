import argparse
import time
from os.path import join as joinpath
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.Frontend.GPT import doGPT3Translate, doGPT4Translate, doNewBingTranslate
from GalTransl import LOGGER, PROGRAM_SPLASH


def main() -> int:
    parser = argparse.ArgumentParser("GalTransl")
    parser.add_argument("--project_dir", "-p", help="project folder", required=True)
    parser.add_argument(
        "--translator",
        "-t",
        choices=["gpt35", "gpt4", "chatgpt-gpt35", "newbing", "caiyun"],
        help="choose which Translator to use",
        required=True,
    )
    args = parser.parse_args()

    print(PROGRAM_SPLASH)
    print("GalTransl Core version: 1.0.1 [2023.05.23]")
    print("Author: cx2333")

    cfg = CProjectConfig(args.project_dir)

    start_time = time.time()
    if args.translator == "gpt35":
        doGPT3Translate(cfg)
    elif args.translator == "gpt4":
        doGPT4Translate(cfg)
    elif args.translator == "chatgpt-gpt35":
        doGPT3Translate(cfg, type="unoffapi")
    elif args.translator == "newbing":
        doNewBingTranslate(cfg)
    elif args.translator == "caiyun":
        raise RuntimeError("Work in progress!")
    end_time = time.time()
    LOGGER.info(f"spend time:{str(end_time-start_time)}s")
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        exit(1)
