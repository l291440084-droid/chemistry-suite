"""原生电子书阅读器 — 使用 PDF.js 渲染，Qt 原生控件外壳"""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QSpinBox, QSplitter, QMenu, QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QUrl, QObject, Signal, Slot, QPoint, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QFont
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from core.i18n import i18n


# ── 通信桥 ──────────────────────────────────────────────────────
class PDFReaderBridge(QObject):
    """Python ↔ PDF.js 通信桥"""
    fileOpened = Signal(str, int)      # filename, total_pages
    pageChanged = Signal(int, int)     # current_page, total_pages
    contextMenu = Signal(str, int, int)  # selected_text, x, y
    importRequested = Signal()
    loadFailed = Signal(str, str)       # filename, error
    openExternal = Signal(str)          # filepath
    searchResult = Signal(int, int)     # count, page

    @Slot(str, int)
    def onFileOpened(self, filename: str, total: int):
        self.fileOpened.emit(filename, total)

    @Slot(int, int)
    def onPageChanged(self, page: int, total: int):
        self.pageChanged.emit(page, total)

    @Slot(str, int, int)
    def onContextMenu(self, text: str, x: int, y: int):
        self.contextMenu.emit(text, x, y)

    @Slot(str, str)
    def onLoadFailed(self, filename: str, error: str):
        self.loadFailed.emit(filename, error)

    @Slot(str)
    def onOpenExternal(self, filepath: str):
        self.openExternal.emit(filepath)

    @Slot(int, int)
    def onSearchResult(self, count: int, page: int):
        self.searchResult.emit(count, page)


# ── 工具栏 ──────────────────────────────────────────────────────
class PDFToolbar(QWidget):
    pagePrev = Signal()
    pageNext = Signal()
    pageGo = Signal(int)
    zoomChanged = Signal(str)
    searchRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(4, 2, 4, 2)
        lo.setSpacing(4)

        self.btn_import = QPushButton(i18n.tr("导入书籍"))
        self.btn_import.setFixedHeight(26)
        lo.addWidget(self.btn_import)

        lo.addSpacing(8)

        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedSize(30, 26)
        self.btn_prev.setToolTip(i18n.tr("上一页"))
        lo.addWidget(self.btn_prev)

        self.spin_page = QSpinBox()
        self.spin_page.setMinimum(1)
        self.spin_page.setMaximum(99999)
        self.spin_page.setFixedWidth(60)
        self.spin_page.setToolTip(i18n.tr("页码"))
        lo.addWidget(self.spin_page)

        self.label_total = QLabel("/ 0")
        lo.addWidget(self.label_total)

        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedSize(30, 26)
        self.btn_next.setToolTip(i18n.tr("下一页"))
        lo.addWidget(self.btn_next)

        lo.addSpacing(8)

        self.combo_zoom = QComboBox()
        self.combo_zoom.addItems(["100%", "75%", "125%", "150%", "200%",
                                   i18n.tr("适应宽度"), i18n.tr("适应页面")])
        self.combo_zoom.setCurrentIndex(0)
        self.combo_zoom.setFixedWidth(90)
        lo.addWidget(self.combo_zoom)

        lo.addStretch()

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText(i18n.tr("搜索..."))
        self.input_search.setFixedWidth(160)
        self.input_search.setClearButtonEnabled(True)
        lo.addWidget(self.input_search)

        self.btn_find = QPushButton(i18n.tr("查找"))
        self.btn_find.setFixedHeight(26)
        lo.addWidget(self.btn_find)

        # 信号连接
        self.btn_prev.clicked.connect(self.pagePrev)
        self.btn_next.clicked.connect(self.pageNext)
        self.spin_page.valueChanged.connect(self._on_page_input)
        self.combo_zoom.currentTextChanged.connect(self.zoomChanged)
        self.btn_find.clicked.connect(lambda: self.searchRequested.emit(self.input_search.text()))
        self.input_search.returnPressed.connect(lambda: self.searchRequested.emit(self.input_search.text()))

        self._block_page_signal = False

    def _on_page_input(self, val):
        if not self._block_page_signal:
            self.pageGo.emit(val)

    def set_page_range(self, current: int, total: int):
        self._block_page_signal = True
        self.spin_page.setMaximum(max(1, total))
        self.spin_page.setValue(current)
        self.label_total.setText(f"/ {total}")
        self._block_page_signal = False

    def set_current_page(self, page: int):
        self._block_page_signal = True
        self.spin_page.setValue(page)
        self._block_page_signal = False

    def refresh_i18n(self):
        self.btn_import.setText(i18n.tr("导入书籍"))
        self.btn_prev.setToolTip(i18n.tr("上一页"))
        self.btn_next.setToolTip(i18n.tr("下一页"))
        self.spin_page.setToolTip(i18n.tr("页码"))
        self.input_search.setPlaceholderText(i18n.tr("搜索..."))
        self.btn_find.setText(i18n.tr("查找"))
        cur = self.combo_zoom.currentIndex()
        self.combo_zoom.setItemText(5, i18n.tr("适应宽度"))
        self.combo_zoom.setItemText(6, i18n.tr("适应页面"))


