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
from GalTransl.__main__ import worker


INPUT_PROMPT_TMP = "请输入/拖入项目文件夹，或项目文件夹内的yaml配置文件[default]："


def get_user_input(user_input, project_dir):
    if user_input != "":
        project_name = project_dir.split(os.sep)[-1]
        input_prompt = INPUT_PROMPT_TMP.replace(
            "[default]", f"(留空继续『{project_name}』项目)"
        )
    else:
        input_prompt = INPUT_PROMPT_TMP.replace("[default]", "")

    while True:
        user_input = input(input_prompt).strip('"') or user_input
        if not user_input:
            continue
        user_input = os.path.abspath(user_input)

        if user_input.endswith(".yaml"):
            config_file_name = os.path.basename(user_input)
            project_dir = os.path.dirname(user_input)
        else:
            config_file_name = CONFIG_FILENAME
            project_dir = user_input

        if not os.path.exists(os.path.join(project_dir, config_file_name)):
            print(f"{project_dir}文件夹内不存在配置文件{config_file_name}，请检查后重新输入\n")
            continue
        else:
            return user_input, project_dir, config_file_name


def main():
    user_input = ""
    project_dir = ""
    config_file_name = CONFIG_FILENAME
    translator = ""
    while True:
        print(PROGRAM_SPLASH)
        print(f"Ver: {GALTRANSL_VERSION}")
        print(f"Author: {AUTHOR}")
        print(f"Contributors: {CONTRIBUTORS}\n")

        try:
            user_input, project_dir, config_file_name = get_user_input(
                user_input, project_dir
            )
            if translator != "":
                default_choice = list(TRANSLATOR_SUPPORTED.keys()).index(translator)
            else:
                default_choice = 0
            os.system("")  # 解决cmd的ANSI转义bug
            translator = BulletMenu(
                f"请为『{project_dir.split(os.sep)[-1]}』项目选择翻译器：", TRANSLATOR_SUPPORTED
            ).run(default_choice)
        except KeyboardInterrupt:
            print("\nGoodbye.")
            sys.exit(0)
        worker(project_dir, config_file_name, translator, show_banner=False)

        os.system("pause")
        os.system("cls")


if __name__ == "__main__":
    main()
