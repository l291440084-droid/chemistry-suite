"""PDF.js 电子书阅读器 — QWebEngineView 封装"""

import json
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QUrl, QObject, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from core.i18n import i18n


class PDFReaderBridge(QObject):
    """Python ↔ PDF.js 通信桥"""
    fileOpened = Signal(str)
    pageChanged = Signal(int, int)
    bookmarksChanged = Signal(str)
    contextMenu = Signal(str, int, int)  # selected_text, x, y

    @Slot(str)
    def onFileOpened(self, filename: str):
        self.fileOpened.emit(filename)

    @Slot(int, int)
    def onPageChanged(self, page: int, total: int):
        self.pageChanged.emit(page, total)

    @Slot(str)
    def onBookmarksChanged(self, data: str):
        self.bookmarksChanged.emit(data)

    @Slot(str, int, int)
    def onContextMenu(self, text: str, x: int, y: int):
        self.contextMenu.emit(text, x, y)


class PDFReaderWidget(QWidget):
    """PDF 电子书阅读器面板"""

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
        self.label_status = QLabel(i18n.tr("PDF 阅读器"))
        toolbar.addWidget(self.label_status)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # WebEngine
        self._webview = QWebEngineView()
        self._webview.setContextMenuPolicy(Qt.NoContextMenu)
        self._channel = QWebChannel()
        self._bridge = PDFReaderBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._webview.page().setWebChannel(self._channel)

        url = f"http://127.0.0.1:{self._port}/pdfjs/reader.html"
        self._webview.setUrl(QUrl(url))
        self._webview.loadFinished.connect(self._on_load_finished)

        layout.addWidget(self._webview)

        i18n.languageChanged.connect(self._update_ui_texts)

    def _update_ui_texts(self, lang_code=None):
        current = self.label_status.text()
        if "Ready" in current or "bereit" in current or "prêt" in current or "就绪" in current:
            self.label_status.setText(i18n.tr("PDF 阅读器就绪"))
        elif "failed" in current.lower() or "fehlgeschlagen" in current or "失败" in current:
            self.label_status.setText(i18n.tr("加载失败"))
        else:
            self.label_status.setText(i18n.tr("PDF 阅读器"))

    def _on_load_finished(self, ok: bool):
        self.label_status.setText(i18n.tr("PDF 阅读器就绪") if ok else i18n.tr("加载失败"))

    def _call_js(self, func: str, *args):
        js_args = ", ".join(json.dumps(a) for a in args)
        js = f"if (typeof {func} === 'function') {{ {func}({js_args}); }}"
        self._webview.page().runJavaScript(js)

    # ---- 公开 API ----

    def load_pdf(self, url: str, filename: str = ""):
        self._call_js("loadPDF", url, filename or url)

    @property
    def webview(self):
        return self._webview

    @property
    def signal_file_opened(self):
        return self._bridge.fileOpened

    @property
    def signal_page_changed(self):
        return self._bridge.pageChanged

    @property
    def signal_context_menu(self):
        return self._bridge.contextMenu