# ── 书单侧栏 ────────────────────────────────────────────────────
class BookSidebar(QWidget):
    bookSelected = Signal(str)       # filepath
    bookmarkJump = Signal(str, int)  # filepath, page

    def __init__(self, books_dir: Path, notes_manager=None, parent=None):
        super().__init__(parent)
        self._books_dir = books_dir
        self._notes = notes_manager
        self._init_ui()
        self.refresh_books()

    def _init_ui(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(4, 4, 4, 4)
        lo.setSpacing(4)

        # 书单
        lbl = QLabel(i18n.tr("教材"))
        lbl.setFont(QFont("sans-serif", 11, QFont.Bold))
        lo.addWidget(lbl)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(i18n.tr("筛选..."))
        self.filter_input.setClearButtonEnabled(True)
        self.filter_input.textChanged.connect(self._filter_books)
        lo.addWidget(self.filter_input)

        self.book_list = QListWidget()
        self.book_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.book_list.customContextMenuRequested.connect(self._book_context_menu)
        self.book_list.itemClicked.connect(self._on_book_clicked)
        lo.addWidget(self.book_list)

        # 书签
        lbl2 = QLabel(i18n.tr("书签"))
        lbl2.setFont(QFont("sans-serif", 11, QFont.Bold))
        lo.addWidget(lbl2)

        self.bm_list = QListWidget()
        self.bm_list.itemClicked.connect(self._on_bookmark_clicked)
        self.bm_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bm_list.customContextMenuRequested.connect(self._bm_context_menu)
        lo.addWidget(self.bm_list)

        self._all_books = []  # [(filepath, name, size_str)]

    def _book_context_menu(self, pos):
        item = self.book_list.currentItem()
        if not item:
            return
        fp = item.data(Qt.UserRole)
        menu = QMenu(self)
        a = menu.addAction(i18n.tr("在系统查看器中打开"))
        a.triggered.connect(lambda: self._open_external(fp))
        menu.addAction(i18n.tr("在阅读器中打开")).triggered.connect(lambda: self.bookSelected.emit(fp))
        menu.exec(self.book_list.mapToGlobal(pos))

    def _bm_context_menu(self, pos):
        item = self.bm_list.currentItem()
        if not item:
            return
        bm_id = item.data(Qt.UserRole)
        if bm_id and self._notes:
            menu = QMenu(self)
            menu.addAction(i18n.tr("删除书签")).triggered.connect(lambda: self._delete_bookmark(bm_id))
            menu.exec(self.bm_list.mapToGlobal(pos))

    def _delete_bookmark(self, bm_id):
        self._notes.delete_bookmark(bm_id)
        self.refresh_bookmarks()

    def _open_external(self, filepath):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))

    def refresh_books(self):
        self._all_books.clear()
        self.book_list.clear()
        if not self._books_dir.exists():
            return
        for fp in sorted(self._books_dir.glob("*.pdf")):
            size_mb = fp.stat().st_size / (1024 * 1024)
            name = fp.stem
            self._all_books.append((str(fp), name, f"{size_mb:.1f} MB"))
        self._filter_books("")

    def _filter_books(self, text):
        self.book_list.clear()
        t = text.lower()
        for fp, name, size_str in self._all_books:
            if t and t not in name.lower():
                continue
            item = QListWidgetItem(f"{name}\n  {size_str}")
            item.setData(Qt.UserRole, fp)
            item.setToolTip(name)
            self.book_list.addItem(item)

    def _on_book_clicked(self, item):
        fp = item.data(Qt.UserRole)
        if fp:
            self.bookSelected.emit(fp)

    def set_current_book(self, filepath: str):
        for i in range(self.book_list.count()):
            if self.book_list.item(i).data(Qt.UserRole) == filepath:
                self.book_list.setCurrentRow(i)
                return

    def refresh_bookmarks(self, subject: str = "general"):
        self.bm_list.clear()
        if not self._notes:
            return
        for bm in self._notes.list_bookmarks(subject):
            text = f"{bm['book_filename']} — p.{bm['book_page']}"
            if bm.get("label"):
                text += f"  [{bm['label']}]"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, bm["id"])
            item.setToolTip(i18n.tr("点击跳转"))
            self.bm_list.addItem(item)

    def _on_bookmark_clicked(self, item):
        # Find bookmark in notes manager
        bm_id = item.data(Qt.UserRole)
        if not self._notes or not bm_id:
            return
        for bm in self._notes.list_bookmarks():
            if bm["id"] == bm_id:
                fp = str(self._books_dir / bm["book_filename"])
                if Path(fp).exists():
                    self.bookmarkJump.emit(fp, bm["book_page"])
                return

    def refresh_i18n(self):
        self.filter_input.setPlaceholderText(i18n.tr("筛选..."))
        # Rebuild label texts
        for i in range(self.layout().count()):
            w = self.layout().itemAt(i).widget()
            if isinstance(w, QLabel):
                if "教" in w.text() or "Textbook" in w.text() or "Manuels" in w.text() or "Lehrbuch" in w.text():
                    w.setText(i18n.tr("教材"))
                elif "书签" in w.text() or "Bookmark" in w.text() or "Lesezeichen" in w.text() or "Signets" in w.text():
                    w.setText(i18n.tr("书签"))


