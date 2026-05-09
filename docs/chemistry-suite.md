# 化学学习套件 (Chemistry Suite)

## 项目概述

一站式化学学习工作台，集成 2D/3D 分子编辑、公式渲染、电子书阅读、周期表、笔记系统、化学计算器等工具。

**技术栈**: PySide6 + RDKit + Ketcher + 3Dmol.js + KaTeX + PDF.js  
**入口**: `main.py` → `ChemistrySuite(QMainWindow)`  
**启动**: `run.sh` (先启动 HTTP 服务器端口 8766，再启动 Qt)

---

## 设计思路

### 核心设计原则
1. **按需加载**: 工具面板不预加载，首次点击侧栏按钮时才创建 widget，缓存在 `_tool_cache` dict 中复用
2. **面板可分离**: 每个工具面板可脱离主窗口成为独立浮窗（第二屏幕场景），关闭浮窗自动 dock 回
3. **PDF 常驻**: 电子书阅读器始终在右侧可见，方便对照学习
4. **命令面板**: VS Code 风格 Ctrl+Shift+P，模糊搜索所有操作，键盘驱动
5. **快捷键可见**: 菜单项用 `\t` 显示快捷键，降低学习成本

### 架构图
```
ChemistrySuite (QMainWindow)
├── MenuBar (文件/编辑/视图/导航/工具/帮助/语言)
├── CentralWidget (从 main_window.ui 加载)
│   ├── subjectTabWidget (6 学科标签)
│   └── mainArea
│       └── QHBoxLayout
│           ├── Sidebar (54px 固定宽, VS Code 风格)
│           └── QSplitter
│               ├── 工具面板区 (QStackedWidget + 标题栏)
│               │   └── DetachableToolWindow (浮窗模式)
│               └── PDF 阅读器 (常驻右侧)
```

### 数据流
```
Ketcher (JS) ←→ QWebChannel ←→ ChemEditorWidget (Python)
3Dmol.js (JS) ←→ QWebChannel ←→ Mol3DViewerWidget (Python)
PDF.js (JS)  ←→ QWebChannel ←→ PDFReaderWidget (Python)
```

### 通信模式
- Python → JS: `page().runJavaScript("func(args)")`
- JS → Python: QWebChannel bridge signal → Python slot
- 结构数据通过 MOL V2000 格式在 Python ↔ JS 之间传递

---

## 版本历史

### v0.1-v0.2 — 基础框架
- 6 面板网格布局，每个学科 6 个标签
- 嵌入 Ketcher、3Dmol、KaTeX、PDF.js
- 周期表、笔记、计算器、PubChem/PDB 导入
- **问题**: QMainWindow 嵌套导致白屏

### v0.3 — 交互增强
- **修复白屏**: `.ui` 根改为 QWidget，`setCentralWidget(central)` 解决 QMainWindow 嵌套
- VS Code 风格命令面板 Ctrl+Shift+P
- 菜单项显示快捷键

### v0.4 — 架构重构
- **左侧工具栏**: VS Code 风格 Sidebar，图标+文字，可切换的工具面板
- **懒加载**: `_tool_cache` dict，首次访问创建，后续复用
- **分离面板**: `DetachableToolWindow(QMainWindow)`，关闭自动 dock 回
- **PDF 常驻右侧**: QSplitter 布局
- 30+ 命令注册表供命令面板搜索

### v0.5 — 3D 建模器重做
- 交互式原子搭建 (点击 3D 位置放置原子)
- MMFF94/UFF 力场优化
- 结构稳定性检测 (键长、近接触)
- 测量工具 (距离/角度)
- 片段库 (10 种常用官能团)
- 加氢/去氢
- 导入导出 (MOL/PDB/XYZ)
- 15 种常用元素 CPK 色按钮

### v0.6 — 多语言 (当前)
- 4 语言: 中文/English/Deutsch/Français
- I18nManager 单例, signal 驱动
- QSettings 持久化语言偏好
- 200+ 翻译条目

---

## 关键设计决策

### 为什么用 QWebEngineView 而非原生 Qt 组件？
Ketcher 和 3Dmol.js 是成熟的 Web 化学组件，功能远超 Qt 原生方案。通过 QWebChannel 建立双向通信，体验接近原生。

### 为什么 MOL V2000 格式作为数据交换格式？
MOL 是化学信息学标准格式，RDKit 原生支持，可完整保留原子坐标、键级、手性等信息。SMILES 丢失 3D 坐标，JSON 无统一标准。

### 为什么分离窗口用"关闭=Dock回"而非真关闭？
教学场景：学生临时把面板拖到第二屏幕，用完想放回去。如果用真关闭，需重新打开+加载，体验差。"关闭即 Dock"让操作可逆。

