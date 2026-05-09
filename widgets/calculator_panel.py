"""化学计算器面板"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTextEdit,
)
from PySide6.QtCore import Qt

from core.i18n import i18n


class CalculatorPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        title = QLabel(f"<b>{i18n.tr('化学计算器')}</b>")
        layout.addWidget(title)

        self._tabs = QTabWidget()

        self._tabs.addTab(self._mw_tab(), i18n.tr("分子量/元素分析"))
        self._tabs.addTab(self._solution_tab(), i18n.tr("溶液配制"))
        self._tabs.addTab(self._ph_tab(), i18n.tr("pH 计算"))
        self._tabs.addTab(self._yield_tab(), i18n.tr("产率/稀释"))

        layout.addWidget(self._tabs)

        i18n.languageChanged.connect(self._update_ui_texts)

    def _update_ui_texts(self, lang_code=None):
        """语言切换时刷新"""
        self._tabs.setTabText(0, i18n.tr("分子量/元素分析"))
        self._tabs.setTabText(1, i18n.tr("溶液配制"))
        self._tabs.setTabText(2, i18n.tr("pH 计算"))
        self._tabs.setTabText(3, i18n.tr("产率/稀释"))
        self.mw_input.setPlaceholderText(i18n.tr("SMILES (如 CCO) 或 分子式"))
        self.mw_btn.setText(i18n.tr("计算"))
        self.sol_mass.setPlaceholderText(i18n.tr("质量 (g):"))
        self.sol_volume.setPlaceholderText(i18n.tr("体积 (L):"))
        self.sol_conc.setPlaceholderText(i18n.tr("浓度 (mol/L):"))
        self.sol_mw.setPlaceholderText(i18n.tr("摩尔质量:"))
        self.sol_btn.setText(i18n.tr("计算 (输入其中三项)"))
        self.ph_hplus.setPlaceholderText(i18n.tr("直接输入 [H+]"))
        self.ph_ka.setPlaceholderText(i18n.tr("Ka (弱酸)"))
        self.ph_ka_conc.setPlaceholderText(i18n.tr("弱酸浓度"))
        self.ph_btn.setText(i18n.tr("计算 pH"))
        self.yld_theo.setPlaceholderText(i18n.tr("理论产量:"))
        self.yld_actual.setPlaceholderText(i18n.tr("实际产量:"))
        self.yld_btn.setText(i18n.tr("计算产率"))
        self.dil_btn.setText(i18n.tr("计算稀释"))

    def _mw_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.mw_input = QLineEdit()
        self.mw_input.setPlaceholderText(i18n.tr("SMILES (如 CCO) 或 分子式"))
        layout.addRow(i18n.tr("输入:"), self.mw_input)

        self.mw_btn = QPushButton(i18n.tr("计算"))
        self.mw_btn.clicked.connect(self._calc_mw)
        layout.addRow("", self.mw_btn)

        self.mw_output = QLabel("")
        self.mw_output.setWordWrap(True)
        layout.addRow("", self.mw_output)
        return w

    def _solution_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.sol_mass = QLineEdit()
        self.sol_mass.setPlaceholderText(i18n.tr("质量 (g):"))
        self.sol_volume = QLineEdit()
        self.sol_volume.setPlaceholderText(i18n.tr("体积 (L):"))
        self.sol_conc = QLineEdit()
        self.sol_conc.setPlaceholderText(i18n.tr("浓度 (mol/L):"))
        self.sol_mw = QLineEdit()
        self.sol_mw.setPlaceholderText(i18n.tr("摩尔质量:"))

        layout.addRow(i18n.tr("质量 (g):"), self.sol_mass)
        layout.addRow(i18n.tr("体积 (L):"), self.sol_volume)
        layout.addRow(i18n.tr("浓度 (mol/L):"), self.sol_conc)
        layout.addRow(i18n.tr("摩尔质量:"), self.sol_mw)

        self.sol_btn = QPushButton(i18n.tr("计算 (输入其中三项)"))
        self.sol_btn.clicked.connect(self._calc_solution)
        layout.addRow("", self.sol_btn)

        self.sol_output = QLabel("")
        layout.addRow("", self.sol_output)
        return w

    def _ph_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.ph_hplus = QLineEdit()
        self.ph_hplus.setPlaceholderText(i18n.tr("直接输入 [H+]"))
        self.ph_ka = QLineEdit()
        self.ph_ka.setPlaceholderText(i18n.tr("Ka (弱酸)"))
        self.ph_ka_conc = QLineEdit()
        self.ph_ka_conc.setPlaceholderText(i18n.tr("弱酸浓度"))

        layout.addRow("[H+] (mol/L):", self.ph_hplus)
        layout.addRow("Ka:", self.ph_ka)
        layout.addRow(i18n.tr("弱酸浓度") + ":", self.ph_ka_conc)

        self.ph_btn = QPushButton(i18n.tr("计算 pH"))
        self.ph_btn.clicked.connect(self._calc_ph)
        layout.addRow("", self.ph_btn)

        self.ph_output = QLabel("")
        layout.addRow("", self.ph_output)
        return w

    def _yield_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.yld_theo = QLineEdit()
        self.yld_theo.setPlaceholderText(i18n.tr("理论产量:"))
        self.yld_actual = QLineEdit()
        self.yld_actual.setPlaceholderText(i18n.tr("实际产量:"))

        layout.addRow(i18n.tr("理论产量:"), self.yld_theo)
        layout.addRow(i18n.tr("实际产量:"), self.yld_actual)

        self.yld_btn = QPushButton(i18n.tr("计算产率"))
        self.yld_btn.clicked.connect(self._calc_yield)
        layout.addRow("", self.yld_btn)

        self.yld_output = QLabel("")
        layout.addRow("", self.yld_output)

        # 稀释
        layout.addRow(QLabel("<hr>"), QLabel("<hr>"))
        self.dil_c1 = QLineEdit()
        self.dil_c1.setPlaceholderText("c1")
        self.dil_v1 = QLineEdit()
        self.dil_v1.setPlaceholderText("v1")
        self.dil_c2 = QLineEdit()
        self.dil_c2.setPlaceholderText("c2 (留空自动算)")
        self.dil_v2 = QLineEdit()
        self.dil_v2.setPlaceholderText("v2 (留空自动算)")

        layout.addRow("c1:", self.dil_c1)
        layout.addRow("v1:", self.dil_v1)
        layout.addRow("c2:", self.dil_c2)
        layout.addRow("v2:", self.dil_v2)

        self.dil_btn = QPushButton(i18n.tr("计算稀释"))
        self.dil_btn.clicked.connect(self._calc_dilution)
        layout.addRow("", self.dil_btn)
        self.dil_output = QLabel("")
        layout.addRow("", self.dil_output)
        return w

    def _calc_mw(self):
        try:
            from core.calculator import calc_molecular_weight, calc_elemental_analysis
            inp = self.mw_input.text().strip()
            result = calc_elemental_analysis(inp)
            text = f"<b>分子式:</b> {result['formula']}<br>"
            text += f"<b>分子量:</b> {result['mw']} g/mol<br><br>"
            for sym, d in result['elements'].items():
                text += f"{sym}: {d['count']}× = {d['mass']} g/mol ({d['percent']}%)<br>"
            self.mw_output.setText(text)
        except Exception as e:
            self.mw_output.setText(f"<span style='color:red;'>错误: {e}</span>")

    def _calc_solution(self):
        try:
            from core.calculator import calc_solution
            mass = float(self.sol_mass.text()) if self.sol_mass.text() else None
            volume = float(self.sol_volume.text()) if self.sol_volume.text() else None
            conc = float(self.sol_conc.text()) if self.sol_conc.text() else None
            mw = float(self.sol_mw.text()) if self.sol_mw.text() else None
            result = calc_solution(mass=mass, volume=volume, concentration=conc, mw=mw)
            text = "  ".join(f"{k}={v}" for k, v in result.items())
            self.sol_output.setText(text)
        except Exception as e:
            self.sol_output.setText(f"<span style='color:red;'>错误: {e}</span>")

    def _calc_ph(self):
        try:
            from core.calculator import calc_ph
            hplus = float(self.ph_hplus.text()) if self.ph_hplus.text() else None
            ka = float(self.ph_ka.text()) if self.ph_ka.text() else None
            conc = float(self.ph_ka_conc.text()) if self.ph_ka_conc.text() else None
            result = calc_ph(hplus=hplus, ka=ka, c_acid=conc)
            text = "  ".join(f"{k}={v}" for k, v in result.items())
            self.ph_output.setText(text)
        except Exception as e:
            self.ph_output.setText(f"<span style='color:red;'>错误: {e}</span>")

    def _calc_yield(self):
        try:
            from core.calculator import calc_yield
            theo = float(self.yld_theo.text())
            actual = float(self.yld_actual.text())
            result = calc_yield(theo, actual)
            self.yld_output.setText(f"产率: {result['yield_percent']}%")
        except Exception as e:
            self.yld_output.setText(f"<span style='color:red;'>错误: {e}</span>")

    def _calc_dilution(self):
        try:
            from core.calculator import calc_dilution
            c1 = float(self.dil_c1.text())
            v1 = float(self.dil_v1.text())
            c2 = float(self.dil_c2.text()) if self.dil_c2.text() else None
            v2 = float(self.dil_v2.text()) if self.dil_v2.text() else None
            result = calc_dilution(c1, v1, c2, v2)
            text = "  ".join(f"{k}={v}" for k, v in result.items())
            self.dil_output.setText(text)
        except Exception as e:
            self.dil_output.setText(f"<span style='color:red;'>错误: {e}</span>")
