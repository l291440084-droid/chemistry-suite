"""VS Code 风格左侧工具栏"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.i18n import i18n


BUTTON_STYLE = """
    QToolButton {
        border: none;
        color: #bbb;
        font-size: 10px;
        padding: 6px 2px;
        border-left: 2px solid transparent;
        background: transparent;
    }
    QToolButton:hover {
        background: #3a3a3a;
        color: #fff;
    }
    QToolButton:checked {
        background: #37373d;
        color: #fff;
        border-left: 2px solid #4fc3f7;
    }
"""

SIDEBAR_STYLE = """
    QWidget#sidebar {
        background: #2b2b2b;
        border-right: 1px solid #3c3c3c;
    }
"""


class SidebarButton(QToolButton):
    def __init__(self, icon_char, text, parent=None):
        super().__init__(parent)
        self._icon_char = icon_char
        self._text_key = text  # original Chinese text key
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self._update_label()
        self.setCheckable(True)
        self.setFont(QFont("sans-serif", 10))
        self.setMinimumWidth(54)
        self.setMaximumWidth(54)
        self.setMinimumHeight(56)
        self.setMaximumHeight(56)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setStyleSheet(BUTTON_STYLE)
        self._update_tooltip()

    def _update_label(self):
        self.setText(f"{self._icon_char}\n{i18n.tr(self._text_key)}")

    def _update_tooltip(self):
        self.setToolTip(i18n.tr(self._text_key))

    def refresh_i18n(self):
        self._update_label()
        self._update_tooltip()


class Sidebar(QWidget):
    """左侧工具栏 — 每个按钮切换对应工具面板"""

    toolToggled = Signal(str, bool)  # tool_name, checked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setStyleSheet(SIDEBAR_STYLE)
        self.setFixedWidth(54)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(1)

        self._buttons = {}

        # 图标 + 文字 (图标在上，文字在下)
        tools = [
            ("mol", "结构"),
            ("3d",  "3D"),
            ("fx",  "公式"),
            ("pt",  "周期表"),
            ("tl",  "工具"),
            ("nt",  "笔记"),
        ]
        for key, name in tools:
            btn = SidebarButton(key, name)
            btn.toggled.connect(lambda checked, k=key: self.toolToggled.emit(k, checked))
            layout.addWidget(btn)
            self._buttons[key] = btn

        layout.addStretch()

        i18n.languageChanged.connect(self._on_language_changed)

    def _on_language_changed(self, lang_code):
        for btn in self._buttons.values():
            btn.refresh_i18n()

    def set_checked(self, tool_name, checked):
        if tool_name in self._buttons:
            self._buttons[tool_name].blockSignals(True)
            self._buttons[tool_name].setChecked(checked)
            self._buttons[tool_name].blockSignals(False)

    def uncheck_all(self):
        for btn in self._buttons.values():
            btn.blockSignals(True)
            btn.setChecked(False)
            btn.blockSignals(False)
