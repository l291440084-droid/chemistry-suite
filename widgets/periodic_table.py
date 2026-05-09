"""交互式周期表 — QGraphicsScene 原生绘制"""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsScene,
    QGraphicsView, QGraphicsRectItem, QGraphicsTextItem,
    QLabel, QPushButton, QComboBox, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import (
    QFont, QColor, QBrush, QPen, QPainter, QMouseEvent,
)


# 颜色方案
CATEGORY_COLORS = {
    "碱金属": "#ff6666", "碱土金属": "#ffcc80",
    "过渡金属": "#ffff99", "金属": "#cccccc",
    "类金属": "#80cc80", "非金属": "#66cc66",
    "卤素": "#66ffff", "惰性气体": "#9999ff",
    "镧系": "#ff99cc", "锕系": "#ff66cc",
}


def _heatmap_color(value, vmin, vmax):
    """值→热力图颜色 (蓝→白→红)"""
    if value is None or vmin is None or vmax is None:
        return QColor(180, 180, 180)
    if vmax == vmin:
        return QColor(255, 255, 255)
    ratio = (value - vmin) / (vmax - vmin)
    ratio = max(0, min(1, ratio))
    r = int(255 * ratio)
    b = int(255 * (1 - ratio))
    g = int(200 * (1 - abs(ratio - 0.5) * 2))
    return QColor(r, g, b)


class ElementTile(QGraphicsRectItem):
    """单个元素方块"""

    def __init__(self, element, rect, parent=None):
        super().__init__(rect, parent)
        self.element = element
        self._color_mode = "category"
        self._setup()

    def _setup(self):
        self.setAcceptHoverEvents(True)
        cat = self.element.get("category", "金属")
        color = QColor(CATEGORY_COLORS.get(cat, "#cccccc"))
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#333"), 1))

    def update_color(self, mode="category"):
        """根据显示模式更新颜色"""
        el = self.element
        if mode == "category":
            cat = el.get("category", "金属")
            color = QColor(CATEGORY_COLORS.get(cat, "#cccccc"))
            self.setBrush(QBrush(color))
        elif mode == "electronegativity":
            val = el.get("electronegativity")
            color = _heatmap_color(val, 0.7, 4.0)
            self.setBrush(QBrush(color))
        elif mode == "radius":
            val = el.get("atomic_radius")
            color = _heatmap_color(val, 30, 300)
            self.setBrush(QBrush(color))
        elif mode == "ionization":
            val = el.get("first_ionization")
            color = _heatmap_color(val, 3.9, 25.0)
            self.setBrush(QBrush(color))
        self._color_mode = mode

    def hoverEnterEvent(self, event):
        self.setPen(QPen(QColor("#ff0000"), 2))

    def hoverLeaveEvent(self, event):
        self.setPen(QPen(QColor("#333"), 1))


