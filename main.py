"""化学学习套件 — 应用入口"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QInputDialog, QMessageBox,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QLineEdit,
    QDialog, QTreeWidget, QTreeWidgetItem, QPushButton, QStackedWidget,
    QSplitter, QMenu, QSizePolicy,
)
from PySide6.QtCore import Qt, QObject, QPoint, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QFont

from core.i18n import i18n, LANGUAGES
from core.notes_manager import NotesManager
from widgets.sidebar import Sidebar
from widgets.chem_editor import ChemEditorWidget
from widgets.mol3d_viewer import Mol3DViewerWidget
from widgets.katex_renderer import KaTeXEditorWidget
from widgets.pdf_reader import PDFReaderWidget
from widgets.periodic_table import PeriodicTableWidget
from widgets.note_editor import NoteEditorWidget
from widgets.calculator_panel import CalculatorPanel
import widgets.tools_stubs as stubs


# ── 可分离工具窗口 ──────────────────────────────────────────────
class DetachableToolWindow(QMainWindow):
    """工具面板的独立浮动窗口"""
    dockRequested = Signal(str)

    def __init__(self, tool_key, widget, title, parent=None):
        super().__init__(parent)
        self._tool_key = tool_key
        self._widget = widget
        self.setWindowTitle(title)
        self.resize(750, 580)

        mb = self.menuBar()
        self._dock_action = mb.addAction(i18n.tr("Dock 回主窗口"))
        self._dock_action.triggered.connect(self._request_dock)

        self.setCentralWidget(widget)
        widget.show()

    def _request_dock(self):
        self.dockRequested.emit(self._tool_key)

    def closeEvent(self, event):
        self._request_dock()
        event.ignore()

    def take_widget(self):
        """取出内部 widget (由主窗口调用)"""
        w = self.takeCentralWidget()
        w.setParent(None)
        return w


# ── 命令注册表 ──────────────────────────────────────────────────
def _build_command_registry(window):
    return {
        "打开结构文件": (window._import_file, "Ctrl+O", "文件"),
        "打开教材 PDF": (window._open_pdf, "Ctrl+P", "文件"),
        "从 PubChem 导入": (window._import_pubchem, "Ctrl+Shift+D", "文件"),
        "从 PDB 导入": (window._import_pdb, "Ctrl+Shift+P", "文件"),
        "退出应用": (window.close, "Ctrl+Q", "文件"),
        "2D 结构 → 3D 推送": (window._push_2d_to_3d, "Ctrl+D", "视图"),
        "获取当前 SMILES": (window._get_smiles_shortcut, "Ctrl+G", "视图"),
        "切换笔记面板": (window._toggle_notes, "Ctrl+B", "视图"),
        "全屏切换": (window._toggle_fullscreen, "F11", "视图"),
        "聚焦 SMILES 输入": (window._focus_smiles_input, "Ctrl+Shift+Space", "视图"),
        "分离当前面板": (window._detach_current_tool, "", "视图"),
        "Dock 回主窗口": (window._dock_current_tool, "", "视图"),
        "切换到 有机化学": (lambda: window.subject_tabs.setCurrentIndex(0), "Ctrl+1", "导航"),
        "切换到 无机化学": (lambda: window.subject_tabs.setCurrentIndex(1), "Ctrl+2", "导航"),
        "切换到 物理化学": (lambda: window.subject_tabs.setCurrentIndex(2), "Ctrl+3", "导航"),
        "切换到 结构化学": (lambda: window.subject_tabs.setCurrentIndex(3), "Ctrl+4", "导航"),
        "切换到 原理": (lambda: window.subject_tabs.setCurrentIndex(4), "Ctrl+5", "导航"),
        "切换到 全部工具": (lambda: window.subject_tabs.setCurrentIndex(5), "Ctrl+6", "导航"),
        "化学计算器": (window._show_tool_calculator, "", "工具"),
        "波谱模拟器": (window._show_tool_spectroscopy, "", "工具"),
        "MO 能级图": (window._show_tool_mo, "", "工具"),
        "热力学循环搭建器": (window._show_tool_thermo, "", "工具"),
        "点群分析器": (window._show_tool_symmetry, "", "工具"),
        "晶体结构浏览器": (window._show_tool_crystal, "", "工具"),
        "反应机理动画": (window._show_tool_mechanism, "", "工具"),
        "IUPAC 命名训练器": (window._show_tool_naming, "", "工具"),
        "相图分析器": (window._show_tool_phase, "", "工具"),
        "酸碱滴定模拟器": (window._show_tool_titration, "", "工具"),
        "量子化学可视化": (window._show_tool_quantum, "", "工具"),
        "光谱参考表": (window._show_tool_spectral, "", "工具"),
        "使用说明": (window._show_usage_guide, "", "帮助"),
        "关于化学学习套件": (window._show_about, "", "帮助"),
    }


TOOL_TITLES = {
    "mol": "2D 结构编辑器",
    "3d":  "3D 分子查看器",
    "fx":  "公式编辑器",
    "pt":  "周期表",
    "tl":  "化学工具集",
    "nt":  "笔记",
}


class ChemistrySuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_dir = Path(__file__).resolve().parent
        self.setWindowTitle("化学学习套件")
        self.resize(1400, 950)
        self.setAcceptDrops(True)

        self._tool_cache = {}
        self._active_tool_key = None
        self._detached_tools = {}   # key → DetachableToolWindow
        self._pdf_selected_text = ""
        self._tool_indices = {}

        self._build_menus()
        self._load_ui()
        self._build_sidebar_and_content()
        self._setup_shortcuts()
        self._connect_pdf_context_menu()
        self._init_status("就绪 — Ctrl+Shift+P 命令面板 | 左侧工具栏 | 面板可分离")

        i18n.languageChanged.connect(self._update_ui_texts)

    # ── 菜单栏 ─────────────────────────────────────────────────
    def _build_menus(self):
        mb = self.menuBar()
        self._menu_refs = {}  # store menu objects for i18n re-label
        self._menu_action_texts = {}  # action → original Chinese text

        m = mb.addMenu("文件(&F)")
        self._file_menu = m
        self._add_menu_action(m, "打开结构文件...\tCtrl+O", self._import_file)
        self._add_menu_action(m, "打开教材 PDF...\tCtrl+P", self._open_pdf)
        m.addSeparator()
        self._add_menu_action(m, "从 PubChem 导入...\tCtrl+Shift+D", self._import_pubchem)
        self._add_menu_action(m, "从 PDB 导入...\tCtrl+Shift+P", self._import_pdb)
        m.addSeparator()
        self._add_menu_action(m, "退出\tCtrl+Q", self.close)

        m = mb.addMenu("编辑(&E)")
        self._edit_menu = m
        self._add_menu_action(m, "获取 SMILES\tCtrl+G", self._get_smiles_shortcut)
        self._add_menu_action(m, "2D → 3D 推送\tCtrl+D", self._push_2d_to_3d)

        m = mb.addMenu("视图(&V)")
        self._view_menu = m
        self._add_menu_action(m, "分离当前面板", self._detach_current_tool)
        self._add_menu_action(m, "Dock 回主窗口", self._dock_current_tool)
        m.addSeparator()
        self._add_menu_action(m, "切换笔记面板\tCtrl+B", self._toggle_notes)
        self._add_menu_action(m, "全屏\tF11", self._toggle_fullscreen)

        m = mb.addMenu("导航(&N)")
        self._nav_menu = m
        subjects = ["有机化学", "无机化学", "物理化学", "结构化学", "原理", "全部工具"]
        for i, s in enumerate(subjects):
            idx = i
            a = m.addAction(f"{s}\tCtrl+{i + 1}")
            a.triggered.connect(lambda checked, i=idx: self.subject_tabs.setCurrentIndex(i))
            self._menu_action_texts[a] = s

        m = mb.addMenu("工具(&T)")
        self._tools_menu = m
        for name, handler in [
            ("化学计算器", self._show_tool_calculator),
            ("波谱模拟器", self._show_tool_spectroscopy),
            ("点群分析器", self._show_tool_symmetry),
            ("MO 能级图", self._show_tool_mo),
            ("热力学循环搭建器", self._show_tool_thermo),
            ("晶体结构浏览器", self._show_tool_crystal),
            ("反应机理动画", self._show_tool_mechanism),
            ("IUPAC 命名训练器", self._show_tool_naming),
            ("相图分析器", self._show_tool_phase),
            ("酸碱滴定模拟器", self._show_tool_titration),
            ("量子化学可视化", self._show_tool_quantum),
            ("光谱参考表", self._show_tool_spectral),
        ]:
            self._add_menu_action(m, name, handler)

        m = mb.addMenu("帮助(&H)")
        self._help_menu = m
        self._add_menu_action(m, "使用说明", self._show_usage_guide)
        self._add_menu_action(m, "关于...", self._show_about)

        # 语言菜单
        self._lang_menu = mb.addMenu("语言(&L)")
        self._lang_actions = {}
        for code, name in LANGUAGES.items():
            action = self._lang_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(code == i18n.current_language)
            action.triggered.connect(lambda checked, c=code: i18n.set_language(c))
            self._lang_actions[code] = action

    def _add_menu_action(self, menu, text, handler):
        """添加菜单项并记录原始中文文本"""
        action = menu.addAction(text)
        action.triggered.connect(handler)
        self._menu_action_texts[action] = text.split("\t")[0]
        return action

    # ── UI 加载 ────────────────────────────────────────────────
    def _load_ui(self):
        loader = QUiLoader()
        ui_file = self.base_dir / "ui" / "main_window.ui"
        central = loader.load(str(ui_file))
        self.setCentralWidget(central)

        find = central.findChild
        self.subject_tabs = find(QObject, "subjectTabWidget")
        self.main_area = find(QObject, "mainArea")

    # ── 左侧工具栏 + 内容区 ───────────────────────────────────
    def _build_sidebar_and_content(self):
        if not self.main_area:
            return

        lo = QHBoxLayout(self.main_area)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        # 左侧工具栏
        self._sidebar = Sidebar()
        self._sidebar.toolToggled.connect(self._on_tool_toggled)
        lo.addWidget(self._sidebar)

        # 内容分屏区
        self._content_splitter = QSplitter(Qt.Horizontal)
        self._content_splitter.setChildrenCollapsible(False)

        # 工具面板容器 (带标题栏 + QStackedWidget)
        self._tool_container = QWidget()
        tc_lo = QVBoxLayout(self._tool_container)
        tc_lo.setContentsMargins(0, 0, 0, 0)
        tc_lo.setSpacing(0)

        # 标题栏
        self._tool_header = QWidget()
        self._tool_header.setFixedHeight(28)
        self._tool_header.setStyleSheet(
            "background: #3c3c3c; border-bottom: 1px solid #555;"
        )
        hdr_lo = QHBoxLayout(self._tool_header)
        hdr_lo.setContentsMargins(8, 2, 4, 2)
        hdr_lo.setSpacing(4)

        self._tool_title_label = QLabel("")
        self._tool_title_label.setStyleSheet("color: #ddd; font-size: 12px; border: none;")
        hdr_lo.addWidget(self._tool_title_label)
        hdr_lo.addStretch()

        detach_btn = QPushButton("↗")
        detach_btn.setFixedSize(22, 22)
        detach_btn.setToolTip("分离为独立窗口")
        detach_btn.setStyleSheet(
            "QPushButton { border: 1px solid #555; background: #4a4a4a; color: #ccc; "
            "font-size: 13px; border-radius: 2px; }"
            "QPushButton:hover { background: #666; color: #fff; }"
        )
        detach_btn.clicked.connect(self._detach_current_tool)
        hdr_lo.addWidget(detach_btn)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(22, 22)
        close_btn.setToolTip("关闭面板")
        close_btn.setStyleSheet(
            "QPushButton { border: 1px solid #555; background: #4a4a4a; color: #ccc; "
            "font-size: 14px; border-radius: 2px; }"
            "QPushButton:hover { background: #c44; color: #fff; }"
        )
        close_btn.clicked.connect(self._close_tool)
        hdr_lo.addWidget(close_btn)

        tc_lo.addWidget(self._tool_header)

        # 工具栈
        self._tool_stack = QStackedWidget()
        self._tool_stack.setMinimumWidth(200)
        tc_lo.addWidget(self._tool_stack)

        self._tool_container.hide()

        # PDF 阅读器 (常驻)
        self.pdf_reader = PDFReaderWidget(http_port=8766)

        self._content_splitter.addWidget(self._tool_container)
        self._content_splitter.addWidget(self.pdf_reader)
        self._content_splitter.setSizes([0, 1400])
        self._content_splitter.setStretchFactor(0, 4)
        self._content_splitter.setStretchFactor(1, 6)

        lo.addWidget(self._content_splitter)

    # ── 工具面板懒加载 ────────────────────────────────────────
    def _on_tool_toggled(self, key, checked):
        if key in self._detached_tools:
            # 已分离的工具: 点击始终聚焦浮窗 (不 dock)
            self._detached_tools[key].raise_()
            self._detached_tools[key].activateWindow()
            self._sidebar.set_checked(key, True)  # 保持选中态
            self._init_status(i18n.tr("已聚焦: ") + self._tr_tool_title(key))
            return

        if checked:
            self._open_tool(key)
        else:
            self._close_tool()

    def _open_tool(self, key):
        if self._active_tool_key and self._active_tool_key != key:
            self._close_tool()

        # 懒加载
        if key not in self._tool_cache:
            widget = self._make_tool_widget(key)
            if widget:
                self._tool_cache[key] = widget
                self._tool_stack.addWidget(widget)

        widget = self._tool_cache.get(key)
        if widget:
            self._tool_stack.setCurrentWidget(widget)
            self._tool_title_label.setText(self._tr_tool_title(key))
            self._tool_container.show()
            self._sidebar.set_checked(key, True)
            self._active_tool_key = key

            # 给工具面板合理宽度
            sizes = self._content_splitter.sizes()
            if len(sizes) >= 2 and sizes[0] < 100:
                total = sum(sizes)
                self._content_splitter.setSizes([total * 4 // 10, total * 6 // 10])

    def _close_tool(self):
        self._tool_container.hide()
        self._tool_title_label.setText("")
        self._sidebar.uncheck_all()
        self._active_tool_key = None

    def _make_tool_widget(self, key):
        wd = str(self.base_dir / "web")
        port = 8766

        if key == "mol":
            widget = ChemEditorWidget(web_dir=wd, http_port=port)
            self.chem_editor = widget
            widget.btn_to_3d.clicked.connect(self._push_2d_to_3d)
            return widget
        elif key == "3d":
            self.mol_viewer = Mol3DViewerWidget(http_port=port)
            return self.mol_viewer
        elif key == "fx":
            self.formula_editor = KaTeXEditorWidget(http_port=port)
            return self.formula_editor
        elif key == "pt":
            self.periodic_table = PeriodicTableWidget()
            return self.periodic_table
        elif key == "tl":
            return self._make_tools_panel()
        elif key == "nt":
            if not hasattr(self, "notes_manager"):
                self.notes_manager = NotesManager()
            self.note_editor = NoteEditorWidget(self.notes_manager)
            return self.note_editor
        return None

    def _make_tools_panel(self):
        from PySide6.QtWidgets import QComboBox

        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(4, 4, 4, 4)
        lo.setSpacing(4)

        self._tools_combo = QComboBox()
        lo.addWidget(self._tools_combo)

        stack = QStackedWidget()
        panels = [
            ("化学计算器", CalculatorPanel()),
            ("波谱模拟器", stubs.create_spectroscopy_panel()),
            ("MO 能级图", stubs.create_mo_panel()),
            ("热力学循环", stubs.create_thermo_cycle_panel()),
            ("点群分析器", stubs.create_symmetry_panel()),
            ("晶体浏览器", stubs.create_crystal_panel()),
            ("反应机理动画", stubs.create_mechanism_panel()),
            ("IUPAC 命名训练", stubs.create_naming_panel()),
            ("相图分析器", stubs.create_phase_diagram_panel()),
            ("酸碱滴定", stubs.create_titration_panel()),
            ("量子可视化", stubs.create_quantum_panel()),
            ("光谱参考表", stubs.create_spectral_ref_panel()),
        ]
        for i, (name, panel) in enumerate(panels):
            stack.addWidget(panel)
            self._tools_combo.addItem(i18n.tr(name))
            self._tool_indices[name] = i

        self._tools_combo.currentIndexChanged.connect(stack.setCurrentIndex)
        lo.addWidget(stack)
        return w

    # ── 分离 / Dock ───────────────────────────────────────────
    def _detach_current_tool(self):
        key = self._active_tool_key
        if not key or key in self._detached_tools:
            return

        widget = self._tool_stack.currentWidget()
        if not widget:
            return

        title = self._tr_tool_title(key)
        self._tool_stack.removeWidget(widget)

        win = DetachableToolWindow(key, widget, title)
        win.dockRequested.connect(self._dock_tool)
        win.show()

        self._detached_tools[key] = win
        self._tool_container.hide()
        self._active_tool_key = None
        self._init_status(i18n.tr("已分离: ") + title)

    def _dock_tool(self, tool_key):
        win = self._detached_tools.pop(tool_key, None)
        if not win:
            return

        widget = win.take_widget()
        if widget:
            self._tool_stack.addWidget(widget)
            self._tool_stack.setCurrentWidget(widget)
            self._tool_title_label.setText(self._tr_tool_title(tool_key))
            self._tool_container.show()
            self._sidebar.set_checked(tool_key, True)
            self._active_tool_key = tool_key

            sizes = self._content_splitter.sizes()
            if len(sizes) >= 2 and sizes[0] < 100:
                total = sum(sizes)
                self._content_splitter.setSizes([total * 4 // 10, total * 6 // 10])

        win.hide()
        win.deleteLater()
        self._init_status(i18n.tr("Dock 完成"))

    def _dock_current_tool(self):
        """Dock 最近分离的工具"""
        if self._detached_tools:
            key = next(iter(self._detached_tools))
            self._dock_tool(key)
        else:
            self._init_status(i18n.tr("没有已分离的面板"))

    # ── PDF 右键菜单 ─────────────────────────────────────────
    def _connect_pdf_context_menu(self):
        if hasattr(self, "pdf_reader") and self.pdf_reader:
            self.pdf_reader.signal_context_menu.connect(self._on_pdf_context_menu)

    def _on_pdf_context_menu(self, text, x, y):
        self._pdf_selected_text = text.strip()
        if not self._pdf_selected_text:
            return

        menu = QMenu(self)

        menu.addAction(i18n.tr("在结构编辑器中打开"), self._ctx_open_structure)
        menu.addAction(i18n.tr("查看 3D 结构"), self._ctx_view_3d)
        menu.addAction(i18n.tr("查询原子量/元素"), self._ctx_query_element)
        menu.addSeparator()
        menu.addAction(i18n.tr("从 PubChem 搜索"), self._ctx_pubchem_search)
        menu.addAction(i18n.tr("添加到笔记"), self._ctx_add_to_notes)

        more = menu.addMenu(i18n.tr("更多"))
        more.addAction(i18n.tr("波谱模拟"), self._ctx_spectroscopy)
        more.addAction(i18n.tr("MO 能级图"), self._ctx_mo)
        more.addAction(i18n.tr("IUPAC 命名"), self._ctx_naming)
        more.addAction(i18n.tr("热力学数据"), self._ctx_thermo)
        more.addAction(i18n.tr("晶体结构查询"), self._ctx_crystal)

        gpos = self.pdf_reader.webview.mapToGlobal(QPoint(x, y))
        menu.exec(gpos)

    def _ctx_open_structure(self):
        self._sidebar.set_checked("mol", True)
        self._open_tool("mol")
        self._search_structure(self._pdf_selected_text)

    def _ctx_view_3d(self):
        self._sidebar.set_checked("3d", True)
        self._open_tool("3d")
        self._search_and_view_3d(self._pdf_selected_text)

    def _ctx_query_element(self):
        self._sidebar.set_checked("pt", True)
        self._open_tool("pt")
        self._init_status(f"{i18n.tr('查询原子量/元素')}: {self._pdf_selected_text}")

    def _ctx_pubchem_search(self):
        self._search_and_load_pubchem(self._pdf_selected_text)

    def _ctx_add_to_notes(self):
        text = self._pdf_selected_text
        if not hasattr(self, "notes_manager"):
            self.notes_manager = NotesManager()
        self.notes_manager.add_note(
            subject=i18n.tr("通用"),
            title=f"{i18n.tr('来自电子书: ')}{text[:30]}",
            content=text,
        )
        self._init_status(f"{i18n.tr('已添加到笔记: ')}{text[:30]}...")

    def _ctx_spectroscopy(self):
        self._sidebar.set_checked("tl", True)
        self._open_tool("tl")
    def _ctx_mo(self):
        self._sidebar.set_checked("tl", True)
        self._open_tool("tl")
    def _ctx_naming(self):
        self._sidebar.set_checked("tl", True)
        self._open_tool("tl")
    def _ctx_thermo(self):
        self._sidebar.set_checked("tl", True)
        self._open_tool("tl")
    def _ctx_crystal(self):
        self._sidebar.set_checked("tl", True)
        self._open_tool("tl")

    def _search_structure(self, text):
        if not hasattr(self, "chem_editor"):
            return
        try:
            from core.importers import pubchem_name_to_smiles
            smiles = pubchem_name_to_smiles(text)
            self.chem_editor.set_smiles(smiles)
            self._init_status(i18n.tr("PubChem: ") + f"{text} → {smiles[:50]}")
        except Exception:
            self.chem_editor.smiles_input.setText(text)
            self._init_status(i18n.tr("已填入输入栏: ") + f"{text}" + i18n.tr("，请手动确认"))

    def _search_and_view_3d(self, text):
        if not hasattr(self, "mol_viewer"):
            return
        try:
            from core.importers import pubchem_name_to_smiles
            smiles = pubchem_name_to_smiles(text)
            self.mol_viewer.load_smiles(smiles)
            self._init_status(f"3D: {text} → {smiles[:50]}")
        except Exception:
            self._init_status(i18n.tr("3D 加载失败: ") + text)

    def _search_and_load_pubchem(self, text):
        try:
            from core.importers import pubchem_name_to_smiles, pubchem_cid_to_smiles
            smiles = pubchem_cid_to_smiles(int(text)) if text.isdigit() else pubchem_name_to_smiles(text)
            self._sidebar.set_checked("mol", True)
            self._open_tool("mol")
            if hasattr(self, "chem_editor"):
                self.chem_editor.set_smiles(smiles)
            if hasattr(self, "mol_viewer"):
                self.mol_viewer.load_smiles(smiles)
            self._init_status(i18n.tr("PubChem: ") + f"{text} → {smiles[:50]}")
        except Exception as e:
            QMessageBox.warning(self, i18n.tr("PubChem 搜索失败"), str(e))

    # ── 快捷键 ────────────────────────────────────────────────
    def _setup_shortcuts(self):
        bindings = [
            ("Ctrl+O", self._import_file),
            ("Ctrl+P", self._open_pdf),
            ("Ctrl+Shift+P", self._show_command_palette),
            ("Ctrl+Shift+D", self._import_pdb),
            ("Ctrl+D", self._push_2d_to_3d),
            ("Ctrl+G", self._get_smiles_shortcut),
            ("Ctrl+B", self._toggle_notes),
            ("Ctrl+Q", self.close),
            ("F11", self._toggle_fullscreen),
            ("Ctrl+Shift+Space", self._focus_smiles_input),
        ]
        for key, handler in bindings:
            QShortcut(QKeySequence(key), self, handler)

        for i in range(6):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self,
                      lambda idx=i: self.subject_tabs.setCurrentIndex(idx) if self.subject_tabs else None)

        if self.subject_tabs:
            self.subject_tabs.currentChanged.connect(self._on_subject_changed)

    # ── 命令面板 ──────────────────────────────────────────────
    def _show_command_palette(self):
        dlg = CommandPalette(self)
        if dlg.exec() == QDialog.Accepted and dlg.selected_command:
            name = dlg.selected_command
            registry = _build_command_registry(self)
            if name in registry:
                handler, _, _ = registry[name]
                handler()

    # ── 操作实现 ──────────────────────────────────────────────
    def _push_2d_to_3d(self):
        if self._ensure_tool("3d"):
            if hasattr(self, "chem_editor"):
                smiles = self.chem_editor.get_smiles()
                if smiles and hasattr(self, "mol_viewer"):
                    self.mol_viewer.load_smiles(smiles)
                    self._init_status(i18n.tr("2D → 3D: ") + smiles[:50])

    def _get_smiles_shortcut(self):
        if hasattr(self, "chem_editor"):
            self.chem_editor._get_smiles()
            self._init_status(i18n.tr("已获取 SMILES"))

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _focus_smiles_input(self):
        self._ensure_tool("mol")
        if hasattr(self, "chem_editor"):
            self.chem_editor.smiles_input.setFocus()
            self.chem_editor.smiles_input.selectAll()

    def _toggle_notes(self):
        if self._active_tool_key == "nt":
            self._close_tool()
        else:
            self._sidebar.set_checked("nt", True)
            self._open_tool("nt")

    def _ensure_tool(self, key):
        """确保某工具面板已打开 (不重复打开)"""
        if key in self._detached_tools:
            self._detached_tools[key].raise_()
            return True
        if self._active_tool_key != key:
            self._sidebar.set_checked(key, True)
            self._open_tool(key)
        return True

    # ── 工具快捷切换 ──────────────────────────────────────────
    def _show_tool_calculator(self):
        self._ensure_tool("tl")
    def _show_tool_spectroscopy(self):
        self._ensure_tool("tl")
    def _show_tool_mo(self):
        self._ensure_tool("tl")
    def _show_tool_thermo(self):
        self._ensure_tool("tl")
    def _show_tool_symmetry(self):
        self._ensure_tool("tl")
    def _show_tool_crystal(self):
        self._ensure_tool("tl")
    def _show_tool_mechanism(self):
        self._ensure_tool("tl")
    def _show_tool_naming(self):
        self._ensure_tool("tl")
    def _show_tool_phase(self):
        self._ensure_tool("tl")
    def _show_tool_titration(self):
        self._ensure_tool("tl")
    def _show_tool_quantum(self):
        self._ensure_tool("tl")
    def _show_tool_spectral(self):
        self._ensure_tool("tl")

    # ── 导入 ──────────────────────────────────────────────────
    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("打开结构文件"), "",
            i18n.tr("化学结构文件 (*.mol *.sdf *.pdb *.cif *.xyz *.smi *.smiles);;所有文件 (*)")
        )
        if not path:
            return
        from core.importers import import_structure_file
        result = import_structure_file(path)
        if result.get("error"):
            QMessageBox.warning(self, i18n.tr("导入错误"), result["error"])
            return
        fmt = result.get("format")
        if fmt == "smiles":
            self._ensure_tool("mol")
            self.chem_editor.set_smiles(result["smiles"])
            self._init_status(i18n.tr("已加载 SMILES: ") + result["smiles"][:60])
        elif fmt == "mol":
            self._ensure_tool("mol")
            self.chem_editor.set_smiles(result["smiles"])
            self._init_status(i18n.tr("已加载 Molfile"))
        elif fmt == "pdb":
            self._ensure_tool("3d")
            self.mol_viewer.load_pdb(result["pdb_data"])
            self._init_status(i18n.tr("已加载 PDB"))
        elif fmt in ("cif", "xyz"):
            self._init_status(i18n.tr("已加载: ") + fmt.upper())

    def _open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("打开教材 PDF"), str(self.base_dir / "books"),
            i18n.tr("PDF 文件 (*.pdf);;所有文件 (*)")
        )
        if not path:
            return
        import shutil
        dest = self.base_dir / "books" / Path(path).name
        if not dest.exists():
            shutil.copy2(path, dest)
        self._init_status(i18n.tr("已添加教材: ") + Path(path).name)
        self.pdf_reader.webview.page().runJavaScript("listBooks();")

    def _import_pubchem(self):
        name, ok = QInputDialog.getText(
            self, i18n.tr("从 PubChem 导入..."),
            i18n.tr("输入化合物名称(中/英文)、SMILES、InChI 或 PubChem CID:")
        )
        if not ok or not name.strip():
            return
        from core.importers import pubchem_name_to_smiles, pubchem_cid_to_smiles
        try:
            name = name.strip()
            smiles = pubchem_cid_to_smiles(int(name)) if name.isdigit() else pubchem_name_to_smiles(name)
            self._ensure_tool("mol")
            self.chem_editor.set_smiles(smiles)
            self._ensure_tool("3d")
            self.mol_viewer.load_smiles(smiles)
            self._init_status(i18n.tr("PubChem: ") + f"{name} → {smiles[:50]}")
        except Exception as e:
            QMessageBox.warning(self, i18n.tr("PubChem 导入失败"), str(e))

    def _import_pdb(self):
        pdb_id, ok = QInputDialog.getText(
            self, i18n.tr("从 PDB 导入..."),
            i18n.tr("输入 PDB ID (4位字符，如 1MOL、4HHB):")
        )
        if not ok or not pdb_id.strip():
            return
        from core.importers import pdb_download
        try:
            pdb_data = pdb_download(pdb_id.strip())
            self._ensure_tool("3d")
            self.mol_viewer.load_pdb(pdb_data)
            self._init_status(i18n.tr("PDB: ") + f"{pdb_id.strip().upper()} " + i18n.tr("已加载"))
        except Exception as e:
            QMessageBox.warning(self, i18n.tr("PDB 导入失败"), str(e))

    # ── 拖放 ──────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        from core.importers import import_structure_file
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path:
                continue
            ext = path.lower()
            if ext.endswith((".mol", ".sdf", ".pdb", ".cif", ".xyz", ".smi", ".smiles")):
                result = import_structure_file(path)
                if result.get("smiles"):
                    self._ensure_tool("mol")
                    self.chem_editor.set_smiles(result["smiles"])
                self._init_status(i18n.tr("拖放加载: ") + Path(path).name)
            elif ext.endswith(".pdf"):
                import shutil
                dest = self.base_dir / "books" / Path(path).name
                if not dest.exists():
                    shutil.copy2(path, dest)
                self._init_status(i18n.tr("拖放添加教材: ") + Path(path).name)
                self.pdf_reader.webview.page().runJavaScript("listBooks();")

    # ── 学科切换 ──────────────────────────────────────────────
    def _on_subject_changed(self, index: int):
        tab_name = self.subject_tabs.tabText(index) if self.subject_tabs else ""
        self._init_status(i18n.tr("当前学科: ") + tab_name)

    # ── 对话框 ────────────────────────────────────────────────
    def _show_about(self):
        QMessageBox.about(
            self, i18n.tr("关于 化学学习套件"),
            i18n.tr("化学学习套件") + " v0.6\n\n"
            + i18n.tr("化学学习套件") + "\n\n"
            "PySide6 + RDKit + Ketcher + 3Dmol.js + KaTeX + PDF.js"
        )

    def _show_usage_guide(self):
        from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout, QPushButton, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("使用说明")
        dlg.resize(750, 600)
        lo = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(USAGE_GUIDE_HTML)
        lo.addWidget(browser)
        btn = QPushButton("关闭")
        btn.clicked.connect(dlg.accept)
        btn_lo = QHBoxLayout()
        btn_lo.addStretch()
        btn_lo.addWidget(btn)
        lo.addLayout(btn_lo)
        dlg.exec()

    def _init_status(self, message: str):
        self.statusBar().showMessage(message)

    def _tr_tool_title(self, key: str) -> str:
        """翻译工具标题"""
        return i18n.tr(TOOL_TITLES.get(key, key))

    def _update_ui_texts(self, lang_code: str):
        """语言切换时刷新所有 UI 文本"""
        # 窗口标题
        self.setWindowTitle(i18n.tr("化学学习套件"))

        # 菜单标题
        menu_titles = {
            self._file_menu: "文件(&F)",
            self._edit_menu: "编辑(&E)",
            self._view_menu: "视图(&V)",
            self._nav_menu: "导航(&N)",
            self._tools_menu: "工具(&T)",
            self._help_menu: "帮助(&H)",
        }
        for menu, title in menu_titles.items():
            menu.setTitle(i18n.tr(title))

        self._lang_menu.setTitle(i18n.tr("语言(&L)"))

        # 菜单动作文本
        for action, chinese_text in self._menu_action_texts.items():
            cur = action.text()
            shortcut = ""
            if "\t" in cur:
                shortcut = "\t" + cur.split("\t", 1)[1]
            action.setText(i18n.tr(chinese_text) + shortcut)

        # 语言菜单选中态
        for code, action in self._lang_actions.items():
            action.setChecked(code == lang_code)

        # 学科标签
        if self.subject_tabs:
            subjects = ["有机化学", "无机化学", "物理化学", "结构化学", "原理", "全部工具"]
            for i, s in enumerate(subjects):
                if i < self.subject_tabs.count():
                    self.subject_tabs.setTabText(i, i18n.tr(s))

        # DetachableToolWindow 菜单
        for win in self._detached_tools.values():
            mb = win.menuBar()
            if mb:
                for a in mb.actions():
                    a.setText(i18n.tr("Dock 回主窗口"))

        # 工具标题栏
        if self._active_tool_key and self._active_tool_key in TOOL_TITLES:
            self._tool_title_label.setText(i18n.tr(TOOL_TITLES[self._active_tool_key]))

        # 按钮 tooltips
        for child in self._tool_header.findChildren(QPushButton):
            if child.text() == "↗":
                child.setToolTip(i18n.tr("分离为独立窗口"))
            elif child.text() == "×":
                child.setToolTip(i18n.tr("关闭面板"))

        # 工具集下拉框
        if hasattr(self, "_tools_combo"):
            tool_names = list(self._tool_indices.keys())
            for i, name in enumerate(tool_names):
                if i < self._tools_combo.count():
                    self._tools_combo.setItemText(i, i18n.tr(name))

        # 状态栏
        self.statusBar().showMessage(i18n.tr("就绪 — Ctrl+Shift+P 命令面板 | 左侧工具栏 | 面板可分离"))


# ── 命令面板 ────────────────────────────────────────────────────
class CommandPalette(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("命令面板"))
        self.setFixedSize(520, 380)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.selected_command = None
        self._registry = _build_command_registry(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(i18n.tr("搜索命令... (如: 3D, PubChem, 全屏, 分离)"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFont(QFont(self.search_input.font().family(), 13))
        self.search_input.textChanged.connect(self._filter)
        layout.addWidget(self.search_input)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([i18n.tr("命令"), i18n.tr("快捷键"), i18n.tr("分类")])
        self.tree.setColumnWidth(0, 240)
        self.tree.setColumnWidth(1, 110)
        self.tree.setColumnWidth(2, 90)
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._accept)
        self.tree.setFont(QFont(self.tree.font().family(), 11))
        layout.addWidget(self.tree)

        hint = QLabel(i18n.tr("↑↓ 选择  Enter 执行  Esc 关闭  输入关键词搜索"))
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        self._filter("")
        self.search_input.setFocus()

    def _filter(self, text):
        self.tree.clear()
        categories = {}
        lower = text.lower().split()
        for name, (handler, shortcut, category) in self._registry.items():
            match = all(word in name.lower() for word in lower) if lower else True
            if not match:
                continue
            tr_category = i18n.tr(category)
            if tr_category not in categories:
                categories[tr_category] = QTreeWidgetItem(self.tree, [tr_category, "", ""])
                categories[tr_category].setExpanded(True)
                font = categories[tr_category].font(0)
                font.setBold(True)
                categories[tr_category].setFont(0, font)
            item = QTreeWidgetItem(categories[tr_category], [i18n.tr(name), shortcut, ""])
            item.setData(0, Qt.UserRole, name)

        if self.tree.topLevelItemCount() > 0:
            first_cat = self.tree.topLevelItem(0)
            if first_cat.childCount() > 0:
                self.tree.setCurrentItem(first_cat.child(0))

    def _accept(self):
        item = self.tree.currentItem()
        if item and item.data(0, Qt.UserRole):
            self.selected_command = item.data(0, Qt.UserRole)
            self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._accept()
        elif event.key() == Qt.Key_Down:
            current = self.tree.currentItem()
            if current:
                below = self.tree.itemBelow(current)
                if below:
                    self.tree.setCurrentItem(below)
        elif event.key() == Qt.Key_Up:
            current = self.tree.currentItem()
            if current:
                above = self.tree.itemAbove(current)
                if above:
                    self.tree.setCurrentItem(above)
        else:
            super().keyPressEvent(event)


USAGE_GUIDE_HTML = """
<h1>化学学习套件 — 使用说明</h1>

