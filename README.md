# 化学学习套件 (Chemistry Suite)

一站式化学学习工作台，集成 2D/3D 分子编辑、公式渲染、电子书阅读、周期表、笔记系统、化学计算器等工具。

## 功能

- **2D 结构编辑器** — 基于 Ketcher，支持 SMILES/InChI/名称输入，PubChem/PDB 导入
- **3D 分子建模器** — 交互式原子搭建，MMFF94/UFF 力场优化，结构检测，测量工具
- **公式编辑器** — KaTeX 实时渲染 LaTeX 化学公式
- **PDF 电子书阅读器** — 选中文字右键自动搜索结构/3D/元素/PubChem
- **交互式周期表** — 118 元素详细数据
- **化学工具集** — 计算器/波谱/MO能级/热力学/点群/晶体/反应机理等 12 个工具
- **笔记系统** — Markdown 笔记，按学科分类，SQLite 存储
- **多语言** — 中文/English/Deutsch/Français
- **面板可分离** — 工具面板可拖到第二屏幕独立使用
- **命令面板** — VS Code 风格 Ctrl+Shift+P 模糊搜索

## 技术栈

PySide6 + RDKit + Ketcher + 3Dmol.js + KaTeX + PDF.js + QWebEngine

## 安装

### 依赖

- Python 3.10+
- Node.js 18+
- RDKit (通过 pip 安装)

### Windows

```bat
setup_windows.bat
```

### Linux

```bash
python3 -m venv ../chemistry-suite-venv
source ../chemistry-suite-venv/bin/activate
pip install -r requirements.txt
npm install
```

## 启动

### Windows

双击 `run.bat` 或终端执行：

```bat
run.bat
```

### Linux

```bash
./run.sh
```

首次启动会自动加载本地 HTTP 服务器 (端口 8766) 供 Web 组件使用。

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+Shift+P | 命令面板 |
| Ctrl+1~6 | 切换学科标签 |
| Ctrl+O | 打开结构文件 |
| Ctrl+P | 打开教材 PDF |
| Ctrl+D | 2D → 3D 推送 |
| Ctrl+G | 获取 SMILES |
| Ctrl+B | 切换笔记面板 |
| F11 | 全屏 |
| Ctrl+Shift+Space | 聚焦 SMILES 输入 |

## 项目结构

```
chemistry-suite/
├── main.py              # 应用入口
├── run.sh / run.bat     # 启动脚本
├── core/                # 后端逻辑 (i18n/计算/导入/笔记)
├── widgets/             # UI 组件 (编辑器/查看器/周期表/笔记)
├── web/                 # 前端资源 (Ketcher/3Dmol/KaTeX/PDF.js)
├── ui/                  # Qt Designer XML
├── data/                # 元素数据
├── books/               # 教材 PDF
└── notes/               # SQLite 笔记
```

## 许可证

MIT
