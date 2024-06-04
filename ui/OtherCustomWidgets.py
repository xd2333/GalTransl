from qfluentwidgets import LineEdit, TextEdit


class CustomLineEdit(LineEdit):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():  # 当文件拖入此区域时为True
            event.accept()  # 接受拖入文件
        else:
            event.ignore()  # 忽略拖入文件

    def dropEvent(self, event):
        file_list = []
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            file_paths = [url.toLocalFile() for url in urls]
            for file_path in file_paths:
                file_list.append(file_path)
            self.setText(file_list[0])
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

class CustomTextEdit(TextEdit):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():  # 当文件拖入此区域时为True
            event.accept()  # 接受拖入文件
        else:
            event.ignore()  # 忽略拖入文件

    def dropEvent(self, event):
        file_list = []
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            file_paths = [url.toLocalFile() for url in urls]
            for file_path in file_paths:
                file_list.append(file_path)
            self.setText("\n".join(file_list))
            event.acceptProposedAction()
        else:
            super().dropEvent(event)