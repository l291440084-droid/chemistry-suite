"""Ketcher 2D 化学结构编辑器 — QWebEngineView 封装"""

import json
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QApplication,
)
from PySide6.QtCore import QUrl, QObject, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from core.i18n import i18n


class KetcherBridge(QObject):
    """Python ↔ Ketcher JS 双向通信桥"""
    smilesChanged = Signal(str)
    molfileReady = Signal(str)

    @Slot(str)
    def onSmiles(self, smiles: str):
        self.smilesChanged.emit(smiles)

    @Slot(str)
    def onMolfile(self, molfile: str):
        self.molfileReady.emit(molfile)

    @Slot(str)
    def onSmilesChanged(self, smiles: str):
        """Ketcher 中结构变化时自动回调"""
        self.smilesChanged.emit(smiles)


class ChemEditorWidget(QWidget):
    """2D 化学结构编辑器面板"""

    def __init__(self, web_dir: str = None, http_port: int = 8766, parent=None):
        super().__init__(parent)
        self._port = http_port
        if web_dir:
            self._web_dir = str(Path(web_dir).resolve())
        else:
            self._web_dir = str(Path(__file__).resolve().parent.parent / "web")
        self._server = None
        self._bridge = None
        self._init_http_server()
        self._init_ui()

    def _init_http_server(self):
        """HTTP 服务器由 main.py 统一启动，此处仅保留引用以避免重复绑定"""
        import main
        global_server = getattr(main, "_http_server", None)
        if global_server is not None:
            self._server = global_server
            return
        web_root = self._web_dir

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=web_root, **kwargs)

            def log_message(self, format, *args):
                pass

        self._server = HTTPServer(("127.0.0.1", self._port), Handler)
        main._http_server = self._server
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self.smiles_input = QLineEdit()
        self.smiles_input.setPlaceholderText(
            i18n.tr("输入 SMILES / InChI / 化合物名称，回车加载...")
        )
        self.smiles_input.returnPressed.connect(self._on_smiles_enter)

        self.btn_get_smiles = QPushButton(i18n.tr("获取SMILES"))
        self.btn_get_smiles.clicked.connect(self._get_smiles)

        self.btn_clear = QPushButton(i18n.tr("清除"))
        self.btn_clear.clicked.connect(self.clear)

        self.btn_to_3d = QPushButton("→3D")
        self.btn_to_3d.setToolTip(i18n.tr("推送当前结构到 3D 分子查看器"))
        self.btn_to_3d.setMaximumWidth(45)

        self.label_status = QLabel("")

        toolbar.addWidget(self.smiles_input)
        toolbar.addWidget(self.btn_get_smiles)
        toolbar.addWidget(self.btn_clear)
        toolbar.addWidget(self.btn_to_3d)
        toolbar.addWidget(self.label_status)
        layout.addLayout(toolbar)

        # WebEngine 区域
        self._webview = QWebEngineView()
        self._channel = QWebChannel()
        self._bridge = KetcherBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._webview.page().setWebChannel(self._channel)

        wrapper_url = f"http://127.0.0.1:{self._port}/ketcher/wrapper.html"
        self._webview.setUrl(QUrl(wrapper_url))
        self._webview.loadFinished.connect(self._on_load_finished)

        layout.addWidget(self._webview)

        i18n.languageChanged.connect(self._update_ui_texts)

    def _update_ui_texts(self, lang_code=None):
        """语言切换时刷新 UI"""
        self.smiles_input.setPlaceholderText(
            i18n.tr("输入 SMILES / InChI / 化合物名称，回车加载...")
        )
        self.btn_get_smiles.setText(i18n.tr("获取SMILES"))
        self.btn_clear.setText(i18n.tr("清除"))
        self.btn_to_3d.setToolTip(i18n.tr("推送当前结构到 3D 分子查看器"))
        # Update status label based on current state
        current = self.label_status.text()
        if "Ketcher" in current or "Ketcher" in self.label_status.text():
            pass  # keep load status as-is
        elif "已加载" in current or "画布" in current:
            self.label_status.setText(i18n.tr("画布已清除"))
        elif current:
            pass

    def _on_load_finished(self, ok: bool):
        if ok:
            self.label_status.setText(i18n.tr("Ketcher 就绪"))
        else:
            self.label_status.setText(i18n.tr("Ketcher 加载失败"))

    def _on_smiles_enter(self):
        smiles = self.smiles_input.text().strip()
        if smiles:
            self.set_smiles(smiles)

    def _get_smiles(self):
        self._webview.page().runJavaScript("getSmilesAsync();")

    # ---- 公开 API ----

    def set_smiles(self, smiles: str):
        escaped = json.dumps(smiles)
        js = f"setMolecule({escaped});"
        self._webview.page().runJavaScript(js)
        short = smiles[:40] + "..." if len(smiles) > 40 else smiles
        self.label_status.setText(i18n.tr("已加载: ") + short)

    def get_smiles(self) -> str:
        result = []

        def callback(s):
            result.append(s)

        self._bridge.smilesChanged.connect(callback)
        self._webview.page().runJavaScript("getSmilesAsync();")
        time.sleep(0.1)
        QApplication.processEvents()
        try:
            self._bridge.smilesChanged.disconnect(callback)
        except Exception:
            pass
        return result[0] if result else ""

    def get_molfile(self) -> str:
        result = []

        def callback(m):
            result.append(m)

        self._bridge.molfileReady.connect(callback)
        self._webview.page().runJavaScript("getMolfileAsync();")
        time.sleep(0.1)
        QApplication.processEvents()
        try:
            self._bridge.molfileReady.disconnect(callback)
        except Exception:
            pass
        return result[0] if result else ""

    def clear(self):
        self._webview.page().runJavaScript("clearCanvas();")
        self.smiles_input.clear()
        self.label_status.setText(i18n.tr("画布已清除"))

    def add_fragment(self, smiles: str):
        escaped = json.dumps(smiles)
        js = f"addFragment({escaped});"
        self._webview.page().runJavaScript(js)

    @property
    def signal_smiles_changed(self):
        return self._bridge.smilesChanged

    @property
    def signal_molfile_ready(self):
        return self._bridge.molfileReady
