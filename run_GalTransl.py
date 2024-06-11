import os
import sys
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

class ProjectManager:
    def __init__(self):
        self.user_input = ""
        self.project_dir = ""
        self.config_file_name = CONFIG_FILENAME
        self.translator = ""

    def validate_project_path(self, user_input):
        user_input = os.path.abspath(user_input)
        if user_input.endswith(".yaml"):
            config_file_name = os.path.basename(user_input)
            project_dir = os.path.dirname(user_input)
        else:
            config_file_name = CONFIG_FILENAME
            project_dir = user_input

        if not os.path.exists(os.path.join(project_dir, config_file_name)):
            print(f"{project_dir}文件夹内不存在配置文件{config_file_name}，请检查后重新输入\n")
            return None, None, None
        return user_input, project_dir, config_file_name

    def get_user_input(self):
        while True:
            input_prompt = INPUT_PROMPT_TMP.replace(
                "[default]",
                f"(留空继续『{self.project_name()}』项目)" if self.project_dir else ""
            )
            user_input = input(input_prompt).strip('"') or self.user_input

            if not user_input:
                continue

            self.user_input, self.project_dir, self.config_file_name = self.validate_project_path(user_input)
            if not self.project_dir:
                continue

            return

    def print_program_info(self):
        print(PROGRAM_SPLASH)
        print(f"Ver: {GALTRANSL_VERSION}")
        print(f"Author: {AUTHOR}")
        print(f"Contributors: {CONTRIBUTORS}\n")

    def choose_translator(self):
        default_choice = list(TRANSLATOR_SUPPORTED.keys()).index(self.translator) if self.translator else 0
        os.system("")  # 解决cmd的ANSI转义bug
        self.translator = BulletMenu(
            f"请为『{self.project_name()}』项目选择翻译器：",
            TRANSLATOR_SUPPORTED
        ).run(default_choice)

    def project_name(self):
        return self.project_dir.split(os.sep)[-1] if self.project_dir else ""

    def run(self):
        # 检查命令行参数
        if len(sys.argv) > 1:
            self.user_input = sys.argv[1]
            self.user_input, self.project_dir, self.config_file_name = self.validate_project_path(self.user_input)

        while True:
            self.print_program_info()

            # 如果初始路径无效或未提供，进入交互式输入阶段
            if not self.project_dir:
                try:
                    self.get_user_input()
                except KeyboardInterrupt:
                    print("\nGoodbye.")
                    return

            try:
                self.choose_translator()
            except KeyboardInterrupt:
                print("\nGoodbye.")
                return

            worker(self.project_dir, self.config_file_name, self.translator, show_banner=False)

            print("翻译任务完成，准备重新开始...")
            self.user_input = ""
            self.translator = ""

            os.system("pause")
            os.system("cls")


if __name__ == "__main__":
    manager = ProjectManager()
    manager.run()