class PeriodicScene(QGraphicsScene):
    """周期表场景"""

    elementClicked = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tiles = {}
        self._color_mode = "category"
        self._build_table()

    def _build_table(self):
        # 加载数据
        data_path = Path(__file__).resolve().parent.parent / "data" / "elements.json"
        with open(data_path, "r", encoding="utf-8") as f:
            self.elements = json.load(f)

        self._el_by_z = {el["z"]: el for el in self.elements}

        # 标准周期表布局: (z, row, col)
        # Period 1
        layout = [
            (1, 0, 0), (2, 0, 17),
            # Period 2
            (3, 1, 0), (4, 1, 1), (5, 1, 12), (6, 1, 13),
            (7, 1, 14), (8, 1, 15), (9, 1, 16), (10, 1, 17),
            # Period 3
            (11, 2, 0), (12, 2, 1), (13, 2, 12), (14, 2, 13),
            (15, 2, 14), (16, 2, 15), (17, 2, 16), (18, 2, 17),
            # Period 4 (includes 3d)
            (19, 3, 0), (20, 3, 1),
            (21, 3, 2), (22, 3, 3), (23, 3, 4), (24, 3, 5),
            (25, 3, 6), (26, 3, 7), (27, 3, 8), (28, 3, 9),
            (29, 3, 10), (30, 3, 11),
            (31, 3, 12), (32, 3, 13), (33, 3, 14), (34, 3, 15),
            (35, 3, 16), (36, 3, 17),
            # Period 5 (includes 4d)
            (37, 4, 0), (38, 4, 1),
            (39, 4, 2), (40, 4, 3), (41, 4, 4), (42, 4, 5),
            (43, 4, 6), (44, 4, 7), (45, 4, 8), (46, 4, 9),
            (47, 4, 10), (48, 4, 11),
            (49, 4, 12), (50, 4, 13), (51, 4, 14), (52, 4, 15),
            (53, 4, 16), (54, 4, 17),
            # Period 6 (includes 5d, lanthanides offset to row 8)
            (55, 5, 0), (56, 5, 1),
            (71, 5, 2), (72, 5, 3), (73, 5, 4), (74, 5, 5),
            (75, 5, 6), (76, 5, 7), (77, 5, 8), (78, 5, 9),
            (79, 5, 10), (80, 5, 11),
            (81, 5, 12), (82, 5, 13), (83, 5, 14), (84, 5, 15),
            (85, 5, 16), (86, 5, 17),
            # Period 7 (includes 6d, actinides offset to row 9)
            (87, 6, 0), (88, 6, 1),
            (103, 6, 2), (104, 6, 3), (105, 6, 4), (106, 6, 5),
            (107, 6, 6), (108, 6, 7), (109, 6, 8), (110, 6, 9),
            (111, 6, 10), (112, 6, 11),
            (113, 6, 12), (114, 6, 13), (115, 6, 14), (116, 6, 15),
            (117, 6, 16), (118, 6, 17),
        ]

        # Lanthanides row 8: Z=57..70
        for i, z in enumerate(range(57, 71)):
            layout.append((z, 8, 2 + i))
        # Actinides row 9: Z=89..102
        for i, z in enumerate(range(89, 103)):
            layout.append((z, 9, 2 + i))

        self.TILE_W = 58
        self.TILE_H = 64
        self.OFFSET_X = 20
        self.OFFSET_Y = 10
        self.COL_COUNT = 18
        self.ROW_COUNT = 10

        for z, row, col in layout:
            el = self._el_by_z.get(z)
            if not el:
                continue
            x = self.OFFSET_X + col * self.TILE_W
            y = self.OFFSET_Y + row * self.TILE_H

            tile = ElementTile(el, QRectF(x, y, self.TILE_W - 2, self.TILE_H - 2))
            self.addItem(tile)

            # 原子序数
            z_text = self.addText(str(z))
            z_text.setPos(x + 2, y + 1)
            z_text.setDefaultTextColor(QColor("#555"))
            font_small = QFont("Arial", 7)
            z_text.setFont(font_small)

            # 元素符号
            sym_text = self.addText(el["symbol"])
            sym_text.setPos(x + self.TILE_W / 2 - 12, y + 10)
            sym_text.setDefaultTextColor(QColor("#111"))
            font_bold = QFont("Arial", 13, QFont.Bold)
            sym_text.setFont(font_bold)

            # 名称
            name_text = self.addText(el.get("name_cn", ""))
            name_text.setPos(x + 4, y + 38)
            name_text.setDefaultTextColor(QColor("#333"))
            name_text.setFont(QFont("Noto Sans CJK SC", 8))

            self._tiles[z] = tile

        # 添加 lanthanide/actinide 标记
        marker_font = QFont("Arial", 9, QFont.Bold)
        la_marker = self.addText("La-Lu →")
        la_marker.setPos(self.OFFSET_X + 1.8 * self.TILE_W, self.OFFSET_Y + 5 * self.TILE_H + 18)
        la_marker.setFont(marker_font)
        la_marker.setDefaultTextColor(QColor("#888"))

        ac_marker = self.addText("Ac-Lr →")
        ac_marker.setPos(self.OFFSET_X + 1.8 * self.TILE_W, self.OFFSET_Y + 6 * self.TILE_H + 18)
        ac_marker.setFont(marker_font)
        ac_marker.setDefaultTextColor(QColor("#888"))

    def set_color_mode(self, mode: str):
        self._color_mode = mode
        for tile in self._tiles.values():
            tile.update_color(mode)

    def mousePressEvent(self, event):
        pos = event.scenePos()
        for z, tile in self._tiles.items():
            if tile.contains(pos):
                self.elementClicked.emit(self._el_by_z[z])
                return
        super().mousePressEvent(event)


