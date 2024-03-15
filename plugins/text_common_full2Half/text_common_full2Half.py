from GalTransl import LOGGER
from GalTransl.CSentense import CSentense
from GalTransl.GTPlugin import GTextPlugin


class text_common_fullWidthFix(GTextPlugin):

    def gtp_init(self, plugin_conf: dict, project_conf: dict):
        """
        This method is called when the plugin is loaded.在插件加载时被调用。
        :param plugin_conf: The settings for the plugin.插件yaml中所有设置的dict。
        :param project_conf: The settings for the project.项目yaml中common下设置的dict。
        """
        # 打印提示的方法，打印时请带上模块名，以便区分日志。
        self.pname = plugin_conf["Core"].get("Name", "")
        settings = plugin_conf["Settings"]
        LOGGER.info(f"[{self.pname}] 请注意，您开启了全角转半角功能。")
        LOGGER.info(f"[{self.pname}] 当前是否转换标点:{settings.get('是否替换标点', False)}")
        # 读取配置文件中的设置，并保存到变量中。
        self.是否替换标点 = settings.get("是否替换标点", False)

    def full2half(self, s):
        # 创建一个转换表，包括数字、字母和常见标点符号
        full_to_half_dict = {}
        full_to_half_dict.update({chr(0xFF10 + i): chr(0x30 + i) for i in range(10)})  # 数字
        full_to_half_dict.update({chr(0xFF21 + i): chr(0x41 + i) for i in range(26)})  # 大写字母
        full_to_half_dict.update({chr(0xFF41 + i): chr(0x61 + i) for i in range(26)})  # 小写字母

        # 扩展：添加常见全角标点符号到半角的映射
        if self.是否替换标点:
            punctuations = {
                '。': '.', '，': ',', '、': '\\', '；': ';', '：': ':',
                '？': '?', '！': '!', '“': '"', '”': '"', '‘': "'", '’': "'",
                '（': '(', '）': ')', '【': '[', '】': ']', '《': '<', '》': '>',
                '—': '-', '…': '...', '・': '·', '『': '{', '』': '}', '〔': '[',
                '〕': ']', '｛': '{', '｝': '}', '％': '%', '＋': '+', '－': '-',
                '＊': '*', '／': '/', '＝': '=', '＜': '<', '＞': '>', '＆': '&',
                '＄': '$', '＃': '#', '＠': '@', '＾': '^', '｜': '|', '～': '~',
                '｀': '`'
            }
            # 更新转换表
            full_to_half_dict.update(punctuations)

        return ''.join(full_to_half_dict.get(char, char) for char in s)


    def before_src_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called before the source sentence is processed.
        在post_jp没有被去除对话框和字典替换之前的处理，如果这是第一个插件的话post_jp=原始日文。
        :param tran: The CSentense to be processed.
        :return: The modified CSentense."""
        tran.post_jp = self.full2half(tran.post_jp)
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
