from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout,  QGroupBox, QLabel, QSizePolicy
)
from qfluentwidgets import (
    PushButton, CheckBox, SpinBox, PrimaryPushButton, EditableComboBox, FluentIcon as FIF,
)
from .OtherCustomWidgets import CustomLineEdit, CustomTextEdit


class ConfigButtons(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("配置按钮", parent)
        self.init_ui()

    def init_ui(self):
        # # 创建文件选择部分
        # self.label_file_path = CustomLineEdit(self)
        # self.label_file_path.setPlaceholderText("请选择要写入的 YAML 文件路径")
        # label_file_path_relative = "./uiProject/config.yaml"
        # label_file_path_absolute = os.path.abspath(label_file_path_relative)
        # self.label_file_path.setText(label_file_path_absolute)
        # self.pushButton_select_file = PushButton('选择文件', self, FIF.FOLDER)
        # self.pushButton_select_file.clicked.connect(self.select_file)

        # layout_file_selection = QHBoxLayout()
        # layout_file_selection_lable = QVBoxLayout()
        # layout_file_selection_lable.addWidget(QLabel("配置文件路径（config.yaml）"))
        # layout_file_selection.addWidget(self.label_file_path)
        # layout_file_selection.addWidget(self.pushButton_select_file)

        # # 输入目录选择部分
        # self.label_input_dir = CustomLineEdit(self)
        # self.label_input_dir.setPlaceholderText("请选择输入目录")
        # label_input_dir_relative = "gt_input"
        # self.label_input_dir.setText(os.path.join(os.path.dirname(label_file_path_absolute), label_input_dir_relative))
        # self.pushButton_select_dir = PushButton('选择目录', self, FIF.FOLDER)
        # self.pushButton_select_dir.clicked.connect(self.select_directory)

        # layout_dir_selection = QHBoxLayout()
        # layout_dir_selection_lable = QVBoxLayout()
        # layout_dir_selection_lable.addWidget(QLabel("文本输入目录（gt_input）"))
        # layout_dir_selection.addWidget(self.label_input_dir)
        # layout_dir_selection.addWidget(self.pushButton_select_dir)

        # 创建写入和读取 YAML 文件的按钮
        self.pushButton_write_yaml = PrimaryPushButton('写入配置', self, FIF.SAVE)
        self.pushButton_read_yaml = PrimaryPushButton(
            '读取配置', self, FIF.BOOK_SHELF)
        self.pushButton_reset_config = PrimaryPushButton(
            '重置配置', self, FIF.CANCEL)

        layout_buttons = QHBoxLayout()
        # 添加弹性空间
        layout_buttons.addStretch(1)

        # 添加按钮
        layout_buttons.addWidget(self.pushButton_write_yaml)
        layout_buttons.addSpacing(30)
        layout_buttons.addWidget(self.pushButton_read_yaml)
        layout_buttons.addSpacing(30)
        layout_buttons.addWidget(self.pushButton_reset_config)

        # 添加弹性空间
        layout_buttons.addStretch(1)

        main_layout = QVBoxLayout()
        # main_layout.addLayout(layout_file_selection_lable)
        # main_layout.addLayout(layout_file_selection)
        # main_layout.addLayout(layout_dir_selection_lable)
        # main_layout.addLayout(layout_dir_selection)
        main_layout.addLayout(layout_buttons)
        self.setLayout(main_layout)

    # def select_file(self):
    #     file_path, _ = QFileDialog.getOpenFileName(
    #         self, '选择文件', '', "YAML files (*.yaml *.yml);;All files (*)")
    #     if file_path:
    #         self.label_file_path.setText(file_path)
    #     dir_path = os.path.dirname(file_path)
    #     gt_input_path = os.path.join(dir_path, 'gt_input')
    #     if os.path.exists(gt_input_path):
    #         self.label_input_dir.setText(gt_input_path)
    #         print(f"[INFO] 已自动设置 gt_input 路径为 {gt_input_path}")
    #     else:
    #         print(f"[INFO] gt_input 路径 {gt_input_path} 不存在，请手动设置")

    # def select_directory(self):
    #     directory = QFileDialog.getExistingDirectory(self, '选择目录', '')
    #     if directory:
    #         self.label_input_dir.setText(directory)
    #     base_dir = os.path.dirname(directory)
    #     config_path = os.path.join(base_dir, 'config.yaml')
    #     if not os.path.exists(config_path):
    #         print(f"[INFO] 未找到配置文件 {config_path}，将使用默认配置")
    #         gt_input_path = os.path.join(base_dir, 'gt_input')
    #         if not os.path.exists(gt_input_path):
    #             os.makedirs(gt_input_path)
    #         for file_name in os.listdir(directory):
    #             file_path = os.path.join(directory, file_name)
    #             if os.path.isfile(file_path):
    #                 shutil.copy(file_path, gt_input_path)
    #         print(f"[INFO] 已自动复制 {directory} 到 {gt_input_path}")
    #     else:
    #         self.label_file_path.setText(config_path)
    #         print(f"[INFO] 已自动设置配置文件路径为 {config_path}")


class ProgramSettings(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("程序设置", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.save_log = CheckBox('是否记录日志到文件', self)
        self.workers_per_project = SpinBox(self)
        self.workers_per_project.setRange(1, 999)
        self.workers_per_project.setValue(1)

        # 定义源语言和目标语言下拉框
        self.source_language = EditableComboBox(self)
        self.source_language.setPlaceholderText("源语言")
        self.target_language = EditableComboBox(self)
        self.target_language.setPlaceholderText("目标语言")

        language_items = ["ja", "zh-cn", "zh-tw", "en", "ko", "ru", "fr"]
        self.source_language.addItems(language_items)
        self.target_language.addItems(language_items)

        self.source_language.setCurrentText("ja")
        self.target_language.setCurrentText("zh-cn")

        # 定义中间的箭头和切换按钮
        self.language_arrow = QLabel("→", self)
        self.language_switch_button = PushButton('切换', self, icon=FIF.SCROLL,)
        self.language_switch_button.clicked.connect(self.switch_languages)

        # 将上述控件横向排列
        language_layout = QHBoxLayout()
        language_layout.addWidget(self.source_language)
        language_layout.addWidget(self.language_arrow)
        language_layout.addWidget(self.target_language)
        language_layout.addWidget(self.language_switch_button)

        self.save_steps = SpinBox(self)
        self.save_steps.setRange(1, 999)
        self.save_steps.setValue(1)
        self.linebreak_symbol = CustomLineEdit(self)
        self.linebreak_symbol.setPlaceholderText("换行符 (如: '\\r\\n')")
        self.linebreak_symbol.setText("\\r\\n")
        self.skip_h = CheckBox('跳过可能触发敏感词检测的句子', self)
        self.skip_h.setChecked(False)
        self.skip_retry = CheckBox('出错时跳过循环重试', self)
        self.skip_retry.setChecked(False)
        self.retransl_fail = CheckBox('重启时重翻所有失败的句子', self)
        self.retransl_fail.setChecked(False)
        self.retransl_key = EditableComboBox(self)
        self.retransl_key.setPlaceholderText("重启时重翻的关键字（如: '残留日文'）")
        retransl_key_items = ["", "词频过高", "标点错漏",
                              "残留日文", "丢失换行", "多加换行", "比日文长", "字典使用"]
        self.retransl_key.addItems(retransl_key_items)
        self.retransl_key.setCurrentText("")

        gpt_section = QGroupBox("GPT 设置")

        gpt_layout = QVBoxLayout()
        self.num_per_request_translate = SpinBox(self)
        self.num_per_request_translate.setRange(1, 40)
        self.num_per_request_translate.setValue(8)
        self.stream_output_mode = CheckBox("流式输出效果", self)
        self.stream_output_mode.setChecked(True)
        self.transl_dropout = SpinBox(self)
        self.transl_dropout.setRange(0, 2)
        self.transl_dropout.setValue(0)

        self.transl_style = EditableComboBox(self)
        self.transl_style.setPlaceholderText("翻译风格 (如: '流畅')")
        transl_style_items = ["流畅", "文艺"]
        self.transl_style.addItems(transl_style_items)
        self.transl_style.setCurrentText("流畅")

        self.enable_proof_read = CheckBox("是否开启译后校润", self)
        self.enable_proof_read.setChecked(False)
        self.num_per_request_proof_read = SpinBox(self)
        self.num_per_request_proof_read.setRange(1, 20)
        self.num_per_request_proof_read.setValue(7)
        self.restore_context_mode = CheckBox("重启时恢复上一轮的译文前文", self)
        self.restore_context_mode.setChecked(True)

        gpt_layout.addWidget(QLabel("单次翻译句子数量"))
        gpt_layout.addWidget(self.num_per_request_translate)
        gpt_layout.addWidget(self.stream_output_mode)
        gpt_layout.addWidget(QLabel("丢弃翻译结果末尾的行数"))
        gpt_layout.addWidget(self.transl_dropout)
        gpt_layout.addWidget(QLabel("翻译风格(仅适用于 Galtransl-v1 引擎)"))
        gpt_layout.addWidget(self.transl_style)
        gpt_layout.addWidget(self.enable_proof_read)
        gpt_layout.addWidget(QLabel("单次校润句子数量"))
        gpt_layout.addWidget(self.num_per_request_proof_read)
        gpt_layout.addWidget(self.restore_context_mode)
        gpt_section.setLayout(gpt_layout)

        layout.addWidget(self.save_log)
        layout.addWidget(QLabel("多线程翻译的文件数量"))
        layout.addWidget(self.workers_per_project)
        layout.addWidget(QLabel("语言"))
        layout.addLayout(language_layout)
        layout.addWidget(QLabel("每翻译n次保存一次缓存"))
        layout.addWidget(self.save_steps)
        layout.addWidget(QLabel("换行符"))
        layout.addWidget(self.linebreak_symbol)
        layout.addWidget(self.skip_h)
        layout.addWidget(self.skip_retry)
        layout.addWidget(self.retransl_fail)
        layout.addWidget(QLabel("重翻关键字"))
        layout.addWidget(self.retransl_key)
        layout.addWidget(gpt_section)
        self.setLayout(layout)

    def switch_languages(self):
        source_lang = self.source_language.currentText()
        target_lang = self.target_language.currentText()
        self.source_language.setCurrentText(target_lang)
        self.target_language.setCurrentText(source_lang)


class PluginSettings(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("插件设置", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.file_plugin = EditableComboBox(self)
        self.file_plugin.setPlaceholderText("请输入文件插件")
        file_plugin_items = ["file_galtransl_json", "file_i18n_json",
                             "file_subtitle_srt", "file_translator++_xlsx"]
        self.file_plugin.addItems(file_plugin_items)
        self.file_plugin.setCurrentText("file_galtransl_json")
        self.text_plugins = CustomTextEdit(self)
        self.text_plugins.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.text_plugins.setPlaceholderText("请输入文本处理插件列表，按顺序执行（每行一个）")
        self.text_plugins.setPlainText(
            "text_common_normalfix\n(project_dir)text_common_example")

        layout.addWidget(QLabel("文件插件"))
        layout.addWidget(self.file_plugin)
        layout.addWidget(QLabel("文本处理插件列表"))
        layout.addWidget(self.text_plugins)

        self.setLayout(layout)


class ProxySettings(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("代理设置", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.enable_proxy = CheckBox("是否启用代理", self)
        self.enable_proxy.setChecked(False)
        self.proxy_address = CustomLineEdit(self)
        self.proxy_address.setPlaceholderText("请输入代理地址")
        self.proxy_address.setText("http://127.0.0.1:7890")

        layout.addWidget(self.enable_proxy)
        layout.addWidget(self.proxy_address)

        self.setLayout(layout)


class DictionarySettings(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("字典设置", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.default_dict_folder = CustomLineEdit(self)
        self.default_dict_folder.setPlaceholderText("通用字典文件夹")
        self.default_dict_folder.setText("Dict")
        self.use_pre_dict_in_name = CheckBox("在名称中使用译前字典", self)
        self.use_pre_dict_in_name.setChecked(False)
        self.use_post_dict_in_name = CheckBox("在名称中使用译后字典", self)
        self.use_post_dict_in_name.setChecked(False)

        self.pre_dict = CustomTextEdit(self)
        self.pre_dict.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pre_dict.setPlaceholderText("译前字典列表（每行一个）")
        self.pre_dict.setPlainText(
            "01H字典_矫正_译前.txt\n00通用字典_译前.txt\n(project_dir)项目字典_译前.txt")
        self.gpt_dict = CustomTextEdit(self)
        self.gpt_dict.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gpt_dict.setPlaceholderText("GPT 字典列表（每行一个）")
        self.gpt_dict.setPlainText("GPT字典.txt\n(project_dir)项目GPT字典.txt")
        self.post_dict = CustomTextEdit(self)
        self.post_dict.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.post_dict.setPlaceholderText("译后字典列表（每行一个）")
        self.post_dict.setPlainText(
            "00通用字典_符号_译后.txt\n00通用字典_译后.txt\n(project_dir)项目字典_译后.txt")

        layout.addWidget(QLabel("通用字典文件夹"))
        layout.addWidget(self.default_dict_folder)
        layout.addWidget(self.use_pre_dict_in_name)
        layout.addWidget(self.use_post_dict_in_name)
        layout.addWidget(QLabel("译前字典"))
        layout.addWidget(self.pre_dict)
        layout.addWidget(QLabel("GPT 字典"))
        layout.addWidget(self.gpt_dict)
        layout.addWidget(QLabel("译后字典"))
        layout.addWidget(self.post_dict)

        self.setLayout(layout)


class BackendSettings(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("翻译后端设置", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # GPT3.5 设置
        gpt35_section = QGroupBox("GPT3.5 设置")

        gpt35_layout = QVBoxLayout()
        self.gpt35_tokens = CustomTextEdit(self)
        self.gpt35_tokens.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gpt35_tokens.setPlaceholderText("GPT3.5 API 的 tokens")
        self.gpt35_tokens.setPlainText(
            "sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nsk-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
        self.gpt35_endpoint = CustomLineEdit(self)
        self.gpt35_endpoint.setPlaceholderText("GPT3.5 API 的 endpoint")
        self.gpt35_endpoint.setText("https://api.openai.com")
        self.gpt35_model_name = CustomLineEdit(self)
        self.gpt35_model_name.setPlaceholderText("（可选）替换的模型名称")
        self.gpt35_model_name.setText("")

        gpt35_layout.addWidget(QLabel("Tokens 列表"))
        gpt35_layout.addWidget(self.gpt35_tokens)
        gpt35_layout.addWidget(QLabel("API Endpoint"))
        gpt35_layout.addWidget(self.gpt35_endpoint)
        gpt35_layout.addWidget(QLabel("替换的模型名称"))
        gpt35_layout.addWidget(self.gpt35_model_name)
        gpt35_section.setLayout(gpt35_layout)

        # GPT4 设置
        gpt4_section = QGroupBox("GPT4 设置")

        gpt4_layout = QVBoxLayout()
        self.gpt4_tokens = CustomTextEdit(self)
        self.gpt4_tokens.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gpt4_tokens.setPlaceholderText("GPT4 API 的 tokens")
        self.gpt4_tokens.setPlainText(
            "sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.gpt4_endpoint = CustomLineEdit(self)
        self.gpt4_endpoint.setPlaceholderText("GPT4 API 的 endpoint")
        self.gpt4_endpoint.setText("https://api.openai.com")
        self.gpt4_model_name = CustomLineEdit(self)
        self.gpt4_model_name.setPlaceholderText("（可选）替换的模型名称")
        self.gpt4_model_name.setText("")

        gpt4_layout.addWidget(QLabel("Tokens 列表"))
        gpt4_layout.addWidget(self.gpt4_tokens)
        gpt4_layout.addWidget(QLabel("API Endpoint"))
        gpt4_layout.addWidget(self.gpt4_endpoint)
        gpt4_layout.addWidget(QLabel("替换的模型名称"))
        gpt4_layout.addWidget(self.gpt4_model_name)
        gpt4_section.setLayout(gpt4_layout)

        # BingGPT4 设置
        bing_gpt4_section = QGroupBox("BingGPT4 设置")

        bing_gpt4_layout = QVBoxLayout()
        self.bing_gpt4_cookies = CustomTextEdit(self)
        self.bing_gpt4_cookies.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bing_gpt4_cookies.setPlaceholderText(
            "BingGPT4 API 的 cookies 路径列表")
        self.bing_gpt4_cookies.setPlainText(
            "newbing_cookies/cookie1.json\nnewbing_cookies/cookie2.json")

        bing_gpt4_layout.addWidget(QLabel("Cookies 路径列表"))
        bing_gpt4_layout.addWidget(self.bing_gpt4_cookies)
        bing_gpt4_section.setLayout(bing_gpt4_layout)

        # SakuraLLM 设置
        sakura_section = QGroupBox("SakuraLLM 设置")

        sakura_layout = QVBoxLayout()
        self.sakura_endpoint = CustomLineEdit(self)
        self.sakura_endpoint.setPlaceholderText("SakuraLLM 的 endpoint")
        self.sakura_endpoint.setText("http://127.0.0.1:8080")
        self.sakura_model_name = CustomLineEdit(self)
        self.sakura_model_name.setPlaceholderText("（可选）替换的模型名称")
        self.sakura_model_name.setText("")

        sakura_layout.addWidget(QLabel("API Endpoint"))
        sakura_layout.addWidget(self.sakura_endpoint)
        sakura_layout.addWidget(QLabel("替换的模型名称"))
        sakura_layout.addWidget(self.sakura_model_name)
        sakura_section.setLayout(sakura_layout)

        # 添加各部分到主布局
        layout.addWidget(gpt35_section)
        layout.addWidget(gpt4_section)
        layout.addWidget(bing_gpt4_section)
        layout.addWidget(sakura_section)

        self.setLayout(layout)


class ProblemAnalyzeSettings(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("自动问题分析配置", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.problem_list = CustomTextEdit(self)
        self.problem_list.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.problem_list.setPlaceholderText("要发现的问题清单（每行一个）")
        self.problem_list.setPlainText(
            "词频过高\n标点错漏\n残留日文\n丢失换行\n多加换行\n比日文长\n字典使用")

        self.arinashi_dict = CustomTextEdit(self)
        self.arinashi_dict.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.arinashi_dict.setPlaceholderText("arinashi 字典（每行一个，格式：aaa: bbb）")
        self.arinashi_dict.setPlainText("aaa: bbb\nccc: ddd")

        layout.addWidget(QLabel("要发现的问题清单"))
        layout.addWidget(self.problem_list)
        layout.addWidget(QLabel("arinashi 字典"))
        layout.addWidget(self.arinashi_dict)

        self.setLayout(layout)
