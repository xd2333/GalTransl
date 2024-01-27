from configparser import SectionProxy
from GalTransl import LOGGER
from GalTransl.CSentense import *
from GalTransl.GTPlugin import GTTextPlugin


class ExampleNoUse(GTTextPlugin):
    def gtp_init(self, settings: SectionProxy = None):
        """
        This method is called when the plugin is loaded.
        在插件加载时被调用。
        如果配置文件中有Settings，则会传入用于初始化插件设置。
        :param settings: The settings for the plugin.
        """
        # 打印提示的方法，打印时请带上模块名，以便区分日志。
        LOGGER.info("[样例插件] 寄寄子·启动！")
        LOGGER.info(f"[样例插件] set_bool:{settings.getboolean('set_bool', True)}")
        LOGGER.info(f"[样例插件] set_int:{settings.getint('set_int', 10)}")
        LOGGER.info(f"[样例插件] set_str:{settings.get('set_string', 'default_str')}")
        LOGGER.info(f"[样例插件] 设置样例4:{settings.getboolean('设置样例4', True)}")
        # 读取配置文件中的设置，并保存到变量中。
        self.set_bool = settings.getboolean("set_bool", True)
        self.set_int = settings.getint("set_int", 10)
        self.set_str = settings.get("set_string", "default_str")
        self.设置样例4 = settings.getboolean("设置样例4", True)

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
