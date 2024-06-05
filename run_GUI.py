import sys
import shutil
import time
import yaml
import os
from functools import partial
from PySide6.QtCore import Qt, QEasingCurve, QUrl, QThread, Signal, QObject, QTimer
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QScrollArea, QGroupBox, QLabel, QFrame, QFileDialog, 
    QMainWindow, QWidget, QSizePolicy, QStackedWidget, QSpacerItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtGui import QIcon, QPainter, QImage, QColor, QBrush, QFont, QDesktopServices, QPixmap
from qfluentwidgets import (
    PushButton, LineEdit, CheckBox, SpinBox, PrimaryPushButton, TextEdit, SmoothScrollArea, NavigationWidget, EditableComboBox,TransparentPushButton,
    NavigationInterface, NavigationItemPosition, InfoBarPosition, Dialog, FluentIcon as FIF,TableWidget,ProgressBar,IndeterminateProgressRing,ProgressRing, IndeterminateProgressBar,
    MessageBox, setTheme, Theme, MSFluentWindow, NavigationAvatarWidget, qrouter, SubtitleLabel, setFont, setThemeColor, 
)

from qframelesswindow import FramelessWindow


from ui import *

from GalTransl import (
    AUTHOR,
    CONFIG_FILENAME,
    CONTRIBUTORS,
    GALTRANSL_VERSION,
    PROGRAM_SPLASH,
    TRANSLATOR_SUPPORTED,
)
from GalTransl.__main__ import worker_with_progress
from ui import OtherCustomWidgets

GALTRANSL_GUI_VERSION = "0.0.3"

PROGRAM_PATH = os.path.dirname(os.path.abspath(__file__))

# coding:utf-8

class GaltranslWorker(QObject):
    progress = Signal(str)
    finished = Signal(bool)

    def __init__(self, project_dir_or_config_file, translator, is_batch=False):
        super().__init__()
        self.project_dir_or_config_file = project_dir_or_config_file
        self.project_dir = ""
        self.config_file_name = CONFIG_FILENAME
        self.translator = translator
        self.is_batch = is_batch

    def get_project_dir_or_config_file(self, project_dir_or_config_file, project_dir):
        project_dir_or_config_file = os.path.abspath(project_dir_or_config_file)
        if project_dir_or_config_file.endswith(".yaml"):
            config_file_name = os.path.basename(project_dir_or_config_file)
            project_dir = os.path.dirname(project_dir_or_config_file)
        else:
            config_file_name = CONFIG_FILENAME
            project_dir = project_dir_or_config_file

        if not os.path.exists(os.path.join(project_dir, config_file_name)):
            self.progress.emit(f"{project_dir} 文件夹内不存在配置文件 {config_file_name}，请检查后重新输入\n")
        else:
            return project_dir_or_config_file, project_dir, config_file_name

    def worker_ui(self, project_dir, config_file_name, translator):
        if self.get_project_dir_or_config_file(project_dir, project_dir):
            self.progress.emit("正在翻译中...")
            result = True
            try:
                worker_with_progress(project_dir, config_file_name, translator, show_banner=False, progress_signal=self.progress)
            except Exception as e:
                self.progress.emit(f"翻译过程中遇到问题: {e}")
                result = False
            finally:
                self.finished.emit(result)

    def run(self):
        try:
            self.project_dir_or_config_file, self.project_dir, self.config_file_name = self.get_project_dir_or_config_file(
                self.project_dir_or_config_file, self.project_dir
            )
            if self.translator not in TRANSLATOR_SUPPORTED:
                self.progress.emit(f"不支持的翻译器: {self.translator}")
                self.finished.emit(False)
                return
        except KeyboardInterrupt:
            self.progress.emit("\nGoodbye.")
            self.finished.emit(False)
            return
        self.worker_ui(self.project_dir, self.config_file_name, self.translator)