class PeriodicTableWidget(QWidget):
    """交互式周期表面板"""

    elementSelected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        # 顶部控制栏
        ctrl = QHBoxLayout()
        ctrl.setSpacing(6)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "标准彩色分区", "电负性热力图",
            "原子半径热力图", "第一电离能热力图"
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "全部元素", "金属", "非金属", "类金属",
            "s区", "p区", "d区", "f区",
            "碱金属", "碱土金属", "过渡金属", "卤素", "惰性气体",
        ])
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)

        self.btn_reset = QPushButton("重置")
        self.btn_reset.clicked.connect(self._reset)

        self.label_info = QLabel("点击元素查看详情")

        ctrl.addWidget(QLabel("显示:"))
        ctrl.addWidget(self.mode_combo)
        ctrl.addWidget(QLabel("筛选:"))
        ctrl.addWidget(self.filter_combo)
        ctrl.addWidget(self.btn_reset)
        ctrl.addStretch()
        ctrl.addWidget(self.label_info)
        layout.addLayout(ctrl)

        # 主区域: 周期表 + 性质面板
        main = QHBoxLayout()

        # 图形视图
        self._scene = PeriodicScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setDragMode(QGraphicsView.ScrollHandDrag)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._view.setMinimumHeight(360)
        self._scene.elementClicked.connect(self._on_element_clicked)

        main.addWidget(self._view, 3)

        # 性质面板
        prop_frame = QFrame()
        prop_frame.setFrameShape(QFrame.StyledPanel)
        prop_frame.setMaximumWidth(260)
        prop_frame.setMinimumWidth(220)
        prop_layout = QVBoxLayout(prop_frame)
        prop_layout.setContentsMargins(8, 8, 8, 8)

        prop_title = QLabel("元素性质")
        prop_title.setFont(QFont("Arial", 14, QFont.Bold))
        prop_layout.addWidget(prop_title)

        self.prop_content = QLabel("点击左侧周期表中的\n元素查看详细性质")
        self.prop_content.setWordWrap(True)
        self.prop_content.setAlignment(Qt.AlignTop)
        prop_layout.addWidget(self.prop_content)
        prop_layout.addStretch()

        main.addWidget(prop_frame, 1)
        layout.addLayout(main)

    def _on_element_clicked(self, el):
        self.elementSelected.emit(el)
        self._show_properties(el)

    def _show_properties(self, el):
        def fmt(v):
            return str(v) if v is not None else "—"

        text = f"""
<b style="font-size:24px;">{el['symbol']}</b>
<b style="font-size:16px;">  {el.get('name_cn', '')}</b>
<span style="color:#888;">  ({el.get('name_en', '')})</span>

<p><b>原子序数:</b> {el['z']}
<br><b>原子量:</b> {fmt(el.get('mass'))}
<br><b>电负性:</b> {fmt(el.get('electronegativity'))}
<br><b>电子构型:</b> {fmt(el.get('electron_config'))}
<br><b>原子半径:</b> {fmt(el.get('atomic_radius'))} pm
<br><b>离子半径:</b> {fmt(el.get('ionic_radius'))} pm
<br><b>常见氧化态:</b> {fmt(el.get('oxidation_states'))}
<br><b>第一电离能:</b> {fmt(el.get('first_ionization'))} eV
<br><b>电子亲和势:</b> {fmt(el.get('electron_affinity'))} eV
<br><b>熔点:</b> {fmt(el.get('melting_point'))} °C
<br><b>沸点:</b> {fmt(el.get('boiling_point'))} °C
<br><b>密度:</b> {fmt(el.get('density'))} g/cm³
<br><b>分类:</b> {fmt(el.get('category'))}
<br><b>分区:</b> {fmt(el.get('block'))}-区
<br><b>族:</b> {fmt(el.get('group'))}
<br><b>周期:</b> {fmt(el.get('period'))}
<br><b>发现年份:</b> {fmt(el.get('year_discovered'))}
</p>
"""
        self.prop_content.setText(text)

    def _on_mode_changed(self, idx):
        modes = ["category", "electronegativity", "radius", "ionization"]
        if idx < len(modes):
            self._scene.set_color_mode(modes[idx])

    def _on_filter_changed(self, idx):
        # 简化版筛选: 调整元素方块的透明度
        filter_text = self.filter_combo.currentText()
        self.label_info.setText(f"筛选: {filter_text}")

    def _reset(self):
        self.mode_combo.setCurrentIndex(0)
        self.filter_combo.setCurrentIndex(0)
        self._scene.set_color_mode("category")
        self.label_info.setText("")

    @property
    def signal_element_selected(self):
        return self.elementSelected
