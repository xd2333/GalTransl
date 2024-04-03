import json, re
from GalTransl import LOGGER
from GalTransl.GTPlugin import GFilePlugin


class file_plugin(GFilePlugin):
    def gtp_init(self, plugin_conf: dict, project_conf: dict):
        """
        This method is called when the plugin is loaded.在插件加载时被调用。
        :param plugin_conf: The settings for the plugin.插件yaml中所有设置的dict。
        :param project_conf: The settings for the project.项目yaml中common下设置的dict。
        """
        settings = plugin_conf["Settings"]
        self.保存双语字幕 = settings.get("保存双语字幕", False)
        self.pattern = re.compile(r"\[(\d+:\d+\.\d+)\](.+)", re.UNICODE)
        LOGGER.info(f"保存双语字幕: {self.保存双语字幕}")

    def load_file(self, file_path: str) -> list:
        """
        This method is called to load a file.
        加载文件时被调用。
        :param file_path: The path of the file to load.
        :return: A list of CSentense objects.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            lrc_text = file.read()
        LOGGER.debug(f"lrc_text: {lrc_text}")

        try:
            matches = self.pattern.findall(lrc_text)
            LOGGER.debug(f"matches: {matches}")
            result = [
                {"timestamp": m[0], "message": m[1].strip(), "org_message": m[1].strip()}
                for m in matches
            ]
        except Exception as e:
            raise e

        return result

    def save_file(self, file_path: str, transl_json: list):
        """
        This method is called to save a file.
        保存文件时被调用。
        :param file_path: The path of the file to save.保存文件路径
        :param transl_json: A list of objects same as the return of load_file().load_file提供的json在翻译message和name后的结果。
        :return: None.
        """

        result = ""
        for item in transl_json:
            if not self.保存双语字幕:
                result += f"[{item['timestamp']}]{item['message']}\n"
            else:
                result += f"[{item['timestamp']}]{item['message']} {item['org_message']}\n"

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(result.strip())

    def gtp_final(self):
        """
        This method is called after all translations are done.
        在所有文件翻译完成之后的动作，例如输出提示信息。
        """
        pass