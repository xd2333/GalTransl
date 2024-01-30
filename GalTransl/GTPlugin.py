from GalTransl import LOGGER
from GalTransl.yapsy.IPlugin import IPlugin
from GalTransl.CSentense import CSentense


class GTextPlugin(IPlugin):
    def gtp_init(self, plugin_conf: dict, project_conf: dict):
        """
        This method is called when the plugin is loaded.
        在插件加载时被调用。
        plugin_conf为插件yaml所有项目转换后的字典。
        project_conf为项目yaml中common下的项目转换后的字典。
        :param plugin_conf: The settings for the plugin.
        :param project_conf: The settings for the project.
        """
        pass

    def before_src_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called before the source sentence is processed.
        在post_jp没有被去除对话框和字典替换之前的处理，如果这是第一个插件的话post_jp=原始日文。
        :param tran: The CSentense to be processed.
        :return: The modified CSentense."""
        return tran

    def after_src_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called after the source sentence is processed.
        在post_jp已经被去除对话框和字典替换之后的处理。
        :param tran: The CSentense to be processed.
        :return: The modified CSentense.
        """
        return tran

    def before_dst_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called before the destination sentence is processed.
        在post_zh没有被恢复对话框和字典替换之前的处理，如果这是第一个插件的话post_zh=原始译文。
        :param tran: The CSentense to be processed.
        :return: The modified CSentense.
        """
        return tran

    def after_dst_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called after the destination sentence is processed.
        在post_zh已经被恢复对话框和字典替换之后的处理。
        :param tran: The CSentense to be processed.
        :return: The modified CSentense.
        """
        return tran

    def gtp_final(self):
        """
        This method is called after all translations are done.
        在所有文件翻译完成之后的动作，例如输出提示信息。
        """
        pass


class GFilePlugin(IPlugin):
    def gtp_init(self, plugin_conf: dict, project_conf: dict):
        """
        This method is called when the plugin is loaded.
        在插件加载时被调用。
        plugin_conf为插件yaml中Settings下的设置。
        project_conf为项目yaml中common下的设置。
        :param plugin_conf: The settings for the plugin.
        :param project_conf: The settings for the project.
        """
        pass

    def load_file(self, file_path: str) -> list:
        """
        This method is called to load a file.
        加载文件时被调用。
        :param file_path: The path of the file to load.
        :return: A list of CSentense objects.
        """
        raise NotImplementedError("This method must be implemented by the plugin.")

    def save_file(self, file_path: str, result_json: list):
        """
        This method is called to save a file.
        保存文件时被调用。
        :param file_path: The path of the file to save.
        :param sentenses: A list of CSentense objects to save.
        """
        raise NotImplementedError("This method must be implemented by the plugin.")

    def gtp_final(self):
        """
        This method is called after all translations are done.
        在所有文件翻译完成之后的动作，例如输出提示信息。
        """
        pass