class WidgetRun(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.setAcceptDrops(True)
        self.init_ui()
        self.setAcceptDrops(True)
        self.batch_threads = []  # 保存所有启动的线程

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 创建各部分组件
        self.direct_run = DirectRunSection(self)
        self.batch_run = BatchRunSection(self)
        self.log_section = LogSection(self)
        
        # 将各部分组件添加到主布局
        left_and_right_layout = QHBoxLayout()
        left_and_right_layout.addWidget(self.direct_run)
        left_and_right_layout.addWidget(self.batch_run)
        main_layout.addLayout(left_and_right_layout)
        main_layout.addWidget(self.log_section)

        self.setLayout(main_layout)
        self.connect_signals()

    def connect_signals(self):
        # 连接 DirectRunSection 的信号到相应的槽函数
        self.direct_run.run_button.clicked.connect(self.run_direct)
        # self.direct_run.pushButton_select_dir.clicked.connect(self.direct_run.select_directory_input)
        # self.direct_run.pushButton_select_output_dir.clicked.connect(self.direct_run.select_directory_output)

        # 连接 BatchRunSection 的信号到相应的槽函数
        self.batch_run.add_button.clicked.connect(self.add_to_queue)
        self.batch_run.batch_run_button.clicked.connect(self.run_batch)

        # 连接 LogSection 的信号到相应的槽函数
        self.log_section.clear_log_button.clicked.connect(self.log_section.clear_log)

    def clear_log(self):
        self.log_section.clear_log()

    def run_direct(self):
        input_path = self.direct_run.files_input_dir.text()
        output_path = self.direct_run.files_output_dir.text()
        translator = self.direct_run.translator_combo.currentText()
        project_dict = self.direct_run.project_dict_input.toPlainText().strip().split('\n')

        if not input_path or not output_path or not translator:
            w = MessageBox("警告", "请填写所有字段", self)
            w.exec()
            return

        if not os.makedirs(output_path, exist_ok=True):
            print(f"创建输出目录：{output_path}")

        os.makedirs(os.path.join(PROGRAM_PATH, f"uiProjects/Project_{time.strftime('%Y%m%d%H%M%S')}"), exist_ok=True)
        project_dir = os.path.join(PROGRAM_PATH, f"uiProjects/Project_{time.strftime('%Y%m%d%H%M%S')}")
        os.makedirs(os.path.join(project_dir, "gt_output"), exist_ok=True)
        shutil.copy(os.path.join(PROGRAM_PATH, "uiProjects/_Config/config.yaml"), os.path.join(project_dir, "config.yaml"))
        shutil.copytree(input_path, os.path.join(project_dir, "gt_input"))

        for dict_item in project_dict:
            if dict_item.strip() != '':
                shutil.copy(dict_item.strip(), project_dir)

        print(f"直接运行：输入路径={input_path}, 输出路径={output_path}, 翻译器={translator}, 工程文件夹={project_dir}")

        self.log_section.log_display.clear()

        self.worker = GaltranslWorker(project_dir, translator)
        self.thread = QThread()

        self.worker.moveToThread(self.thread)

        # 延迟启动任务，确保线程启动后再运行
        self.thread.started.connect(lambda: QTimer.singleShot(50, self.worker.run))
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.on_run_finished)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.check_completion)

        print("准备启动线程...")

        self.thread.start()

        print("线程已启动...")

    def on_run_finished(self, success):
        output_path = self.direct_run.files_output_dir.text()
        project_dir = self.worker.project_dir

        for file_name in os.listdir(os.path.join(project_dir, "gt_output")):
            shutil.copy(os.path.join(project_dir, "gt_output", file_name), output_path)
        
        print("翻译完成")

    def update_progress(self, message):
        print(f"接收到进度信号: {message}")

        self.log_section.log_display.append(message)
        QTimer.singleShot(50, QApplication.processEvents)

    def check_completion(self, success, is_batch=False):
        if success and not is_batch:
            w = MessageBox("完成", "翻译已完成！", self)
            w.exec()
        else:
            w = MessageBox("错误", "翻译过程中遇到问题！", self)
            w.exec()

    def run_batch(self):
        row_count = self.batch_run.queue_table.rowCount()
        if row_count == 0:
            print("队列为空")
            return

        self.batch_index = 0
        self.run_next_batch()
    
    def run_next_batch(self):
        if self.batch_index >= self.batch_run.queue_table.rowCount():
            print("所有批量任务完成")
            w = MessageBox("完成", "所有批量任务完成！", self)
            w.exec()
            self.cleanup_threads()
            return

        project_folder = self.batch_run.queue_table.item(self.batch_index, 0).text()
        translator = self.batch_run.queue_table.item(self.batch_index, 1).text()

        self.worker = GaltranslWorker(project_folder, translator, is_batch=True)
        self.thread = QThread()
        self.batch_threads.append(self.thread)  # 保持对线程的引用，防止其被垃圾回收

        print(f"批量运行：工程文件夹={project_folder}, 翻译器={translator}")

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(lambda: QTimer.singleShot(50, self.worker.run))
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.run_next_batch)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(lambda success: self.check_completion(success, is_batch=True))

        self.thread.start()

        print(f"线程已启动: 工程文件夹={project_folder}, 翻译器={translator}")

        self.batch_index += 1
    
    def add_to_queue(self):
        project_folders = self.batch_run.project_folders.toPlainText().strip().split('\n')
        translator = self.batch_run.batch_translator_combo.currentText()

        if not project_folders or not translator:
            w = MessageBox("警告", "请填写所有字段", self)
            w.exec()
            return

        for folder in project_folders:
            row_position = self.batch_run.queue_table.rowCount()
            self.batch_run.queue_table.insertRow(row_position)
            self.batch_run.queue_table.setItem(row_position, 0, QTableWidgetItem(folder))
            self.batch_run.queue_table.setItem(row_position, 1, QTableWidgetItem(translator))

            # 添加删除按钮
            delete_button = TransparentPushButton(FIF.DELETE, "删除", self)
            delete_button.clicked.connect(partial(self.delete_row, delete_button))
            self.batch_run.queue_table.setCellWidget(row_position, 2, delete_button)

        self.batch_run.queue_table.resizeColumnsToContents()
        self.batch_run.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.batch_run.queue_table.horizontalHeader().setStretchLastSection(True)
        print(f"添加到队列：工程文件夹={project_folders}, 翻译器={translator}")

    def delete_row(self, button):
        # 查找按钮所在的行
        index = self.batch_run.queue_table.indexAt(button.pos())
        if index.isValid():
            self.batch_run.queue_table.removeRow(index.row())
            print(f"删除队列中的行：{index.row()}")

    def cleanup_threads(self):
        try:
            for thread in self.batch_threads:
                thread.quit()
                thread.wait()
            self.batch_threads.clear()
        except Exception as e:
            print(f"清理线程时遇到问题: {e}")


