import os, sys

from command import BulletMenu
from GalTransl import (
    AUTHOR,
    CONFIG_FILENAME,
    CONTRIBUTORS,
    GALTRANSL_VERSION,
    PROGRAM_SPLASH,
    TRANSLATOR_SUPPORTED,
)
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.__main__ import worker

INPUT_PROMPT = "请输入/拖入项目文件夹，或项目文件夹内的yaml配置文件："

while True:
    print(PROGRAM_SPLASH)
    print("======Translate your favorite Galgame======")
    print(f"GalTransl ver: {GALTRANSL_VERSION}")
    print(f"Author: {AUTHOR}")
    print(f"Contributors: {CONTRIBUTORS}\n")
    try:
        project_dir = os.path.abspath(input(INPUT_PROMPT).strip('"'))
        config_file_name = CONFIG_FILENAME
        if project_dir.endswith(".yaml"):
            config_file_name = os.path.basename(project_dir)
            project_dir = os.path.dirname(project_dir)
        if not os.path.exists(os.path.join(project_dir, config_file_name)):
            print(f"项目文件夹内不存在配置文件{config_file_name}，请检查后重新输入\n")
            continue
        os.system("")  # 解决cmd的ANSI转义bug
        translator = BulletMenu("翻译器：", TRANSLATOR_SUPPORTED).run()
    except KeyboardInterrupt:
        print("\nGoodbye.")
        sys.exit(0)
    worker(project_dir, config_file_name, translator, show_banner=False)

    os.system("pause")
