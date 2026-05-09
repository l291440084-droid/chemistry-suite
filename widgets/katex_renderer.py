"""KaTeX 公式编辑器 — QWebEngineView 封装"""

import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import QUrl, QObject, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel


class KaTeXBridge(QObject):
    """Python ↔ KaTeX 通信桥"""
    contentChanged = Signal(str)
    favoritesChanged = Signal(str)

    @Slot(str)
    def onContentChanged(self, text: str):
        self.contentChanged.emit(text)

    @Slot(str)
    def onFavoritesChanged(self, data: str):
        self.favoritesChanged.emit(data)


class KaTeXEditorWidget(QWidget):
    """公式编辑器面板"""

    def __init__(self, http_port: int = 8766, parent=None):
        super().__init__(parent)
        self._port = http_port
        self._bridge = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self.btn_copy = QPushButton("复制内容")
        self.btn_copy.clicked.connect(self._copy_content)

        self.btn_paste = QPushButton("粘贴")
        self.btn_paste.clicked.connect(self._paste_content)

        self.label_status = QLabel("")

        toolbar.addWidget(self.btn_copy)
        toolbar.addWidget(self.btn_paste)
        toolbar.addWidget(self.label_status)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # WebEngine
        self._webview = QWebEngineView()
        self._channel = QWebChannel()
        self._bridge = KaTeXBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._webview.page().setWebChannel(self._channel)

        url = f"http://127.0.0.1:{self._port}/katex/editor.html"
        self._webview.setUrl(QUrl(url))
        self._webview.loadFinished.connect(self._on_load_finished)

        layout.addWidget(self._webview)

    def _on_load_finished(self, ok: bool):
        self.label_status.setText("KaTeX 就绪" if ok else "加载失败")

    def _call_js(self, func: str, *args):
        js_args = ", ".join(json.dumps(a) for a in args)
        js = f"if (typeof {func} === 'function') {{ {func}({js_args}); }}"
        self._webview.page().runJavaScript(js)

    def _call_js_str(self, func: str) -> str:
        """调用 JS 并获取返回值 (异步，此处简化)"""
        self._webview.page().runJavaScript(f"{func}();")

    def _copy_content(self):
        self._webview.page().runJavaScript("getContent();", self._on_get_content)

    def _on_get_content(self, text):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.label_status.setText("已复制")

    def _paste_content(self):
        from PySide6.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        if text:
            self.set_content(text)

    # ---- 公开 API ----

    def set_content(self, text: str):
        self._call_js("setContent", text)

    def get_content(self):
        self._webview.page().runJavaScript("getContent();")

    def get_favorites(self) -> list:
        return []

    @property
    def signal_content_changed(self):
        return self._bridge.contentChanged
