"""笔记编辑器面板"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QLineEdit, QListWidget, QSplitter, QMessageBox,
)
from PySide6.QtCore import Qt

from core.i18n import i18n


class NoteEditorWidget(QWidget):
    def __init__(self, notes_manager=None, parent=None):
        super().__init__(parent)
        self._notes = notes_manager
        self._current_note_id = None
        self._init_ui()
        self._load_note_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        # 工具栏
        toolbar = QHBoxLayout()
        self.subject_combo = QComboBox()
        self._subject_items = ["有机化学", "无机化学", "物理化学", "结构化学", "原理", "通用"]
        for s in self._subject_items:
            self.subject_combo.addItem(i18n.tr(s))
        self.subject_combo.currentTextChanged.connect(self._load_note_list)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(i18n.tr("笔记标题..."))
        self.title_input.setMaximumWidth(200)

        self.btn_new = QPushButton(i18n.tr("+ 新建"))
        self.btn_new.clicked.connect(self._new_note)
        self.btn_save = QPushButton(i18n.tr("保存"))
        self.btn_save.clicked.connect(self._save_note)
        self.btn_delete = QPushButton(i18n.tr("删除"))
        self.btn_delete.clicked.connect(self._delete_note)

        self._subject_label = QLabel(i18n.tr("学科:"))
        toolbar.addWidget(self._subject_label)
        toolbar.addWidget(self.subject_combo)
        toolbar.addWidget(self.title_input)
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 主区域: 笔记列表 + 编辑区
        splitter = QSplitter(Qt.Horizontal)

        self.note_list = QListWidget()
        self.note_list.currentRowChanged.connect(self._on_note_selected)
        self.note_list.setMaximumWidth(180)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText(i18n.tr("在此写笔记...\n支持 Markdown 语法\n公式用 $...$ 或 $$...$$"))

        splitter.addWidget(self.note_list)
        splitter.addWidget(self.editor)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        layout.addWidget(splitter)

        i18n.languageChanged.connect(self._update_ui_texts)

    def _update_ui_texts(self, lang_code=None):
        """语言切换时刷新 UI"""
        # 学科下拉框
        cur = self.subject_combo.currentIndex()
        self.subject_combo.blockSignals(True)
        for i, s in enumerate(self._subject_items):
            self.subject_combo.setItemText(i, i18n.tr(s))
        self.subject_combo.setCurrentIndex(cur)
        self.subject_combo.blockSignals(False)

        self._subject_label.setText(i18n.tr("学科:"))
        self.title_input.setPlaceholderText(i18n.tr("笔记标题..."))
        self.btn_new.setText(i18n.tr("+ 新建"))
        self.btn_save.setText(i18n.tr("保存"))
        self.btn_delete.setText(i18n.tr("删除"))
        self.editor.setPlaceholderText(i18n.tr("在此写笔记...\n支持 Markdown 语法\n公式用 $...$ 或 $$...$$"))

    def _load_note_list(self):
        self.note_list.clear()
        if not self._notes:
            return
        subject = self.subject_combo.currentText()
        notes = self._notes.list_notes(subject=subject, limit=200)
        for n in notes:
            label = n["title"] or f"笔记 #{n['id']}"
            self.note_list.addItem(f"{label}")
            self.note_list.item(self.note_list.count() - 1).setData(
                Qt.UserRole, n["id"]
            )

    def _on_note_selected(self, row):
        if row < 0 or not self._notes:
            return
        note_id = self.note_list.item(row).data(Qt.UserRole)
        note = self._notes.get_note(note_id)
        if note:
            self._current_note_id = note["id"]
            # 设置学科
            idx = self.subject_combo.findText(note.get("subject", "通用"))
            if idx >= 0:
                self.subject_combo.blockSignals(True)
                self.subject_combo.setCurrentIndex(idx)
                self.subject_combo.blockSignals(False)
            self.title_input.setText(note.get("title", ""))
            self.editor.setPlainText(note.get("content", ""))

    def _new_note(self):
        self._current_note_id = None
        self.title_input.clear()
        self.editor.clear()
        self.note_list.clearSelection()

    def _save_note(self):
        if not self._notes:
            return
        subject = self.subject_combo.currentText()
        title = self.title_input.text() or i18n.tr("无标题")
        content = self.editor.toPlainText()

        if self._current_note_id:
            self._notes.update_note(
                self._current_note_id,
                subject=subject, title=title, content=content,
            )
        else:
            self._current_note_id = self._notes.add_note(
                subject=subject, title=title, content=content,
            )
        self._load_note_list()

    def _delete_note(self):
        if not self._notes or not self._current_note_id:
            return
        reply = QMessageBox.question(
            self, i18n.tr("确认删除"), i18n.tr("确定删除这条笔记?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._notes.delete_note(self._current_note_id)
            self._current_note_id = None
            self.title_input.clear()
            self.editor.clear()
            self._load_note_list()