### 为什么语言切换用 Signal 而非直接刷新？
Signal 解耦 — I18nManager 不感知有哪些 widget，widget 各自连接信号自行刷新。新增 widget 只需连接信号即可，无需修改 I18nManager。

### 为什么右侧栏按钮"再次点击已分离面板"是聚焦而非 Dock？
v0.4 最初行为是 dock 回，但用户场景是：面板已拖到第二屏幕，在侧栏再点一次是想要关注那个面板，不是想让面板回来。改为聚焦浮窗。

---

## 文件结构

```
chemistry-suite/
├── main.py               # 应用入口, ChemistrySuite, CommandPalette, DetachableToolWindow
├── run.sh                # 启动脚本
├── ui/
│   └── main_window.ui    # Qt Designer XML (学科标签 + 主区域)
├── widgets/
│   ├── sidebar.py        # 左侧工具栏 (Sidebar + SidebarButton)
│   ├── chem_editor.py    # 2D 结构编辑器 (Ketcher 封装)
│   ├── mol3d_viewer.py   # 3D 分子建模器 (3Dmol.js 封装)
│   ├── katex_renderer.py # KaTeX 公式编辑器
│   ├── pdf_reader.py     # PDF.js 电子书阅读器
│   ├── periodic_table.py # 交互式周期表 (QGraphicsScene)
│   ├── note_editor.py    # Markdown 笔记
│   ├── calculator_panel.py # 化学计算器
│   └── tools_stubs.py    # 12 个占位工具面板
├── core/
│   ├── i18n.py           # 多语言管理器 (I18nManager 单例)
│   ├── mol3d_utils.py    # RDKit 3D 工具 (优化/能量/检测/测量)
│   ├── notes_manager.py  # SQLite 笔记 CRUD
│   ├── importers.py      # PubChem/PDB/文件导入
│   └── calculator.py     # 化学计算 (分子量/溶液/pH/产率)
├── web/
│   ├── ketcher/          # Ketcher 2D 编辑器 (JS)
│   ├── 3dmol/            # 3Dmol.js 查看器 + 自主搭建
│   ├── katex/            # KaTeX 公式渲染
│   └── pdfjs/            # PDF.js 阅读器
├── data/
│   └── elements.json     # 118 元素数据
├── books/                # 教材 PDF 存放
├── notes/                # SQLite 笔记数据库
└── docs/
    ├── INDEX.md          # 项目日志库索引
    └── chemistry-suite.md # 本文件
```

---

## 已知问题 & 注意事项

### RDKit 相关
1. **`Chem.MolFromMolBlock` 默认去除 H**: 必须传 `removeHs=False` 保留显式氢，否则加氢/优化结果错误
2. **SMILES 无 conformer**: `mol.GetConformer()` 对 SMILES 输入会抛异常，需 try/except 并用 `EmbedMolecule` 生成 3D 坐标
3. **能量异常大 (9e7 kcal/mol)**: 通常是 Hs 丢失+无 3D 坐标导致，排查 `removeHs` 和 `Is3D()`
4. **MMFF94 不覆盖所有元素**: 对金属等用 UFF 回退

### Qt/PySide6 相关
1. **QMainWindow 不能嵌套**: `.ui` 文件根元素必须是 QWidget，用 `setCentralWidget` 挂载
2. **Fusion 风格无动画**: 不要用 CSS `animation`/`transition` 属性
3. **QWebEngineView 需 HTTP 服务器**: 本地文件 `file://` 不支持 QWebChannel，必须用 `http://127.0.0.1:8766`
4. **侧栏按钮状态管理**: `_close_tool()` 调用 `uncheck_all()` 后需在 `_open_tool()` 中 `set_checked(key, True)` 恢复

### 3Dmol.js 相关
1. **点击 3D 坐标计算**: 使用射线-平面求交，需要相机位置和方向信息
2. **MOL 格式 padding**: V2000 格式字段有严格位置要求，JS 端需精确构建
3. **自动成键阈值**: 共价半径之和 × 1.15~1.2，过敏感/过迟钝都会导致错误成键

### i18n 相关
1. **翻译 key 是中文原文**: 好处是中文无需翻译直接显示，坏处是改中文原文会破坏翻译查找
2. **动态消息**: 含变量的消息（f-string）需在调用处手动 `i18n.tr()` 模板部分
3. **QSettings 持久化**: 语言偏好存储在 `~/.config/ChemistrySuite/ChemistrySuite.conf`

---

## 未来计划

- [ ] 波谱模拟器功能实现 (¹H/¹³C NMR, IR, MS)
- [ ] 反应机理动画 (Arrows.js)
- [ ] IUPAC 命名训练器
- [ ] 晶体结构浏览器 (CIF 导入)
- [ ] MO 能级图交互
- [ ] 导入格式扩展 (CIF, MOL2, Gaussian 输出)
- [ ] 分子动力学简单模拟
- [ ] 插件系统
- [ ] 单元测试覆盖