<h2>一、启动</h2>
<p>终端执行 <code>~/chemistry-suite/run.sh</code> 启动应用。首次启动自动启动本地 HTTP 服务器 (端口 8766)。</p>

<h2>二、界面布局</h2>
<ul>
  <li><b>左侧工具栏</b> — 点击按钮打开工具面板 (结构/3D/公式/周期表/工具/笔记)</li>
  <li><b>中间</b> — 工具面板 (按需加载，可分离为独立窗口)</li>
  <li><b>右侧</b> — PDF 电子书阅读器 (始终可见)</li>
  <li><b>顶部</b> — 学科标签 + 菜单栏</li>
</ul>

<h2>三、工具栏按钮</h2>
<table border=1 cellpadding=4 cellspacing=0>
  <tr><th>按钮</th><th>功能</th></tr>
  <tr><td>结构</td><td>2D 结构编辑器 (Ketcher) — 绘制/导入化学结构</td></tr>
  <tr><td>3D</td><td>3D 分子查看器 — 旋转/缩放/切换显示模式</td></tr>
  <tr><td>公式</td><td>KaTeX 公式编辑器 — LaTeX 实时渲染</td></tr>
  <tr><td>周期表</td><td>交互式元素周期表 — 点击元素查看性质</td></tr>
  <tr><td>工具</td><td>化学工具集 — 计算器/波谱/点群/MO/晶体等 12 个工具</td></tr>
  <tr><td>笔记</td><td>笔记面板 — Markdown 笔记，分学科管理</td></tr>
