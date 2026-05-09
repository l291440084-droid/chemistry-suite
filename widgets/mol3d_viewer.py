"""3D 分子建模器 — 自主搭建、力场优化、稳定性检测"""

import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTextEdit, QSplitter, QFrame, QMessageBox,
    QFileDialog, QGridLayout, QButtonGroup,
)
from PySide6.QtCore import Qt, QUrl, QObject, Signal, Slot, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from core.i18n import i18n

# 常用元素 (符号, 名称, 颜色)
COMMON_ELEMENTS = [
    ("H",  "氢",  "#FFFFFF"),
    ("C",  "碳",  "#404040"),
    ("N",  "氮",  "#3050F0"),
    ("O",  "氧",  "#FF2010"),
    ("F",  "氟",  "#80FF20"),
    ("Si", "硅",  "#808080"),
    ("P",  "磷",  "#FF8000"),
    ("S",  "硫",  "#FFCC00"),
    ("Cl", "氯",  "#20FF20"),
    ("Br", "溴",  "#802020"),
    ("I",  "碘",  "#802080"),
    ("B",  "硼",  "#80FF80"),
    ("Na", "钠",  "#4040FF"),
    ("Mg", "镁",  "#208020"),
    ("Fe", "铁",  "#E08020"),
]

DISPLAY_MODES = [
    ("球棍", "ballstick"),
    ("棍状", "stick"),
    ("空间填充", "sphere"),
    ("线框", "line"),
]

FRAGMENTS = [
    ("甲基 -CH₃", "C"),
    ("乙基 -C₂H₅", "CC"),
    ("苯环", "c1ccccc1"),
    ("羧基 -COOH", "C(=O)O"),
    ("氨基 -NH₂", "N"),
    ("羟基 -OH", "O"),
    ("醛基 -CHO", "C=O"),
    ("氰基 -CN", "C#N"),
    ("硝基 -NO₂", "N(=O)=O"),
    ("三氟甲基 -CF₃", "C(F)(F)F"),
]


class Mol3DBridge(QObject):
    """Python ↔ 3Dmol.js 双向通信"""
    statusMessage = Signal(str)
    atomClicked = Signal(int, str, float, float, float)  # idx, elem, x, y, z
    structureExported = Signal(str)  # molfile

    @Slot(str)
    def onStatus(self, msg: str):
        self.statusMessage.emit(msg)

    @Slot(int, str, float, float, float)
    def onAtomClicked(self, idx: int, elem: str, x: float, y: float, z: float):
        self.atomClicked.emit(idx, elem, x, y, z)

    @Slot(str)
    def onStructureExported(self, molfile: str):
        self.structureExported.emit(molfile)