class Widget_Setting(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.init_ui()

    def init_ui(self):
        self.label = QLabel("这里是设置界面，目前没什么可以设置的", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 25px;")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

class Widget_About(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.init_ui()

    def init_ui(self):
        
        # 图片
        pic = QGroupBox()
        pic.setStyleSheet(""" QGroupBox {border: 0px solid lightgray; border-radius: 8px;}""")
        layout_pic = QHBoxLayout()

        self.image_label = QLabel(self)
        pixmap = QPixmap(os.path.join("./ui/img","sticker.png"))
        self.image_label.setFixedSize(350, 393)
        self.image_label.setPixmap(pixmap)
        self.image_label.setScaledContents(True)


        layout_pic.addWidget(self.image_label)
        pic.setLayout(layout_pic)
        
        # 文本
        text_group = QGroupBox()
        text_group.setStyleSheet(""" QGroupBox {border: 0px solid lightgray; border-radius: 8px;}""")
        text_group_layout = QVBoxLayout()


        self.text_label = QLabel(self)
        self.text_label.setStyleSheet("font-size: 25px;")
        self.text_label.setText("测试版本UI，可能有很多bug")
        self.text_label.setAlignment(Qt.AlignCenter)

        self.text_label_2 = QLabel(self)
        self.text_label_2.setStyleSheet("font-size: 18px;")
        self.text_label_2.setText(f"核心版本：v{GALTRANSL_VERSION}\nGUI版本： v{GALTRANSL_GUI_VERSION}")
        self.text_label_2.setAlignment(Qt.AlignCenter)

        text_group_layout.addStretch(1)  # 添加伸缩项
        text_group_layout.addWidget(self.text_label)
        text_group_layout.addStretch(1)  # 添加伸缩项
        text_group_layout.addWidget(self.text_label_2)
        text_group_layout.addStretch(1)  # 添加伸缩项
        text_group.setLayout(text_group_layout)

        container = QVBoxLayout()

        self.setLayout(container)
        container.setSpacing(28) # 设置布局内控件的间距为28
        container.setContentsMargins(50, 70, 50, 30) # 设置布局的边距, 也就是外边框距离，分别为左、上、右、下

        container.addStretch(1)  # 添加伸缩项
        container.addWidget(pic)
        container.addWidget(text_group)
        container.addStretch(1)  # 添加伸缩项


class YamlReaderThread(QThread):
    yaml_loaded = Signal(dict)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        with open(self.file_path, 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        self.yaml_loaded.emit(config)


class WidgetWriteYaml(SmoothScrollArea):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.setAcceptDrops(True)
        self.config_loaded = False
        self.config_load_error = False
        
        self.config_file_path_absolute = os.path.join(PROGRAM_PATH, "uiProjects/_Config/config.yaml")
        print(self.config_file_path_absolute)
        self.setStyleSheet("""
                    background: transparent;
                    border-radius: 8px;
                    QFrame{
                    border: 1px solid #000000;
                    }
                    """)
        self.init_ui()

    def init_ui(self):
        self.setContentsMargins(50, 70, 50, 30)
        self.setWidgetResizable(True)

        self.config_buttons = ConfigButtons(self)
        self.program_settings = ProgramSettings(self)
        self.plugin_settings = PluginSettings(self)
        self.proxy_settings = ProxySettings(self)
        self.dictionary_settings = DictionarySettings(self)
        self.backend_settings = BackendSettings(self)
        self.problem_analyze_settings = ProblemAnalyzeSettings(self)

        # 将各部分添加到布局
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.config_buttons)
        left_layout.addWidget(self.program_settings)
        left_layout.addWidget(self.plugin_settings)
        left_layout.addWidget(self.proxy_settings)
        left_layout.addWidget(self.dictionary_settings)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.backend_settings)
        right_layout.addWidget(self.problem_analyze_settings)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.setScrollAnimation(Qt.Vertical, 500, QEasingCurve.OutQuint)
        self.setScrollAnimation(Qt.Horizontal, 500, QEasingCurve.OutQuint)
        self.setWidgetResizable(True)
        self.setWidget(main_widget)

        self.config_buttons.pushButton_read_yaml.clicked.connect(
            self.read_yaml)
        self.config_buttons.pushButton_write_yaml.clicked.connect(
            self.write_yaml)
        self.config_buttons.pushButton_reset_config.clicked.connect(
            self.reset_config)

        if not self.config_loaded and not self.config_load_error:
            try:
                self.read_yaml()
                self.config_loaded = True
            except Exception as e:
                print(f"[ERROR] 读取配置文件失败：{e}")
                self.config_load_error = True

    def read_yaml(self, file_path=None):
        if not file_path:
            file_path = self.config_file_path_absolute
        if not os.path.exists(file_path) or file_path == '':
            print("[ERROR] 请选择文件路径")
            return

        self.yaml_reader_thread = YamlReaderThread(file_path)
        self.yaml_reader_thread.yaml_loaded.connect(self.on_yaml_loaded)
        self.yaml_reader_thread.start()

    def on_yaml_loaded(self, config):
        # 读取common设置
        common_settings = config.get('common', {})
        self.program_settings.save_log.setChecked(common_settings.get('saveLog', False))
        self.program_settings.workers_per_project.setValue(common_settings.get('workersPerProject', 1))
        language = common_settings.get('language', 'ja2zh-cn').split('2')
        if len(language) == 2:
            self.program_settings.source_language.setCurrentText(language[0])
            self.program_settings.target_language.setCurrentText(language[1])
        self.program_settings.save_steps.setValue(common_settings.get('save_steps', 1))
        self.program_settings.linebreak_symbol.setText(str(common_settings.get('linebreakSymbol', '\\r\\n')))
        self.program_settings.skip_h.setChecked(common_settings.get('skipH', False))
        self.program_settings.skip_retry.setChecked(common_settings.get('skipRetry', False))
        self.program_settings.retransl_fail.setChecked(common_settings.get('retranslFail', False))
        self.program_settings.retransl_key.setCurrentText(common_settings.get('retranslKey', ''))
        self.program_settings.num_per_request_translate.setValue(common_settings.get('gpt.numPerRequestTranslate', 8))
        self.program_settings.stream_output_mode.setChecked(common_settings.get('gpt.streamOutputMode', True))
        self.program_settings.enable_proof_read.setChecked(common_settings.get('gpt.enableProofRead', False))
        self.program_settings.num_per_request_proof_read.setValue(common_settings.get('gpt.numPerRequestProofRead', 7))
        self.program_settings.restore_context_mode.setChecked(common_settings.get('gpt.restoreContextMode', True))
        self.program_settings.transl_dropout.setValue(common_settings.get('gpt.transl_dropout', 0))
        self.program_settings.transl_style.setCurrentText(common_settings.get('gpt.transl_style', '流畅'))

        # 读取plugin设置
        plugin_settings = config.get('plugin', {})
        self.plugin_settings.file_plugin.setCurrentText(plugin_settings.get('filePlugin', 'file_galtransl_json'))
        self.plugin_settings.text_plugins.setPlainText('\n'.join(plugin_settings.get('textPlugins', [])))

        # 读取proxy设置
        proxy_settings = config.get('proxy', {})
        self.proxy_settings.enable_proxy.setChecked(proxy_settings.get('enableProxy', False))
        proxies = proxy_settings.get('proxies', [])
        if proxies:
            self.proxy_settings.proxy_address.setText(proxies[0].get('address', 'http://127.0.0.1:7890'))

        # 读取dictionary设置
        dictionary_settings = config.get('dictionary', {})
        self.dictionary_settings.default_dict_folder.setText(dictionary_settings.get('defaultDictFolder', 'Dict'))
        self.dictionary_settings.use_pre_dict_in_name.setChecked(dictionary_settings.get('usePreDictInName', False))
        self.dictionary_settings.use_post_dict_in_name.setChecked(dictionary_settings.get('usePostDictInName', False))
        self.dictionary_settings.pre_dict.setPlainText('\n'.join(dictionary_settings.get('preDict', [])))
        self.dictionary_settings.gpt_dict.setPlainText('\n'.join(dictionary_settings.get('gpt.dict', [])))
        self.dictionary_settings.post_dict.setPlainText('\n'.join(dictionary_settings.get('postDict', [])))

        # 读取backendSpecific设置
        backend_specific_settings = config.get('backendSpecific', {})
        gpt35_settings = backend_specific_settings.get('GPT35', {})
        self.backend_settings.gpt35_tokens.setPlainText('\n'.join(token['token'] for token in gpt35_settings.get('tokens', [])))
        self.backend_settings.gpt35_endpoint.setText(gpt35_settings.get('tokens', [{}])[0].get('endpoint', 'https://api.openai.com'))
        self.backend_settings.gpt35_model_name.setText(gpt35_settings.get('rewriteModelName', ''))

        gpt4_settings = backend_specific_settings.get('GPT4', {})
        self.backend_settings.gpt4_tokens.setPlainText('\n'.join(token['token'] for token in gpt4_settings.get('tokens', [])))
        self.backend_settings.gpt4_endpoint.setText(gpt4_settings.get('tokens', [{}])[0].get('endpoint', 'https://api.openai.com'))
        self.backend_settings.gpt4_model_name.setText(gpt4_settings.get('rewriteModelName', ''))

        bing_gpt4_settings = backend_specific_settings.get('bingGPT4', {})
        self.backend_settings.bing_gpt4_cookies.setPlainText('\n'.join(bing_gpt4_settings.get('cookiePath', [])))

        sakura_settings = backend_specific_settings.get('SakuraLLM', {})
        self.backend_settings.sakura_endpoints.setPlainText('\n'.join(sakura_settings.get('endpoints', [])))
        self.backend_settings.sakura_model_name.setText(sakura_settings.get('rewriteModelName', ''))

        # 读取problemAnalyze设置
        problem_analyze_settings = config.get('problemAnalyze', {})
        self.problem_analyze_settings.problem_list.setPlainText('\n'.join(problem_analyze_settings.get('problemList', [])))
        arinashi_dict = problem_analyze_settings.get('arinashiDict', {})
        self.problem_analyze_settings.arinashi_dict.setPlainText('\n'.join(f'{k}: {v}' for k, v in arinashi_dict.items()))

        print(f"[INFO] 配置已读取")


    def write_yaml(self, file_path=None):
        if not file_path:
            file_path = self.config_file_path_absolute
        if not os.path.exists(file_path) or file_path == '':
            print("[ERROR] 请选择文件路径")
            return

        common_settings = {
            'saveLog': self.program_settings.save_log.isChecked(),
            'workersPerProject': self.program_settings.workers_per_project.value(),
            'language': f"{self.program_settings.source_language.currentText()}2{self.program_settings.target_language.currentText()}",
            'save_steps': self.program_settings.save_steps.value(),
            'linebreakSymbol': self.program_settings.linebreak_symbol.text(),
            'skipH': self.program_settings.skip_h.isChecked(),
            'skipRetry': self.program_settings.skip_retry.isChecked(),
            'retranslFail': self.program_settings.retransl_fail.isChecked(),
            'retranslKey': self.program_settings.retransl_key.currentText(),
            'gpt.numPerRequestTranslate': self.program_settings.num_per_request_translate.value(),
            'gpt.streamOutputMode': self.program_settings.stream_output_mode.isChecked(),
            'gpt.enableProofRead': self.program_settings.enable_proof_read.isChecked(),
            'gpt.numPerRequestProofRead': self.program_settings.num_per_request_proof_read.value(),
            'gpt.restoreContextMode': self.program_settings.restore_context_mode.isChecked(),
            'gpt.transl_dropout': self.program_settings.transl_dropout.value(),
            'gpt.transl_style': self.program_settings.transl_style.currentText()
        }

        plugin_settings = {
            'filePlugin': self.plugin_settings.file_plugin.currentText(),
            'textPlugins': [plugin for plugin in self.plugin_settings.text_plugins.toPlainText().split('\n') if plugin.strip() != '']
        }

        proxy_settings = {
            'enableProxy': self.proxy_settings.enable_proxy.isChecked(),
            'proxies': [{'address': self.proxy_settings.proxy_address.text()}]
        }

        dictionary_settings = {
            'defaultDictFolder': self.dictionary_settings.default_dict_folder.text(),
            'usePreDictInName': self.dictionary_settings.use_pre_dict_in_name.isChecked(),
            'usePostDictInName': self.dictionary_settings.use_post_dict_in_name.isChecked(),
            'preDict': [dict_item for dict_item in self.dictionary_settings.pre_dict.toPlainText().split('\n') if dict_item.strip() != ''],
            'gpt.dict': [dict_item for dict_item in self.dictionary_settings.gpt_dict.toPlainText().split('\n') if dict_item.strip() != ''],
            'postDict': [dict_item for dict_item in self.dictionary_settings.post_dict.toPlainText().split('\n') if dict_item.strip() != '']
        }

        backend_specific_settings = {
            'GPT35': {
                'tokens': [{'token': token, 'endpoint': self.backend_settings.gpt35_endpoint.text()} for token in self.backend_settings.gpt35_tokens.toPlainText().split('\n') if token.strip() != ''],
                'rewriteModelName': self.backend_settings.gpt35_model_name.text()
            },
            'GPT4': {
                'tokens': [{'token': token, 'endpoint': self.backend_settings.gpt4_endpoint.text()} for token in self.backend_settings.gpt4_tokens.toPlainText().split('\n') if token.strip() != ''],
                'rewriteModelName': self.backend_settings.gpt4_model_name.text()
            },
            'bingGPT4': {
                'cookiePath': [path for path in self.backend_settings.bing_gpt4_cookies.toPlainText().split('\n') if path.strip() != '']
            },
            'SakuraLLM': {
                'endpoints': [endpoints for endpoints in self.backend_settings.sakura_endpoints.toPlainText().split('\n') if endpoints.strip() != ''],
                'rewriteModelName': self.backend_settings.sakura_model_name.text()
            }
        }

        problem_analyze_settings = {
            'problemList': [problem for problem in self.problem_analyze_settings.problem_list.toPlainText().split('\n') if problem.strip() != ''],
            'arinashiDict': {kv.split(':')[0].strip(): kv.split(':')[1].strip() for kv in self.problem_analyze_settings.arinashi_dict.toPlainText().split('\n') if ':' in kv}
        }

        config = {
            'common': common_settings,
            'plugin': plugin_settings,
            'proxy': proxy_settings,
            'dictionary': dictionary_settings,
            'backendSpecific': backend_specific_settings,
            'problemAnalyze': problem_analyze_settings
        }

        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, allow_unicode=True, sort_keys=False, default_flow_style=False)

        print(f"[INFO] 配置已写入 {file_path}")

    def reset_config(self):
        default_config_path = os.path.join(PROGRAM_PATH, "uiProjects/_Config/config.inc.yaml")
        self.yaml_reader_thread = YamlReaderThread(default_config_path)
        self.yaml_reader_thread.yaml_loaded.connect(self.on_yaml_loaded_and_write)
        self.yaml_reader_thread.start()

    def on_yaml_loaded_and_write(self, config):
        self.on_yaml_loaded(config)
        self.write_yaml()
        print("[INFO] 已重置配置")

class CustomTitleBar(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(18, 18)
        self.titleLabel = QLabel(self)

        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.addWidget(self.iconLabel)
        self.hBoxLayout.addWidget(self.titleLabel)
        self.hBoxLayout.addStretch()

    def setTitle(self, title):
        self.titleLabel.setText(title)
        self.titleLabel.adjustSize()

    def setIcon(self, icon):
        self.iconLabel.setPixmap(QIcon(icon).pixmap(32, 32))


class Window(MSFluentWindow):
    def __init__(self):
        super().__init__()

        # create sub interface
        self.widgetWriteYaml = WidgetWriteYaml("Write YAML")
        self.widgetRun = WidgetRun("Run")
        self.widgetSetting = Widget_Setting("Setting")
        self.widgetAbout = Widget_About("About")

        self.initNavigation()
        self.initWindow()

    def initNavigation(self):
        # Add sub interfaces with icons
        self.addSubInterface(self.widgetWriteYaml, FIF.EDIT, '配置文件')
        self.addSubInterface(self.widgetRun, FIF.PLAY, '运行')
        self.addSubInterface(self.widgetSetting, FIF.SETTING, '设置')
        self.addSubInterface(self.widgetAbout, FIF.INFO, '关于')

        # Add the help item at the bottom
        self.navigationInterface.addItem(
            routeKey='Readme',
            icon=FIF.HELP,
            text='Readme',
            onClick=self.openReadme,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )

        # Set the default item to 'Write YAML'
        self.navigationInterface.setCurrentItem(
            self.widgetWriteYaml.objectName())

    def initWindow(self):
        self.resize(1600, 900)
        self.setWindowIcon(QIcon('./img/logo.png'))
        self.setWindowTitle(f'Galtransl Core v{GALTRANSL_VERSION} GUI v{GALTRANSL_GUI_VERSION}')

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
        with open('./ui/qss/dark.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def openReadme(self):
        QDesktopServices.openUrl(
            QUrl("https://github.com/xd2333/GalTransl/blob/main/README.md"))

if __name__ == '__main__':
    setTheme(Theme.DARK)
    setThemeColor(QColor(80,141,249))

    app = QApplication(sys.argv)
    window = Window()
    window.show()
    app.exec()
