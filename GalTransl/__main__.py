import argparse
import time
from os.path import join as joinpath
from GalTransl.ConfigHelper import loadConfigFile
from GalTransl.Frontend.GPT import doGPT3Translate, doGPT4Translate, doNewBingTranslate
from GalTransl import LOGGER, PROGRAM_SPLASH


def main() -> int:
    parser = argparse.ArgumentParser("GalTransl")
    parser.add_argument("--project_dir", "-p", help="project folder", required=True)
    parser.add_argument("--config", "-c", help="filename of config file", required=True)
    parser.add_argument("--input", "-i", help="path of JSON text wait for translate")
    parser.add_argument("--output", "-o", help="path of outputed text")
    parser.add_argument(
        "--translator",
        "-t",
        choices=["gpt35", "gpt4", "chatgpt-gpt35", "newbing", "caiyun"],
        help="choose which Translator to use",
    )
    args = parser.parse_args()

    print(PROGRAM_SPLASH)
    LOGGER.info("GalTransl Core version: 1.0.0 [2023.05.21]")
    LOGGER.info("Author: cx2333")

    cfg = loadConfigFile(joinpath(args.project_dir, args.config))

    start_time = time.time()
    if backend := args.translator == "gpt35":
        doGPT3Translate(cfg)
    elif backend == "gpt4":
        doGPT4Translate(cfg)
        pass
    elif backend == "chatgpt-gpt35":
        raise RuntimeError("Work in progress!")
    elif backend == "newbing":
        doNewBingTranslate(cfg)
    elif backend == "caiyun":
        raise RuntimeError("Work in progress!")
    end_time = time.time()
    print(f"spend time:{str(end_time-start_time)}s")
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        exit(1)