class Mol3DViewerWidget(QWidget):
    """3D 分子建模器面板"""

    def __init__(self, http_port: int = 8766, parent=None):
        super().__init__(parent)
        self._port = http_port
        self._bridge = None
        self._init_ui()
        QTimer.singleShot(500, self._on_ready)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # ── 工具栏 ──
        layout.addLayout(self._build_toolbar())

        # ── 主区域: 3D 视口 + 属性面板 ──
        splitter = QSplitter(Qt.Horizontal)

        # 3D 视口
        view_widget = QWidget()
        view_lo = QVBoxLayout(view_widget)
        view_lo.setContentsMargins(0, 0, 0, 0)

        self._webview = QWebEngineView()
        self._channel = QWebChannel()
        self._bridge = Mol3DBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._webview.page().setWebChannel(self._channel)

        url = f"http://127.0.0.1:{self._port}/3dmol/viewer.html"
        self._webview.setUrl(QUrl(url))
        view_lo.addWidget(self._webview)

        # 底栏
        self._status_bar = QLabel("就绪")
        self._status_bar.setStyleSheet(
            "background: #222; color: #aaa; font-size: 11px; padding: 2px 8px;"
        )
        view_lo.addWidget(self._status_bar)

        splitter.addWidget(view_widget)

        # 属性面板
        self._props_panel = self._build_props_panel()
        splitter.addWidget(self._props_panel)
        splitter.setSizes([700, 240])

        layout.addWidget(splitter)

        # 桥接信号
        self._bridge.statusMessage.connect(self._status_bar.setText)
        self._bridge.atomClicked.connect(self._on_atom_clicked)
        self._bridge.structureExported.connect(self._on_structure_exported)

        i18n.languageChanged.connect(self._update_ui_texts)

    def _build_toolbar(self):
        tb = QHBoxLayout()
        tb.setSpacing(4)

        # 模式按钮
        self._btn_build = QPushButton(i18n.tr("搭建"))
        self._btn_build.setCheckable(True)
        self._btn_build.setToolTip(i18n.tr("点击空白放置原子 / 点击原子选中"))
        self._btn_build.clicked.connect(lambda: self._set_mode("build"))

        self._btn_select = QPushButton(i18n.tr("选择"))
        self._btn_select.setCheckable(True)
        self._btn_select.setChecked(True)
        self._btn_select.clicked.connect(lambda: self._set_mode("select"))

        self._btn_delete = QPushButton(i18n.tr("删除"))
        self._btn_delete.setCheckable(True)
        self._btn_delete.clicked.connect(lambda: self._set_mode("delete"))

        self._btn_measure = QPushButton(i18n.tr("测量"))
        self._btn_measure.setCheckable(True)
        self._btn_measure.clicked.connect(lambda: self._set_mode("measure"))

        for btn in [self._btn_build, self._btn_select, self._btn_delete, self._btn_measure]:
            btn.setMaximumWidth(50)
            btn.setStyleSheet(
                "QPushButton { padding: 3px 6px; font-size: 11px; }"
                "QPushButton:checked { background: #4fc3f7; color: #000; }"
            )
            tb.addWidget(btn)

        tb.addWidget(_sep())

        # 元素选择
        self._elem_label = QLabel(i18n.tr("元素:"))
        tb.addWidget(self._elem_label)
        self._elem_buttons = QButtonGroup(self)
        self._elem_buttons.setExclusive(True)
        self._active_element = "C"

        for i, (sym, name, color) in enumerate(COMMON_ELEMENTS):
            btn = QPushButton(sym)
            btn.setFixedSize(28, 28)
            btn.setCheckable(True)
            btn.setToolTip(i18n.tr(name))
            btn.setStyleSheet(
                f"QPushButton {{ background: {color}; color: {'#000' if sym in 'HFSiClBrIBMgNa' else '#fff'}; "
                f"font-size: 10px; font-weight: bold; border: 1px solid #666; border-radius: 3px; }}"
                "QPushButton:checked { border: 2px solid #4fc3f7; }"
            )
            if sym == "C":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=sym: self._on_element_changed(s))
            self._elem_buttons.addButton(btn, i)
            tb.addWidget(btn)

        tb.addWidget(_sep())

        # 显示模式
        self._display_label = QLabel(i18n.tr("显示:"))
        tb.addWidget(self._display_label)
        self._display_combo = QComboBox()
        for name, _ in DISPLAY_MODES:
            self._display_combo.addItem(i18n.tr(name))
        self._display_combo.currentIndexChanged.connect(self._on_display_changed)
        tb.addWidget(self._display_combo)

        tb.addWidget(_sep())

        # 操作按钮
        self._btn_opt = QPushButton(i18n.tr("优化"))
        self._btn_opt.setToolTip(i18n.tr("MMFF94 力场优化结构"))
        self._btn_opt.clicked.connect(self._optimize)
        tb.addWidget(self._btn_opt)

        self._btn_h_add = QPushButton("+H")
        self._btn_h_add.setToolTip(i18n.tr("加氢"))
        self._btn_h_add.clicked.connect(self._add_hydrogens)
        self._btn_h_add.setMaximumWidth(36)
        tb.addWidget(self._btn_h_add)

        self._btn_h_rem = QPushButton("-H")
        self._btn_h_rem.setToolTip(i18n.tr("去氢"))
        self._btn_h_rem.clicked.connect(self._remove_hydrogens)
        self._btn_h_rem.setMaximumWidth(36)
        tb.addWidget(self._btn_h_rem)

        self._btn_check = QPushButton(i18n.tr("检测"))
        self._btn_check.setToolTip(i18n.tr("检测结构问题"))
        self._btn_check.clicked.connect(self._check_structure)
        tb.addWidget(self._btn_check)

        tb.addWidget(_sep())

        # 片段库
        self._frag_combo = QComboBox()
        self._frag_combo.addItem(i18n.tr("片段库 ▼"))
        for name, _ in FRAGMENTS:
            self._frag_combo.addItem(i18n.tr(name))
        self._frag_combo.currentIndexChanged.connect(self._on_fragment)
        tb.addWidget(self._frag_combo)

        tb.addWidget(_sep())

        # 导入导出
        self._btn_import = QPushButton(i18n.tr("导入"))
        self._btn_import.clicked.connect(self._import_structure)
        tb.addWidget(self._btn_import)

        self._export_combo = QComboBox()
        self._export_combo.addItem(i18n.tr("导出 ▼"))
        for fmt in ["MOL", "PDB", "XYZ"]:
            self._export_combo.addItem(fmt)
        self._export_combo.currentIndexChanged.connect(self._export_structure)
        tb.addWidget(self._export_combo)

        self._btn_clear = QPushButton(i18n.tr("清除"))
        self._btn_clear.clicked.connect(self.clear)
        tb.addWidget(self._btn_clear)

        tb.addStretch()
        return tb

    def _build_props_panel(self):
        w = QWidget()
        w.setFixedWidth(240)
        lo = QVBoxLayout(w)
        lo.setContentsMargins(6, 4, 6, 4)
        lo.setSpacing(6)

        # 原子信息
        self._props_atom_title = QLabel(f"<b>{i18n.tr('选中原子')}</b>")
        lo.addWidget(self._props_atom_title)
        self._atom_info = QTextEdit()
        self._atom_info.setReadOnly(True)
        self._atom_info.setMaximumHeight(100)
        self._atom_info.setStyleSheet("font-size: 11px; background: #f5f5f5;")
        self._atom_info.setPlaceholderText(i18n.tr("点击原子查看信息"))
        lo.addWidget(self._atom_info)

        # 能量
        self._props_energy_title = QLabel(f"<b>{i18n.tr('能量 / 稳定性')}</b>")
        lo.addWidget(self._props_energy_title)
        self._energy_label = QLabel(i18n.tr("尚未计算"))
        self._energy_label.setWordWrap(True)
        self._energy_label.setStyleSheet("font-size: 11px; color: #555;")
        lo.addWidget(self._energy_label)

        # 问题列表
        self._props_issues_title = QLabel(f"<b>{i18n.tr('结构问题')}</b>")
        lo.addWidget(self._props_issues_title)
        self._issues_text = QTextEdit()
        self._issues_text.setReadOnly(True)
        self._issues_text.setMaximumHeight(100)
        self._issues_text.setStyleSheet("font-size: 10px; background: #fff8f0;")
        self._issues_text.setPlaceholderText(i18n.tr("点击「检测」分析结构"))
        lo.addWidget(self._issues_text)

        # 测量
        self._props_measure_title = QLabel(f"<b>{i18n.tr('测量结果')}</b>")
        lo.addWidget(self._props_measure_title)
        self._measure_label = QLabel(i18n.tr("选择测量模式，点击两个原子"))
        self._measure_label.setWordWrap(True)
        self._measure_label.setStyleSheet("font-size: 10px; color: #555;")
        lo.addWidget(self._measure_label)

        # 统计
        self._props_stats_title = QLabel(f"<b>{i18n.tr('结构统计')}</b>")
        lo.addWidget(self._props_stats_title)
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("font-size: 10px; color: #555;")
        lo.addWidget(self._stats_label)

        lo.addStretch()
        return w

    # ── JS 通信 ───────────────────────────────────────────────
    def _call_js(self, func: str, *args):
        js_args = ", ".join(json.dumps(a) for a in args)
        js = f"if (typeof {func} === 'function') {{ {func}({js_args}); }}"
        self._webview.page().runJavaScript(js)

    def _on_ready(self):
        self._status_bar.setText(i18n.tr("3D 建模器就绪 — 点击「搭建」开始放置原子"))

    def _update_ui_texts(self, lang_code=None):
        """语言切换时刷新所有 UI 文本"""
        # 模式按钮
        self._btn_build.setText(i18n.tr("搭建"))
        self._btn_build.setToolTip(i18n.tr("点击空白放置原子 / 点击原子选中"))
        self._btn_select.setText(i18n.tr("选择"))
        self._btn_delete.setText(i18n.tr("删除"))
        self._btn_measure.setText(i18n.tr("测量"))

        # 元素/显示标签
        self._elem_label.setText(i18n.tr("元素:"))
        self._display_label.setText(i18n.tr("显示:"))

        # 显示模式 combo
        for i, (name, _) in enumerate(DISPLAY_MODES):
            self._display_combo.setItemText(i, i18n.tr(name))

        # 元素按钮 tooltips
        for i, (_, name, _) in enumerate(COMMON_ELEMENTS):
            btn = self._elem_buttons.button(i)
            if btn:
                btn.setToolTip(i18n.tr(name))

        # 操作按钮
        self._btn_opt.setText(i18n.tr("优化"))
        self._btn_opt.setToolTip(i18n.tr("MMFF94 力场优化结构"))
        self._btn_h_add.setToolTip(i18n.tr("加氢"))
        self._btn_h_rem.setToolTip(i18n.tr("去氢"))
        self._btn_check.setText(i18n.tr("检测"))
        self._btn_check.setToolTip(i18n.tr("检测结构问题"))

        # 片段库
        self._frag_combo.setItemText(0, i18n.tr("片段库 ▼"))
        for i, (name, _) in enumerate(FRAGMENTS):
            self._frag_combo.setItemText(i + 1, i18n.tr(name))

        # 导入/导出/清除
        self._btn_import.setText(i18n.tr("导入"))
        self._export_combo.setItemText(0, i18n.tr("导出 ▼"))
        self._btn_clear.setText(i18n.tr("清除"))

        # 属性面板标题
        self._props_atom_title.setText(f"<b>{i18n.tr('选中原子')}</b>")
        self._props_energy_title.setText(f"<b>{i18n.tr('能量 / 稳定性')}</b>")
        self._props_issues_title.setText(f"<b>{i18n.tr('结构问题')}</b>")
        self._props_measure_title.setText(f"<b>{i18n.tr('测量结果')}</b>")
        self._props_stats_title.setText(f"<b>{i18n.tr('结构统计')}</b>")

        # 占位文本
        self._atom_info.setPlaceholderText(i18n.tr("点击原子查看信息"))
        self._issues_text.setPlaceholderText(i18n.tr("点击「检测」分析结构"))
        self._measure_label.setText(i18n.tr("选择测量模式，点击两个原子"))

        # 能量标签(如果不处于计算状态)
        if self._energy_label.text() and "kcal" not in self._energy_label.text():
            self._energy_label.setText(i18n.tr("尚未计算"))

    # ── 模式切换 ──────────────────────────────────────────────
    def _set_mode(self, mode):
        for btn, m in [
            (self._btn_build, "build"),
            (self._btn_select, "select"),
            (self._btn_delete, "delete"),
            (self._btn_measure, "measure"),
        ]:
            btn.setChecked(m == mode)
        self._call_js("setMode", mode)

    def _on_element_changed(self, sym):
        self._active_element = sym
        self._call_js("setActiveElement", sym)
        self._status_bar.setText(i18n.tr("当前元素: ") + sym)

    def _on_display_changed(self, idx):
        mode = DISPLAY_MODES[idx][1]
        self._call_js("setDisplayMode", mode)

    def _on_fragment(self, idx):
        if idx <= 0:
            return
        _, smiles = FRAGMENTS[idx - 1]
        self.load_smiles(smiles)
        from core.mol3d_utils import smiles_to_3d_molfile
        try:
            molfile = smiles_to_3d_molfile(smiles)
            self._call_js("addMolfile", molfile)
        except Exception:
            pass  # 3Dmol.js 会尝试从 SMILES 直接生成
        self._frag_combo.setCurrentIndex(0)

    # ── 原子点击回调 ──────────────────────────────────────────
    def _on_atom_clicked(self, idx, elem, x, y, z):
        self._atom_info.setHtml(
            f"<b>索引:</b> {idx}<br>"
            f"<b>元素:</b> {elem}<br>"
            f"<b>坐标:</b> ({x:.3f}, {y:.3f}, {z:.3f}) Å"
        )

    # ── 优化 ──────────────────────────────────────────────────
    def _optimize(self):
        self._status_bar.setText(i18n.tr("正在优化..."))
        self._call_js("exportMolfile")  # 触发 JS 导出 → bridge.onStructureExported

    def _on_structure_exported(self, data):
        try:
            from core.mol3d_utils import optimize_geometry, detect_issues, calculate_energy
            if "M  END" in data or "V2000" in data:
                molfile = data
            else:
                # JSON 格式的原子列表
                atoms = json.loads(data)
                from core.mol3d_utils import xyz_to_molfile
                molfile = xyz_to_molfile(atoms)

            result = optimize_geometry(molfile)
            self._call_js("addMolfile", result["molfile"])
            conv_text = "✓" if result['converged'] else "✗"
            self._energy_label.setText(
                f"E_before: {result['energy_before']}  E_after: <b>{result['energy_after']}</b> kcal/mol<br>"
                f"Converged: {conv_text}"
            )

            # 检测问题
            issues = detect_issues(result["molfile"])
            self._issues_text.clear()
            if issues["issues"]:
                self._issues_text.setHtml(
                    "<span style='color:#c44;'>⚠ " + "<br>".join(issues["issues"]) + "</span>"
                )
            else:
                self._issues_text.setHtml(f"<span style='color:#4a4;'>✓ {i18n.tr('结构正常，无明显问题')}</span>")

            self._stats_label.setText(
                f"Atoms: {result['num_atoms']} | Bonds: {result['num_bonds']}"
            )
            self._status_bar.setText(
                i18n.tr("优化完成 — 能量: ") + f"{result['energy_after']} kcal/mol"
            )
        except Exception as e:
            self._status_bar.setText(i18n.tr("优化失败: ") + str(e))

    # ── 检测 ──────────────────────────────────────────────────
    def _check_structure(self):
        self._call_js("exportMolfile")

    # ── 加氢/去氢 ─────────────────────────────────────────────
    def _add_hydrogens(self):
        def _cb(data):
            try:
                from core.mol3d_utils import add_hydrogens, xyz_to_molfile
                if "M  END" in data or "V2000" in data:
                    molfile = add_hydrogens(data)
                else:
                    atoms = json.loads(data)
                    molfile = xyz_to_molfile(atoms)
                    molfile = add_hydrogens(molfile)
                self._call_js("addMolfile", molfile)
                self._status_bar.setText(i18n.tr("已加氢"))
            except Exception as e:
                self._status_bar.setText(i18n.tr("加氢失败: ") + str(e))

        # 临时连接
        self._bridge.structureExported.connect(_cb)
        self._call_js("exportMolfile")
        QTimer.singleShot(500, lambda: self._bridge.structureExported.disconnect(_cb))

    def _remove_hydrogens(self):
        def _cb(data):
            try:
                from core.mol3d_utils import remove_hydrogens, xyz_to_molfile
                if "M  END" in data or "V2000" in data:
                    molfile = remove_hydrogens(data)
                else:
                    atoms = json.loads(data)
                    molfile = xyz_to_molfile(atoms)
                    molfile = remove_hydrogens(molfile)
                self._call_js("addMolfile", molfile)
                self._status_bar.setText(i18n.tr("已去氢"))
            except Exception as e:
                self._status_bar.setText(i18n.tr("去氢失败: ") + str(e))

        self._bridge.structureExported.connect(_cb)
        self._call_js("exportMolfile")
        QTimer.singleShot(500, lambda: self._bridge.structureExported.disconnect(_cb))

    # ── 导入 ──────────────────────────────────────────────────
    def _import_structure(self):
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("导入结构文件"), "",
            i18n.tr("化学结构 (*.mol *.sdf *.pdb *.xyz *.smi);;所有文件 (*)")
        )
        if not path:
            return
        try:
            ext = path.lower()
            with open(path) as f:
                data = f.read()
            if ext.endswith((".mol", ".sdf")):
                self._call_js("addMolfile", data)
            elif ext.endswith(".pdb"):
                self.load_pdb(data)
            elif ext.endswith(".xyz"):
                self._call_js("addXYZ", data)
            elif ext.endswith(".smi"):
                self.load_smiles(data.strip())
            self._status_bar.setText(i18n.tr("已导入: ") + path.split('/')[-1])
        except Exception as e:
            QMessageBox.warning(self, i18n.tr("导入失败"), str(e))

    def _export_structure(self, idx):
        fmt = self._export_combo.currentText()
        if fmt == "导出 ▼":
            return

        def _cb(data):
            try:
                from core.mol3d_utils import xyz_to_molfile
                if "M  END" not in data and "V2000" not in data:
                    atoms = json.loads(data)
                    molfile = xyz_to_molfile(atoms)
                else:
                    molfile = data

                ext_map = {"MOL": ".mol", "PDB": ".pdb", "XYZ": ".xyz"}
                path, _ = QFileDialog.getSaveFileName(
                    self, f"{i18n.tr('导出 ▼').rstrip(' ▼')} {fmt}", f"molecule{ext_map[fmt]}",
                    f"{fmt} 文件 (*{ext_map[fmt]});;所有文件 (*)"
                )
                if not path:
                    return

                if fmt == "MOL":
                    with open(path, "w") as f:
                        f.write(molfile)
                elif fmt == "PDB":
                    from rdkit import Chem
                    mol = Chem.MolFromMolBlock(molfile)
                    if mol:
                        Chem.MolToPDBFile(mol, path)
                elif fmt == "XYZ":
                    from rdkit import Chem
                    mol = Chem.MolFromMolBlock(molfile)
                    if mol:
                        Chem.MolToXYZFile(mol, path)

                self._status_bar.setText(i18n.tr("已导出: ") + path.split('/')[-1])
            except Exception as e:
                QMessageBox.warning(self, i18n.tr("导出失败"), str(e))
            self._export_combo.setCurrentIndex(0)

        self._bridge.structureExported.connect(_cb)
        self._call_js("exportMolfile")
        QTimer.singleShot(500, lambda: self._bridge.structureExported.disconnect(_cb))

    # ── 公开 API ──────────────────────────────────────────────
    def load_smiles(self, smiles: str):
        self._call_js("loadSmiles", smiles)

    def load_molfile(self, molfile: str):
        self._call_js("addMolfile", molfile)

    def load_pdb(self, pdb_data: str):
        self._call_js("loadPdb", pdb_data)

    def set_style(self, mode: str):
        self._call_js("setDisplayMode", mode)

    def clear(self):
        self._call_js("clearViewer")
        self._atom_info.clear()
        self._energy_label.setText(i18n.tr("尚未计算"))
        self._issues_text.clear()
        self._measure_label.setText("")
        self._stats_label.setText("")
        self._status_bar.setText(i18n.tr("画布已清除"))


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setMaximumWidth(1)
    f.setStyleSheet("background: #ccc;")
    return f