</table>

<h2>四、面板分离 (Detach)</h2>
<ul>
  <li>工具面板标题栏右侧 <b>↗ 按钮</b> — 将面板分离为独立窗口</li>
  <li>分离后可自由拖动到第二屏幕</li>
  <li><b>关闭浮窗</b> 或 <b>点击左侧工具栏按钮</b> — 自动 Dock 回主窗口</li>
  <li>浮窗菜单栏有 <b>"Dock 回主窗口"</b> 选项</li>
</ul>

<h2>五、PDF 电子书右键菜单</h2>
<p>在电子书中<b>选中化学名词/结构名</b> → 右键：</p>
<ul>
  <li><b>常用</b>：打开结构 | 查看3D | 查询原子量 | PubChem搜索 | 添加笔记</li>
  <li><b>更多</b>：波谱 | MO | IUPAC命名 | 热力学 | 晶体</li>
</ul>

<h2>六、快捷键</h2>
<table border=1 cellpadding=4 cellspacing=0>
  <tr><th>快捷键</th><th>功能</th></tr>
  <tr><td><b>Ctrl+Shift+P</b></td><td>命令面板</td></tr>
  <tr><td><b>Ctrl+1~6</b></td><td>切换学科标签</td></tr>
  <tr><td><b>Ctrl+O</b></td><td>打开结构文件</td></tr>
  <tr><td><b>Ctrl+P</b></td><td>打开教材 PDF</td></tr>
  <tr><td><b>Ctrl+D</b></td><td>2D → 3D</td></tr>
  <tr><td><b>Ctrl+G</b></td><td>获取 SMILES</td></tr>
  <tr><td><b>Ctrl+B</b></td><td>切换笔记面板</td></tr>
  <tr><td><b>Ctrl+Q</b></td><td>退出</td></tr>
  <tr><td><b>F11</b></td><td>全屏</td></tr>
  <tr><td><b>Ctrl+Shift+Space</b></td><td>聚焦 SMILES 输入</td></tr>
