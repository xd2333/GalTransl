from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QFileDialog, QHeaderView
)
from qfluentwidgets import (
    PushButton, PrimaryPushButton, EditableComboBox, TableWidget, FluentIcon as FIF
)

from .OtherCustomWidgets import CustomLineEdit, CustomTextEdit
from GalTransl import TRANSLATOR_SUPPORTED


class DirectRunSection(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("直接运行", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 输入路径框
        self.files_input_dir = CustomLineEdit(self)
        self.files_input_dir.setPlaceholderText("请选择输入目录")
        self.pushButton_select_dir = PushButton('选择目录', self, FIF.FOLDER)
        self.pushButton_select_dir.clicked.connect(self.select_directory_input)

        layout_dir_selection = QHBoxLayout()
        layout_dir_selection_lable = QVBoxLayout()
        layout_dir_selection_lable.addWidget(QLabel("文本输入目录（gt_input）"))
        layout_dir_selection.addWidget(self.files_input_dir)
        layout_dir_selection.addWidget(self.pushButton_select_dir)
        layout.addWidget(QLabel("输入文本文件夹"))
        layout.addLayout(layout_dir_selection)

        # 输出路径框
        self.files_output_dir = CustomLineEdit(self)
        self.files_output_dir.setPlaceholderText("请选择输出目录")
        self.pushButton_select_output_dir = PushButton(
            '选择目录', self, FIF.FOLDER)
        self.pushButton_select_output_dir.clicked.connect(
            self.select_directory_output)

        layout_output_dir_selection = QHBoxLayout()
        layout_output_dir_selection_lable = QVBoxLayout()
        layout_output_dir_selection_lable.addWidget(QLabel("文本输出目录（gt_input）"))
        layout_output_dir_selection.addWidget(self.files_output_dir)
        layout_output_dir_selection.addWidget(
            self.pushButton_select_output_dir)
        layout.addWidget(QLabel("输出文本文件夹"))
        layout.addLayout(layout_output_dir_selection)

        # 翻译器下拉菜单
        self.translator_combo = EditableComboBox(self)
        self.translator_combo.addItems(TRANSLATOR_SUPPORTED)
        layout.addWidget(QLabel("选择翻译器"))
        layout.addWidget(self.translator_combo)

        # 项目字典输入框
        self.project_dict_input = CustomTextEdit(self)
        self.project_dict_input.setPlaceholderText("项目字典，一行一个，支持拖拽")
        layout.addWidget(QLabel("项目字典"))
        layout.addWidget(self.project_dict_input)

        # 运行按钮
        self.run_button = PrimaryPushButton('运行', self)
        layout.addWidget(self.run_button)

        self.setLayout(layout)

    def select_directory(self, directory_type):
        directory = QFileDialog.getExistingDirectory(self, '选择目录', '')
        if directory:
            if directory_type == "input":
                self.files_input_dir.setText(directory)
            elif directory_type == "output":
                self.files_output_dir.setText(directory)

    def select_directory_input(self):
        self.select_directory("input")

    def select_directory_output(self):
        self.select_directory("output")


class BatchRunSection(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("批量运行", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 多行文本输入框
        self.project_folders = CustomTextEdit(self)
        self.project_folders.setPlaceholderText(
            "输入你自己的包含配置的工程文件夹，一行一个，支持拖拽（不受UI配置文件的影响）")
        layout.addWidget(QLabel("工程文件夹"))
        layout.addWidget(self.project_folders)

        # 翻译器下拉菜单
        self.batch_translator_combo = EditableComboBox(self)
        self.batch_translator_combo.addItems(TRANSLATOR_SUPPORTED)
        layout.addWidget(QLabel("选择翻译器"))
        layout.addWidget(self.batch_translator_combo)

        # 添加按钮
        self.add_button = PrimaryPushButton('添加', self)
        layout.addWidget(self.add_button)

        # 队列界面
        self.queue_table = TableWidget(self)
        self.queue_table.setSelectRightClickedRow(True)
        self.queue_table.setBorderVisible(True)
        self.queue_table.setWordWrap(False)
        self.queue_table.setBorderRadius(8)
        self.queue_table.setColumnCount(3)
        self.queue_table.verticalHeader().hide()
        self.queue_table.setHorizontalHeaderLabels(['待翻译工程', '翻译器', '操作'])
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.queue_table.resizeColumnsToContents()
        self.queue_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.queue_table)

        # 运行按钮
        self.batch_run_button = PrimaryPushButton('运行', self)
        layout.addWidget(self.batch_run_button)

        self.setLayout(layout)


class LogSection(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("日志", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.log_display = CustomTextEdit(self)
        self.log_display.setReadOnly(True)

        # 清空日志按钮
        self.clear_log_button = PushButton("清空日志", self)
        layout.addWidget(self.clear_log_button)
        layout.addWidget(self.log_display)

        self.setLayout(layout)

    def clear_log(self):
        self.log_display.clear()
