import json, re
from GalTransl import LOGGER
from GalTransl.GTPlugin import GFilePlugin

import os
import sys
webvtt_path = os.path.abspath("plugins/file_subtitle_vtt/webvtt")
sys.path.append(webvtt_path)
import webvtt


class file_plugin(GFilePlugin):
    def gtp_init(self, plugin_conf: dict, project_conf: dict):
        """
        This method is called when the plugin is loaded.在插件加载时被调用。
        :param plugin_conf: The settings for the plugin.插件yaml中所有设置的dict。
        :param project_conf: The settings for the project.项目yaml中common下设置的dict。
        """
        settings = plugin_conf["Settings"]
        self.保存双语字幕 = settings.get("保存双语字幕", False)
        self.上下双语1左右双语2 = settings.get("上下双语1左右双语2", 2)

    def load_file(self, file_path: str) -> list:
        """
        This method is called to load a file.
        加载文件时被调用。
        :param file_path: The path of the file to load.
        :return: A list of CSentense objects.
        """
        vtt = webvtt.read(file_path)
        result = []
        for caption in vtt:
            result.append({
                # "index": caption.index,
                "timestamp": f"{caption.start} --> {caption.end}", 
                "message": caption.text,
                "org_message": caption.text
            })
        return result

    def save_file(self, file_path: str, transl_json: list):
        """
        This method is called to save a file.
        保存文件时被调用。
        :param file_path: The path of the file to save.保存文件路径
        :param transl_json: A list of objects same as the return of load_file().load_file提供的json在翻译message和name后的结果。
        :return: None.
        """
        vtt = webvtt.WebVTT()
        for item in transl_json:
            caption = webvtt.Caption(item['timestamp'].split(' --> ')[0], item['timestamp'].split(' --> ')[1], item['message'])
            if self.保存双语字幕:
                if self.上下双语1左右双语2 == 2:
                    caption.text = f"{item['message']} {item['org_message']}"
                elif self.上下双语1左右双语2 == 1:  
                    caption.text = f"{item['message']}\n{item['org_message']}"
            vtt.captions.append(caption)
        vtt.save(file_path)

    def gtp_final(self):
        """
        This method is called after all translations are done.
        在所有文件翻译完成之后的动作，例如输出提示信息。
        """
        pass
