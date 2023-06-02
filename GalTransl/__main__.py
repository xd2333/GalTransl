import argparse
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.Runner import run_galtransl
from GalTransl import PROGRAM_SPLASH, TRANSLATOR_SUPPORTED


def main() -> int:
    parser = argparse.ArgumentParser("GalTransl")
    parser.add_argument("--project_dir", "-p", help="project folder", required=True)
    parser.add_argument(
        "--translator",
        "-t",
        choices=TRANSLATOR_SUPPORTED,
        help="choose which Translator to use",
        required=True,
    )
    args = parser.parse_args()

    print(PROGRAM_SPLASH)
    print("GalTransl Core version: 1.0.1 [2023.05.23]")
    print("Author: cx2333")

    cfg = CProjectConfig(args.project_dir)

    run_galtransl(cfg, args.translator)
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        exit(1)