# ── 主阅读器 Widget ─────────────────────────────────────────────
class PDFReaderWidget(QWidget):
    """原生电子书阅读器 — Qt 外壳 + PDF.js 渲染"""

    signal_file_opened = None  # set below after __init__
    signal_page_changed = None
    signal_context_menu = None
    signal_import_requested = None

    def __init__(self, books_dir: Path, http_port: int = 8766, notes_manager=None, parent=None):
        super().__init__(parent)
        self._port = http_port
        self._books_dir = books_dir
        self._notes = notes_manager
        self._bridge = None
        self._current_file = None
        self._current_page = 1
        self._current_total = 0
        self._selected_text = ""
        self._init_ui()

        # 属性别名，兼容旧接口
        self.signal_file_opened = self._bridge.fileOpened
        self.signal_page_changed = self._bridge.pageChanged
        self.signal_context_menu = self._bridge.contextMenu
        self.signal_import_requested = self._bridge.importRequested

        self._connect_bridge()
        i18n.languageChanged.connect(self._refresh_i18n)

    def _init_ui(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        # 工具栏
        self.toolbar = PDFToolbar()
        self.toolbar.btn_import.clicked.connect(self._on_import)
        self.toolbar.pagePrev.connect(self._prev_page)
        self.toolbar.pageNext.connect(self._next_page)
        self.toolbar.pageGo.connect(self._go_page)
        self.toolbar.zoomChanged.connect(self._set_zoom)
        self.toolbar.searchRequested.connect(self._search)
        lo.addWidget(self.toolbar)

        # 分割器 (书单侧栏 | PDF 视图)
        splitter = QSplitter(Qt.Horizontal)

        self.sidebar = BookSidebar(self._books_dir, self._notes)
        self.sidebar.setMinimumWidth(180)
        self.sidebar.setMaximumWidth(320)
        self.sidebar.bookSelected.connect(self.load_book)
        self.sidebar.bookmarkJump.connect(self._jump_bookmark)
        splitter.addWidget(self.sidebar)

        # WebEngineView (仅用于 PDF.js 渲染)
        self._webview = QWebEngineView()
        self._webview.setContextMenuPolicy(Qt.CustomContextMenu)
        self._webview.customContextMenuRequested.connect(self._show_context_menu)
        self._channel = QWebChannel()
        self._bridge = PDFReaderBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._webview.page().setWebChannel(self._channel)

        url = f"http://127.0.0.1:{self._port}/pdfjs/reader.html"
        self._webview.setUrl(QUrl(url))
        self._webview.loadFinished.connect(self._on_page_loaded)

        splitter.addWidget(self._webview)
        splitter.setSizes([200, 1000])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        lo.addWidget(splitter)

        # 状态栏
        self.status_label = QLabel(i18n.tr("PDF 阅读器就绪"))
        self.status_label.setStyleSheet("padding: 2px 6px; color: #888; font-size: 12px;")
        lo.addWidget(self.status_label)

        # 快捷键
        QShortcut(QKeySequence.Copy, self, activated=self._copy)
        QShortcut(QKeySequence.Cut, self, activated=self._cut)
        QShortcut(QKeySequence.Paste, self, activated=self._paste)
        QShortcut(QKeySequence.SelectAll, self, activated=self._select_all)

    # ── 公开 API ────────────────────────────────────────────────
    def refresh_book_list(self, subject: str = "general"):
        self.sidebar.refresh_books()
        self.sidebar.refresh_bookmarks(subject)

    def refresh_i18n(self):
        self._refresh_i18n()

    def _refresh_i18n(self, lang_code=None):
        self.toolbar.refresh_i18n()
        self.sidebar.refresh_i18n()
        cur = self.status_label.text()
        if "就绪" in cur or "Ready" in cur or "bereit" in cur or "prêt" in cur:
            self.status_label.setText(i18n.tr("PDF 阅读器就绪"))
        elif "失败" in cur or "failed" in cur:
            self.status_label.setText(i18n.tr("加载失败"))

    @property
    def webview(self):
        return self._webview

    def load_book(self, filepath: str):
        self._current_file = filepath
        self._current_page = 1
        filename = Path(filepath).name
        encoded = "/books/" + "/".join(
            Path(filepath).name.encode("utf-8").hex("%")
            if isinstance(c, int) and c > 127 else c
            for c in Path(filepath).name
        ) if any(ord(c) > 127 for c in Path(filepath).name) else filename  # noqa
        # 用 URL 编码的文件名
        from urllib.parse import quote
        url = f"http://127.0.0.1:{self._port}/books/{quote(filename)}"
        self._call_js("loadPDF", url, filename)
        self.sidebar.set_current_book(filepath)
        self.status_label.setText(filename)

    def _jump_bookmark(self, filepath: str, page: int):
        self.load_book(filepath)
        QTimer.singleShot(800, lambda: self._go_page(page))

    # ── 页面导航 ────────────────────────────────────────────────
    def _prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._call_js("goToPage", self._current_page)

    def _next_page(self):
        if self._current_page < self._current_total:
            self._current_page += 1
            self._call_js("goToPage", self._current_page)

    def _go_page(self, page: int):
        self._current_page = page
        self._call_js("goToPage", page)

    def _set_zoom(self, mode: str):
        zoom_map = {
            "100%": "1.0", "75%": "0.75", "125%": "1.25",
            "150%": "1.5", "200%": "2.0",
        }
        m = i18n.tr("适应宽度")
        p = i18n.tr("适应页面")
        if mode == m:
            self._call_js("setZoom", "fit-width")
        elif mode == p:
            self._call_js("setZoom", "fit-page")
        elif mode in zoom_map:
            self._call_js("setZoom", zoom_map[mode])

    def _search(self, query: str):
        if query.strip():
            self._call_js("searchPDF", query)

    def _on_page_loaded(self, ok: bool):
        if not ok:
            QTimer.singleShot(800, self._retry_load)
        else:
            self._retry_count = 0

    def _retry_load(self):
        self._retry_count = getattr(self, "_retry_count", 0) + 1
        if self._retry_count <= 5:
            url = f"http://127.0.0.1:{self._port}/pdfjs/reader.html"
            self._webview.setUrl(QUrl(url))

    # ── 右键菜单 ────────────────────────────────────────────────
    def _show_context_menu(self, pos: QPoint):
        self._call_js("getSelectionText", callback=self._on_got_selection)
        self._context_menu_pos = pos

    def _on_got_selection(self, text: str):
        self._selected_text = text.strip() if text else ""
        self._build_context_menu(self._selected_text, self._context_menu_pos)

    def _build_context_menu(self, text: str, pos: QPoint):
        menu = QMenu(self)

        has_text = bool(text)

        a_copy = menu.addAction(i18n.tr("复制\tCtrl+C"))
        a_copy.setEnabled(has_text)
        a_copy.triggered.connect(self._copy)

        a_cut = menu.addAction(i18n.tr("剪切\tCtrl+X"))
        a_cut.setEnabled(has_text)
        a_cut.triggered.connect(self._cut)

        a_paste = menu.addAction(i18n.tr("粘贴\tCtrl+V"))
        a_paste.triggered.connect(self._paste)

        menu.addSeparator()

        a_select = menu.addAction(i18n.tr("全选\tCtrl+A"))
        a_select.triggered.connect(self._select_all)

        if has_text:
            menu.addSeparator()
            # 通知 main.py 显示化学工具菜单
            gpos = self._webview.mapToGlobal(pos)
            self._bridge.contextMenu.emit(text, gpos.x(), gpos.y())
            # 注意: main.py 会创建并显示自己的菜单，我们这里只用基础菜单
            # 如果 main.py 不接管，这里就是完整菜单

        menu.exec(self._webview.mapToGlobal(pos))

    def _copy(self):
        self._call_js("copySelection")
        cb = __import__("PySide6.QtWidgets").QtWidgets.QApplication.clipboard()
        selected = self._selected_text
        if selected:
            cb.setText(selected)
        self.status_label.setText(i18n.tr("已复制"))

    def _cut(self):
        cb = __import__("PySide6.QtWidgets").QtWidgets.QApplication.clipboard()
        if self._selected_text:
            cb.setText(self._selected_text)
        self.status_label.setText(i18n.tr("已剪切"))

    def _paste(self):
        cb = __import__("PySide6.QtWidgets").QtWidgets.QApplication.clipboard()
        pasted = cb.text()
        if pasted:
            self.toolbar.input_search.setText(pasted)
            self.toolbar.input_search.setFocus()

    def _select_all(self):
        self._call_js("selectAll")

    def _on_import(self):
        self._bridge.importRequested.emit()

    # ── JS 桥接 ─────────────────────────────────────────────────
    def _call_js(self, func: str, *args, callback=None):
        js_args = ", ".join(json.dumps(a) for a in args)
        if callback:
            js = f"(typeof {func} === 'function') ? {func}({js_args}) : null"
            self._webview.page().runJavaScript(js, callback)
        else:
            js = f"if (typeof {func} === 'function') {{ {func}({js_args}); }}"
            self._webview.page().runJavaScript(js)

    # ── 页面更新回调(由 JS 侧触发) ──────────────────────────────
    def _on_file_opened(self, filename: str, total: int):
        self._current_total = total
        self._current_page = 1
        self.toolbar.set_page_range(1, total)
        self.status_label.setText(filename)
        self.sidebar.refresh_bookmarks()

    def _on_page_changed(self, page: int, total: int):
        self._current_page = page
        self._current_total = total
        self.toolbar.set_current_page(page)
        self.toolbar.set_page_range(page, total)

    # 重新连接 bridge 信号(在 _bridge 创建后)
    def _connect_bridge(self):
        self._bridge.fileOpened.connect(self._on_file_opened)
        self._bridge.pageChanged.connect(self._on_page_changed)