</table>

<h2>七、结构导入方式</h2>
<ol>
  <li><b>SMILES 输入</b> — 结构编辑器中输入 SMILES 回车</li>
  <li><b>化合物名称</b> — 输入中/英文名自动 PubChem 搜索</li>
  <li><b>文件菜单</b> — 打开结构文件 / 从 PubChem、PDB 导入</li>
  <li><b>拖放文件</b> — 将 .mol/.sdf/.pdb 拖入窗口</li>
  <li><b>PDF 选中文字右键</b> — 自动搜索并加载</li>
</ol>

<h2>八、常见问题</h2>
<p><b>Q: 端口 8766 被占用？</b><br>A: 关闭之前的进程或修改代码中的 http_port 参数。</p>
<p><b>Q: PubChem 失败？</b><br>A: 检查网络，尝试英文名或 CID 号。</p>
<p><b>Q: 备份笔记？</b><br>A: 复制 <code>~/chemistry-suite/notes/notes.db</code>。</p>

<hr>
<p style="color:#888;">化学学习套件 v0.4 — 面板可分离 | 右键菜单 | 命令面板 | 快捷键可见</p>
"""


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    app = QApplication(sys.argv)
    app.setApplicationName("化学学习套件")
    app.setOrganizationName("ChemistrySuite")
    app.setStyle("Fusion")

    window = ChemistrySuite()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
