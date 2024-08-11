import re
import requests
import time
from GalTransl import LOGGER
from GalTransl.CSentense import CSentense
from GalTransl.GTPlugin import GTextPlugin

class ServerChanNotifier(GTextPlugin):
    def gtp_init(self, plugin_conf: dict, project_conf: dict):
        """
        This method is called when the plugin is loaded.在插件加载时被调用。
        :param plugin_conf: The settings for the plugin.插件yaml中所有设置的dict。
        :param project_conf: The settings for the project.项目yaml中common下设置的dict。
        """
        self.start_time = time.time()
        self.pname = plugin_conf["Core"].get("Name", "完成消息推送")
        settings = plugin_conf["Settings"]
        self.push_channels = settings.get("推送渠道", [])
        self.tg_bot_token = settings.get("Telegram_Bot_Token", "")
        self.tg_chat_id = settings.get("Telegram_Bot_ChatID", "")
        self.serverchan_sendkey = settings.get("ServerChan_SendKey", "")
        self.project_dir = project_conf["project_dir"]
        self.project_name = self.project_dir.split("\\")[-1]
        
        if not self.push_channels:
            LOGGER.warning(f"[{self.pname}] 未设置任何推送渠道，插件将不会发送通知。")
        else:
            LOGGER.debug(f"[{self.pname}] 插件初始化成功。推送渠道: {', '.join(self.push_channels)}")

    def before_src_processed(self, tran: CSentense) -> CSentense:
        return tran

    def after_src_processed(self, tran: CSentense) -> CSentense:
        return tran

    def before_dst_processed(self, tran: CSentense) -> CSentense:
        return tran

    def after_dst_processed(self, tran: CSentense) -> CSentense:
        return tran

    def gtp_final(self):
        """
        This method is called after all translations are done.
        在所有文件翻译完成之后的动作，发送通知到ServerChan或Telegram Bot。
        """
        end_time = time.time()
        total_time = end_time - self.start_time
        total_time_format = time.strftime("%H:%M:%S", time.gmtime(total_time))
        title = f"[GalTransl] {self.project_name} 翻译完成"
        content = f"所有文件的翻译工作已经完成，总耗时：{total_time_format}"
        
        for channel in self.push_channels:
            if channel == "ServerChan":
                if self.serverchan_sendkey:
                    self.send_serverchan_notification(title, content)
                else:
                    LOGGER.warning(f"[{self.pname}] ServerChan SendKey未设置，无法发送ServerChan通知。")
            elif channel == "Telegram Bot":
                if self.tg_bot_token and self.tg_chat_id:
                    self.send_telegram_notification(title, content)
                else:
                    LOGGER.warning(f"[{self.pname}] Telegram Bot Token或ChatID未设置，无法发送Telegram通知。")
            else:
                LOGGER.warning(f"[{self.pname}] 未知的推送渠道: {channel}")

        if not self.push_channels:
            LOGGER.warning(f"[{self.pname}] 未设置任何推送渠道，跳过发送通知。")

    def send_serverchan_notification(self, title, content):
        """
        发送通知到ServerChan
        :param title: 通知标题
        :param content: 通知内容
        """
        api_url = f'https://sctapi.ftqq.com/{self.serverchan_sendkey}.send'
        data = {
            'text': title,
            'desp': content
        }
        
        try:
            response = requests.post(api_url, data=data)
            if response.status_code == 200:
                LOGGER.info(f"[{self.pname}] ServerChan通知发送成功")
            else:
                LOGGER.error(f"[{self.pname}] ServerChan通知发送失败，状态码：{response.status_code}")
        except Exception as e:
            LOGGER.error(f"[{self.pname}] 发送ServerChan通知时发生错误：{str(e)}")


    def send_telegram_notification(self, title, content):
        """
        发送通知到Telegram Bot
        :param title: 通知标题
        :param content: 通知内容
        """
        api_url = f"https://api.telegram.org/bot{self.tg_bot_token}/sendMessage"
        
        # 转义 Markdown 特殊字符
        def escape_markdown(text):
            escape_chars = r'_*[]()~`>#+-=|{}.!'
            return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
        
        escaped_title = escape_markdown(title)
        escaped_content = escape_markdown(content)
        
        message = f"*{escaped_title}*\n\n{escaped_content}"
        params = {
            "chat_id": self.tg_chat_id,
            "text": message,
            "parse_mode": "MarkdownV2"
        }
        
        try:
            response = requests.post(api_url, params=params)
            if response.status_code == 200:
                LOGGER.info(f"[{self.pname}] Telegram Bot通知发送成功")
            else:
                LOGGER.error(f"[{self.pname}] Telegram Bot通知发送失败，状态码：{response.status_code}")
                LOGGER.error(f"响应内容：{response.text}")
        except Exception as e:
            LOGGER.error(f"[{self.pname}] 发送Telegram Bot通知时发生错误：{str(e)}")