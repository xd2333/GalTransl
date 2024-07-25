# # 单元测试用
# import sys
# import os

# # 获取 GalTransl 的根目录路径
# galtransl_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# sys.path.insert(0, galtransl_root)

from GalTransl import LOGGER
from GalTransl.CSentense import CSentense
from GalTransl.GTPlugin import GTextPlugin

class LineBreakFix(GTextPlugin):
    def gtp_init(self, plugin_conf: dict, project_conf: dict):
        """
        初始化插件
        :param plugin_conf: 插件配置字典
        :param project_conf: 项目配置字典
        """
        # 从配置中获取插件名称，默认为"行内换行修复"
        self.pname = plugin_conf["Core"].get("Name", "行内换行修复")
        settings = plugin_conf["Settings"]
        LOGGER.info(f"[{self.pname}] 插件启动")

        # 从配置中读取设置
        self.linebreak = settings.get("换行符", "[r]")  # 换行符，默认为"[r]"
        self.mode = settings.get("换行模式", "保持位置")  # 换行模式，默认为"保持位置"
        self.force_fix = settings.get("强制修复", False)  # 是否强制修复，默认为False

        # 输出设置信息
        LOGGER.info(f"[{self.pname}] 换行符: {self.linebreak}")
        LOGGER.info(f"[{self.pname}] 换行模式: {self.mode}")
        LOGGER.info(f"[{self.pname}] 强制修复: {self.force_fix}")

    def before_src_processed(self, tran: CSentense) -> CSentense:
        return tran

    def after_src_processed(self, tran: CSentense) -> CSentense:
        return tran

    def before_dst_processed(self, tran: CSentense) -> CSentense:
        return tran

    def after_dst_processed(self, tran: CSentense) -> CSentense:
        """
        在目标文本处理之后的操作，主要的换行符修复逻辑
        :param tran: CSentense对象
        :return: 处理后的CSentense对象
        """
        # 计算源文本和目标文本中的换行符数量
        src_breaks = tran.pre_jp.count(self.linebreak)
        dst_breaks = tran.post_zh.count(self.linebreak)
        LOGGER.debug(f"[{self.pname}] 源文本换行符数量: {src_breaks}")
        LOGGER.debug(f"[{self.pname}] 目标文本换行符数量: {dst_breaks}")

        # 如果源文本和目标文本的换行符数量相同，且不强制修复，则不进行处理
        if src_breaks == dst_breaks and not self.force_fix:
            return tran

        LOGGER.info(f"[{self.pname}] 发现源文本和目标文本的换行符数量不一致，正在进行换行符修复，模式: {self.mode}")

        # 根据不同的换行模式调用相应的处理方法
        if self.mode == "平均":
            tran.post_zh = self.average_mode(tran.post_zh, src_breaks)
        elif self.mode == "开头":
            tran.post_zh = self.start_mode(tran.post_zh, src_breaks)
        elif self.mode == "结尾":
            tran.post_zh = self.end_mode(tran.post_zh, src_breaks)
        elif self.mode == "切最长":
            tran.post_zh = self.intersperse_mode(tran.post_zh, src_breaks)
        elif self.mode == "保持位置":
            tran.post_zh = self.keep_position_mode(tran.post_zh, tran.post_jp, src_breaks)
        else:
            LOGGER.warning(f"[{self.pname}] 未知的换行模式: {self.mode}")

        return tran

    def average_mode(self, text: str, target_breaks: int) -> str:
        """
        平均模式：将换行符平均分布在文本中
        :param text: 原文本
        :param target_breaks: 目标换行符数量
        :return: 处理后的文本
        """
        # 移除所有现有的换行符
        text_without_breaks = text.replace(self.linebreak, '')
        total_length = len(text_without_breaks)
        chars_per_slice = total_length // (target_breaks + 1)
        
        result = []
        for i in range(target_breaks):
            result.append(text_without_breaks[i * chars_per_slice : (i + 1) * chars_per_slice])
            result.append(self.linebreak)
        result.append(text_without_breaks[target_breaks * chars_per_slice:])
        
        return ''.join(result)

    def start_mode(self, text: str, target_breaks: int) -> str:
        """
        开头模式：在文本开头添加换行符
        :param text: 原文本
        :param target_breaks: 目标换行符数量
        :return: 处理后的文本
        """
        slices = text.split(self.linebreak)
        if len(slices) - 1 >= target_breaks:
            return self.linebreak.join(slices[:target_breaks+1])
        
        first_slice = slices[0]
        breaks_to_add = target_breaks - (len(slices) - 1)
        
        chunk_size = len(first_slice) // (breaks_to_add + 1)
        new_first_slices = []
        for i in range(breaks_to_add):
            new_first_slices.append(first_slice[i*chunk_size:(i+1)*chunk_size])
        new_first_slices.append(first_slice[breaks_to_add*chunk_size:])
        
        return self.linebreak.join(new_first_slices + slices[1:])

    def end_mode(self, text: str, target_breaks: int) -> str:
        """
        结尾模式：在文本结尾添加换行符
        :param text: 原文本
        :param target_breaks: 目标换行符数量
        :return: 处理后的文本
        """
        slices = text.split(self.linebreak)
        if len(slices) - 1 >= target_breaks:
            return self.linebreak.join(slices[:target_breaks+1])
        
        last_slice = slices[-1]
        breaks_to_add = target_breaks - (len(slices) - 1)
        
        chunk_size = len(last_slice) // (breaks_to_add + 1)
        new_last_slices = []
        for i in range(breaks_to_add):
            new_last_slices.append(last_slice[i*chunk_size:(i+1)*chunk_size])
        new_last_slices.append(last_slice[breaks_to_add*chunk_size:])
        
        return self.linebreak.join(slices[:-1] + new_last_slices)

    def intersperse_mode(self, text: str, target_breaks: int) -> str:
        """
        切最长模式：在最长的文本片段中插入换行符
        :param text: 原文本
        :param target_breaks: 目标换行符数量
        :return: 处理后的文本
        """
        slices = text.split(self.linebreak)
        if len(slices) - 1 >= target_breaks:
            return self.linebreak.join(slices[:target_breaks+1])
        
        while len(slices) - 1 < target_breaks:
            longest_slice_index = max(range(len(slices)), key=lambda i: len(slices[i]))
            longest_slice = slices[longest_slice_index]
            mid = len(longest_slice) // 2
            slices[longest_slice_index:longest_slice_index+1] = [longest_slice[:mid], longest_slice[mid:]]
        
        return self.linebreak.join(slices)
    
    def keep_position_mode(self, text: str, src_text: str, target_breaks: int) -> str:
        """
        保持位置模式：尽量保持换行符在原文中的相对位置
        :param text: 目标文本
        :param src_text: 源文本
        :param target_breaks: 目标换行符数量
        :return: 处理后的文本
        """
        src_length = len(src_text.replace(self.linebreak, ''))
        dst_length = len(text.replace(self.linebreak, ''))
        
        src_breaks = src_text.split(self.linebreak)
        break_positions = []
        current_length = 0
        
        for i, slice in enumerate(src_breaks):
            if i < len(src_breaks) - 1:  # 不计算最后一个换行符后的位置
                current_length += len(slice)
                break_positions.append(current_length / src_length)
        
        result = []
        current_length = 0
        break_index = 0
        
        for char in text.replace(self.linebreak, ''):
            result.append(char)
            current_length += 1
            if break_index < len(break_positions) and current_length / dst_length >= break_positions[break_index]:
                result.append(self.linebreak)
                break_index += 1
        
        return ''.join(result)

    def gtp_final(self):
        """
        插件结束时的操作
        """
        pass