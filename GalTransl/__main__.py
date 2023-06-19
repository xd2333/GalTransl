import argparse
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.Runner import run_galtransl
from GalTransl import PROGRAM_SPLASH, TRANSLATOR_SUPPORTED, GALTRANSL_VERSION, AUTHOR, CONTRIBUTORS


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
    print(f"GalTransl Core version: {GALTRANSL_VERSION}")
    print(f"Author: {AUTHOR}")
    print(f"Contributors: {CONTRIBUTORS}")

    cfg = CProjectConfig(args.project_dir)

    run_galtransl(cfg, args.translator)
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        exit(1)
