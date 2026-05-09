"""多语言翻译管理器 — signal 驱动，所有界面自动响应语言切换"""

import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QSettings

LANGUAGES = {
    "zh": "中文",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
}

# ── 翻译字典 ────────────────────────────────────────────────────
# key = 中文原文, value = {"en": ..., "de": ..., "fr": ...}
TRANSLATIONS = {
    # ── 应用 ──
    "化学学习套件": {"en": "Chemistry Suite", "de": "Chemie-Suite", "fr": "Suite Chimique"},
    "就绪": {"en": "Ready", "de": "Bereit", "fr": "Prêt"},
    "已终止": {"en": "Terminated", "de": "Beendet", "fr": "Terminé"},

    # ── 菜单栏 ──
    "文件(&F)": {"en": "&File", "de": "&Datei", "fr": "&Fichier"},
    "编辑(&E)": {"en": "&Edit", "de": "&Bearbeiten", "fr": "&Édition"},
    "视图(&V)": {"en": "&View", "de": "&Ansicht", "fr": "&Affichage"},
    "导航(&N)": {"en": "&Navigate", "de": "&Navigation", "fr": "&Navigation"},
    "工具(&T)": {"en": "&Tools", "de": "&Werkzeuge", "fr": "&Outils"},
    "帮助(&H)": {"en": "&Help", "de": "&Hilfe", "fr": "&Aide"},
    "语言(&L)": {"en": "&Language", "de": "&Sprache", "fr": "&Langue"},

    # ── 文件菜单 ──
    "打开结构文件...": {"en": "Open Structure File...", "de": "Strukturdatei öffnen...", "fr": "Ouvrir un fichier de structure..."},
    "导入教材 PDF...": {"en": "Import Textbook PDF...", "de": "Lehrbuch-PDF importieren...", "fr": "Importer un PDF..."},
    "从 PubChem 导入...": {"en": "Import from PubChem...", "de": "Von PubChem importieren...", "fr": "Importer depuis PubChem..."},
    "从 PDB 导入...": {"en": "Import from PDB...", "de": "Von PDB importieren...", "fr": "Importer depuis PDB..."},
    "退出": {"en": "Exit", "de": "Beenden", "fr": "Quitter"},

    # ── 编辑菜单 ──
    "获取 SMILES": {"en": "Get SMILES", "de": "SMILES abrufen", "fr": "Obtenir SMILES"},
    "2D → 3D 推送": {"en": "2D → 3D Push", "de": "2D → 3D übertragen", "fr": "Pousser 2D → 3D"},

    # ── 视图菜单 ──
    "分离当前面板": {"en": "Detach Panel", "de": "Panel abdocken", "fr": "Détacher le panneau"},
    "Dock 回主窗口": {"en": "Dock Back", "de": "Andocken", "fr": "Réancrer"},
    "切换笔记面板": {"en": "Toggle Notes", "de": "Notizen umschalten", "fr": "Basculer les notes"},
    "全屏": {"en": "Fullscreen", "de": "Vollbild", "fr": "Plein écran"},

    # ── 导航 ──
    "有机化学": {"en": "Organic Chemistry", "de": "Organische Chemie", "fr": "Chimie Organique"},
    "无机化学": {"en": "Inorganic Chemistry", "de": "Anorganische Chemie", "fr": "Chimie Inorganique"},
    "物理化学": {"en": "Physical Chemistry", "de": "Physikalische Chemie", "fr": "Chimie Physique"},
    "结构化学": {"en": "Structural Chemistry", "de": "Strukturchemie", "fr": "Chimie Structurale"},
    "原理": {"en": "Principles", "de": "Prinzipien", "fr": "Principes"},
    "全部工具": {"en": "All Tools", "de": "Alle Werkzeuge", "fr": "Tous les Outils"},

    # ── 工具菜单 ──
    "化学计算器": {"en": "Chemical Calculator", "de": "Chemischer Rechner", "fr": "Calculateur Chimique"},
    "波谱模拟器": {"en": "Spectroscopy Simulator", "de": "Spektroskopie-Simulator", "fr": "Simulateur de Spectroscopie"},
    "点群分析器": {"en": "Point Group Analyzer", "de": "Punktgruppen-Analysator", "fr": "Analyseur de Groupe Ponctuel"},
    "MO 能级图": {"en": "MO Energy Diagram", "de": "MO-Energiediagramm", "fr": "Diagramme d'Énergie OM"},
    "热力学循环搭建器": {"en": "Thermo Cycle Builder", "de": "Thermodynamik-Zyklus", "fr": "Constructeur de Cycle Thermo"},
    "晶体结构浏览器": {"en": "Crystal Structure Browser", "de": "Kristallstruktur-Browser", "fr": "Navigateur de Structure Cristalline"},
    "反应机理动画": {"en": "Reaction Mechanism", "de": "Reaktionsmechanismus", "fr": "Mécanisme Réactionnel"},
    "IUPAC 命名训练器": {"en": "IUPAC Naming Trainer", "de": "IUPAC-Nomenklatur-Trainer", "fr": "Entraîneur de Nomenclature IUPAC"},
    "相图分析器": {"en": "Phase Diagram Analyzer", "de": "Phasendiagramm-Analysator", "fr": "Analyseur de Diagramme de Phase"},
    "酸碱滴定模拟器": {"en": "Acid-Base Titration", "de": "Säure-Base-Titration", "fr": "Titrage Acide-Base"},
    "量子化学可视化": {"en": "Quantum Chemistry Viz", "de": "Quantenchemie-Visualisierung", "fr": "Visualisation de Chimie Quantique"},
    "光谱参考表": {"en": "Spectral Reference", "de": "Spektralreferenz", "fr": "Référence Spectrale"},

    # ── 帮助 ──
    "使用说明": {"en": "User Guide", "de": "Benutzerhandbuch", "fr": "Guide d'Utilisation"},
    "关于...": {"en": "About...", "de": "Über...", "fr": "À propos..."},

    # ── 侧栏 ──
    "结构": {"en": "Structure", "de": "Struktur", "fr": "Structure"},
    "3D": {"en": "3D", "de": "3D", "fr": "3D"},
    "公式": {"en": "Formula", "de": "Formel", "fr": "Formule"},
    "周期表": {"en": "Periodic", "de": "Perioden", "fr": "Périodique"},
    "工具": {"en": "Tools", "de": "Werkzeuge", "fr": "Outils"},
    "笔记": {"en": "Notes", "de": "Notizen", "fr": "Notes"},

    # ── 3D 建模器 ──
    "搭建": {"en": "Build", "de": "Bauen", "fr": "Construire"},
    "选择": {"en": "Select", "de": "Auswählen", "fr": "Sélectionner"},
    "删除": {"en": "Delete", "de": "Löschen", "fr": "Supprimer"},
    "测量": {"en": "Measure", "de": "Messen", "fr": "Mesurer"},
    "元素:": {"en": "Elem:", "de": "Elem:", "fr": "Élém:"},
    "显示:": {"en": "Style:", "de": "Stil:", "fr": "Style:"},
    "优化": {"en": "Optimize", "de": "Optimieren", "fr": "Optimiser"},
    "检测": {"en": "Check", "de": "Prüfen", "fr": "Vérifier"},
    "导入": {"en": "Import", "de": "Importieren", "fr": "Importer"},
    "导出 ▼": {"en": "Export ▼", "de": "Exportieren ▼", "fr": "Exporter ▼"},
    "片段库 ▼": {"en": "Fragments ▼", "de": "Fragmente ▼", "fr": "Fragments ▼"},
    "清除": {"en": "Clear", "de": "Löschen", "fr": "Effacer"},

    "球棍": {"en": "Ball&Stick", "de": "Kugel&Stab", "fr": "Boule&Bâton"},
    "棍状": {"en": "Stick", "de": "Stab", "fr": "Bâton"},
    "空间填充": {"en": "Spheres", "de": "Kugeln", "fr": "Sphères"},
    "线框": {"en": "Wireframe", "de": "Drahtgitter", "fr": "Filaire"},

    "选中原子": {"en": "Selected Atom", "de": "Ausgewähltes Atom", "fr": "Atome Sélectionné"},
    "能量 / 稳定性": {"en": "Energy / Stability", "de": "Energie / Stabilität", "fr": "Énergie / Stabilité"},
    "结构问题": {"en": "Structure Issues", "de": "Strukturprobleme", "fr": "Problèmes de Structure"},
    "测量结果": {"en": "Measurement", "de": "Messung", "fr": "Mesure"},
    "结构统计": {"en": "Statistics", "de": "Statistik", "fr": "Statistiques"},

    # ── 状态消息 ──
    "就绪 — Ctrl+Shift+P 命令面板 | 左侧工具栏 | 面板可分离": {
        "en": "Ready — Ctrl+Shift+P Command Palette | Sidebar | Detachable Panels",
        "de": "Bereit — Ctrl+Shift+P Befehlspalette | Seitenleiste | Abdockbare Panels",
        "fr": "Prêt — Ctrl+Shift+P Palette de Commandes | Barre Latérale | Panneaux Détachables",
    },
    "当前学科: ": {"en": "Subject: ", "de": "Fach: ", "fr": "Matière: "},
    "已聚焦: ": {"en": "Focused: ", "de": "Fokussiert: ", "fr": "Focus: "},
    "已分离: ": {"en": "Detached: ", "de": "Abgedockt: ", "fr": "Détaché: "},
    "Dock 完成": {"en": "Docked", "de": "Angedockt", "fr": "Réancré"},
    "没有已分离的面板": {"en": "No detached panels", "de": "Keine abgedockten Panels", "fr": "Aucun panneau détaché"},
    "已添加到笔记: ": {"en": "Added to notes: ", "de": "Zu Notizen hinzugefügt: ", "fr": "Ajouté aux notes: "},
    "画布已清除": {"en": "Canvas cleared", "de": "Leinwand gelöscht", "fr": "Toile effacée"},
    "3D 建模器就绪 — 点击「搭建」开始放置原子": {
        "en": "3D Modeler ready — Click 'Build' to place atoms",
        "de": "3D-Modellierer bereit — 'Bauen' klicken zum Platzieren",
        "fr": "Modeleur 3D prêt — Cliquez 'Construire' pour placer des atomes",
    },

    # ── PDF 阅读器 ──
    "PDF 阅读器": {"en": "PDF Reader", "de": "PDF-Leser", "fr": "Lecteur PDF"},
    "PDF 阅读器就绪": {"en": "PDF Reader Ready", "de": "PDF-Leser bereit", "fr": "Lecteur PDF prêt"},

    # ── 对话框 ──
    "关于 化学学习套件": {"en": "About Chemistry Suite", "de": "Über Chemie-Suite", "fr": "À propos de Suite Chimique"},
    "导入错误": {"en": "Import Error", "de": "Importfehler", "fr": "Erreur d'Importation"},
    "PubChem 导入失败": {"en": "PubChem Import Failed", "de": "PubChem-Import fehlgeschlagen", "fr": "Échec de l'Importation PubChem"},
    "PDB 导入失败": {"en": "PDB Import Failed", "de": "PDB-Import fehlgeschlagen", "fr": "Échec de l'Importation PDB"},
    "PubChem 搜索失败": {"en": "PubChem Search Failed", "de": "PubChem-Suche fehlgeschlagen", "fr": "Échec de la Recherche PubChem"},
    "导入失败": {"en": "Import Failed", "de": "Import fehlgeschlagen", "fr": "Échec de l'Importation"},
    "导出失败": {"en": "Export Failed", "de": "Export fehlgeschlagen", "fr": "Échec de l'Exportation"},
    "无法解析": {"en": "Parse Error", "de": "Parse-Fehler", "fr": "Erreur d'Analyse"},
    "确认删除": {"en": "Confirm Delete", "de": "Löschen bestätigen", "fr": "Confirmer la Suppression"},
    "确定删除这条笔记?": {"en": "Delete this note?", "de": "Diese Notiz löschen?", "fr": "Supprimer cette note?"},

    # ── PDF 右键菜单 ──
    "在结构编辑器中打开": {"en": "Open in Structure Editor", "de": "Im Struktureditor öffnen", "fr": "Ouvrir dans l'Éditeur"},
    "查看 3D 结构": {"en": "View 3D Structure", "de": "3D-Struktur anzeigen", "fr": "Voir la Structure 3D"},
    "查询原子量/元素": {"en": "Query Atomic Weight", "de": "Atomgewicht abfragen", "fr": "Rechercher Masse Atomique"},
    "从 PubChem 搜索": {"en": "Search PubChem", "de": "PubChem durchsuchen", "fr": "Rechercher sur PubChem"},
    "添加到笔记": {"en": "Add to Notes", "de": "Zu Notizen hinzufügen", "fr": "Ajouter aux Notes"},
    "更多": {"en": "More", "de": "Mehr", "fr": "Plus"},
    "波谱模拟": {"en": "Spectroscopy", "de": "Spektroskopie", "fr": "Spectroscopie"},
    "IUPAC 命名": {"en": "IUPAC Naming", "de": "IUPAC-Nomenklatur", "fr": "Nomenclature IUPAC"},
    "热力学数据": {"en": "Thermo Data", "de": "Thermodynamik-Daten", "fr": "Données Thermo"},
    "晶体结构查询": {"en": "Crystal Query", "de": "Kristallabfrage", "fr": "Recherche Cristalline"},

    # ── 导入对话框 ──
    "打开结构文件": {"en": "Open Structure File", "de": "Strukturdatei öffnen", "fr": "Ouvrir un Fichier"},
    "导入教材 PDF": {"en": "Import Textbook PDF", "de": "Lehrbuch-PDF importieren", "fr": "Importer un PDF"},
    "输入化合物名称(中/英文)、SMILES、InChI 或 PubChem CID:": {
        "en": "Enter compound name, SMILES, InChI, or PubChem CID:",
        "de": "Name, SMILES, InChI oder PubChem CID eingeben:",
        "fr": "Nom, SMILES, InChI ou PubChem CID:",
    },
    "输入 PDB ID (4位字符，如 1MOL、4HHB):": {
        "en": "Enter PDB ID (4 chars, e.g. 1MOL, 4HHB):",
        "de": "PDB-ID eingeben (4 Zeichen, z.B. 1MOL, 4HHB):",
        "fr": "ID PDB (4 caractères, ex: 1MOL, 4HHB):",
    },
    "化学结构文件 (*.mol *.sdf *.pdb *.cif *.xyz *.smi *.smiles);;所有文件 (*)": {
        "en": "Structure files (*.mol *.sdf *.pdb *.cif *.xyz *.smi *.smiles);;All files (*)",
        "de": "Strukturdateien (*.mol *.sdf *.pdb *.cif *.xyz *.smi *.smiles);;Alle Dateien (*)",
        "fr": "Fichiers de structure (*.mol *.sdf *.pdb *.cif *.xyz *.smi *.smiles);;Tous (*)",
    },
    "PDF 文件 (*.pdf);;所有文件 (*)": {
        "en": "PDF files (*.pdf);;All files (*)",
        "de": "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        "fr": "Fichiers PDF (*.pdf);;Tous (*)",
    },
    "化学结构 (*.mol *.sdf *.pdb *.xyz *.smi);;所有文件 (*)": {
        "en": "Structure files (*.mol *.sdf *.pdb *.xyz *.smi);;All files (*)",
        "de": "Strukturdateien (*.mol *.sdf *.pdb *.xyz *.smi);;Alle Dateien (*)",
        "fr": "Fichiers (*.mol *.sdf *.pdb *.xyz *.smi);;Tous (*)",
    },

    # ── 状态消息 (杂项) ──
    "已加载 SMILES: ": {"en": "Loaded SMILES: ", "de": "SMILES geladen: ", "fr": "SMILES chargé: "},
    "已加载 Molfile": {"en": "Molfile loaded", "de": "Molfile geladen", "fr": "Molfile chargé"},
    "已加载 PDB": {"en": "PDB loaded", "de": "PDB geladen", "fr": "PDB chargé"},
    "已添加教材: ": {"en": "Added textbook: ", "de": "Lehrbuch hinzugefügt: ", "fr": "Manuel ajouté: "},
    "导入书籍": {"en": "Import Books", "de": "Bücher importieren", "fr": "Importer des livres"},
    "导入书籍 — 可多选 PDF": {"en": "Import Books - multi-select", "de": "Bücher importieren - Mehrfachauswahl", "fr": "Importer des livres - sélection multiple"},
    "本教材已导入": {"en": " textbook(s) imported", "de": " Lehrbücher importiert", "fr": " manuels importés"},
    "教材已存在，无需重复导入": {"en": "Textbooks already exist", "de": "Lehrbücher bereits vorhanden", "fr": "Manuels déjà existants"},
    "复制": {"en": "Copy", "de": "Kopieren", "fr": "Copier"},
    "剪切": {"en": "Cut", "de": "Ausschneiden", "fr": "Couper"},
    "粘贴": {"en": "Paste", "de": "Einfügen", "fr": "Coller"},
    "全选": {"en": "Select All", "de": "Alles auswählen", "fr": "Tout sélectionner"},
    "页": {"en": "pages", "de": "Seiten", "fr": "pages"},
    "上一页": {"en": "Previous Page", "de": "Vorherige Seite", "fr": "Page précédente"},
    "下一页": {"en": "Next Page", "de": "Nächste Seite", "fr": "Page suivante"},
    "页码": {"en": "Page Number", "de": "Seitenzahl", "fr": "Numéro de page"},
    "搜索...": {"en": "Search...", "de": "Suchen...", "fr": "Rechercher..."},
    "查找": {"en": "Find", "de": "Finden", "fr": "Chercher"},
    "适应宽度": {"en": "Fit Width", "de": "Breite anpassen", "fr": "Ajuster largeur"},
    "适应页面": {"en": "Fit Page", "de": "Seite anpassen", "fr": "Ajuster page"},
    "筛选...": {"en": "Filter...", "de": "Filtern...", "fr": "Filtrer..."},
    "教材": {"en": "Textbooks", "de": "Lehrbücher", "fr": "Manuels"},
    "书签": {"en": "Bookmarks", "de": "Lesezeichen", "fr": "Signets"},
    "在系统查看器中打开": {"en": "Open in System Viewer", "de": "In System-Viewer öffnen", "fr": "Ouvrir dans la visionneuse"},
    "在阅读器中打开": {"en": "Open in Reader", "de": "Im Reader öffnen", "fr": "Ouvrir dans le lecteur"},
    "删除书签": {"en": "Delete Bookmark", "de": "Lesezeichen löschen", "fr": "Supprimer le signet"},
    "点击跳转": {"en": "Click to Jump", "de": "Zum Springen klicken", "fr": "Cliquer pour aller"},
    "已复制": {"en": "Copied", "de": "Kopiert", "fr": "Copié"},
    "已剪切": {"en": "Cut", "de": "Ausgeschnitten", "fr": "Coupé"},
    "复制\tCtrl+C": {"en": "Copy\tCtrl+C", "de": "Kopieren\tCtrl+C", "fr": "Copier\tCtrl+C"},
    "剪切\tCtrl+X": {"en": "Cut\tCtrl+X", "de": "Ausschneiden\tCtrl+X", "fr": "Couper\tCtrl+X"},
    "粘贴\tCtrl+V": {"en": "Paste\tCtrl+V", "de": "Einfügen\tCtrl+V", "fr": "Coller\tCtrl+V"},
    "全选\tCtrl+A": {"en": "Select All\tCtrl+A", "de": "Alles auswählen\tCtrl+A", "fr": "Tout sélectionner\tCtrl+A"},
    "PubChem: ": {"en": "PubChem: ", "de": "PubChem: ", "fr": "PubChem: "},
    "PDB: ": {"en": "PDB: ", "de": "PDB: ", "fr": "PDB: "},
    " 已加载": {"en": " loaded", "de": " geladen", "fr": " chargé"},
    "拖放加载: ": {"en": "Drop loaded: ", "de": "Ablage geladen: ", "fr": "Glissé chargé: "},
    "拖放添加教材: ": {"en": "Drop textbook: ", "de": "Lehrbuch abgelegt: ", "fr": "Manuel déposé: "},
    "SMILES: ": {"en": "SMILES: ", "de": "SMILES: ", "fr": "SMILES: "},
    "已导出: ": {"en": "Exported: ", "de": "Exportiert: ", "fr": "Exporté: "},
    "已导入: ": {"en": "Imported: ", "de": "Importiert: ", "fr": "Importé: "},
    "优化完成 — 能量: ": {"en": "Optimized — Energy: ", "de": "Optimiert — Energie: ", "fr": "Optimisé — Énergie: "},
    "优化失败: ": {"en": "Optimization failed: ", "de": "Optimierung fehlgeschlagen: ", "fr": "Échec de l'Optimisation: "},
    "已加氢": {"en": "H added", "de": "H hinzugefügt", "fr": "H ajoutés"},
    "加氢失败: ": {"en": "Add H failed: ", "de": "H hinzufügen fehlgeschlagen: ", "fr": "Échec ajout H: "},
    "已去氢": {"en": "H removed", "de": "H entfernt", "fr": "H retirés"},
    "去氢失败: ": {"en": "Remove H failed: ", "de": "H entfernen fehlgeschlagen: ", "fr": "Échec retrait H: "},
    "3D 建模器就绪": {"en": "3D Modeler Ready", "de": "3D-Modellierer bereit", "fr": "Modeleur 3D prêt"},
    "空白画布": {"en": "Empty canvas", "de": "Leere Leinwand", "fr": "Toile vide"},
    "尚未计算": {"en": "Not calculated", "de": "Nicht berechnet", "fr": "Non calculé"},
    "选择测量模式，点击两个原子": {
        "en": "Select measure mode, click two atoms",
        "de": "Messmodus wählen, zwei Atome klicken",
        "fr": "Mode mesure, cliquez deux atomes",
    },
    "点击原子查看信息": {
        "en": "Click atom for info",
        "de": "Atom für Info anklicken",
        "fr": "Cliquez un atome pour info",
    },
    "点击「检测」分析结构": {
        "en": "Click 'Check' to analyze",
        "de": "'Prüfen' klicken zum Analysieren",
        "fr": "Cliquez 'Vérifier' pour analyser",
    },
    "正在优化...": {"en": "Optimizing...", "de": "Optimieren...", "fr": "Optimisation..."},
    "当前元素: ": {"en": "Element: ", "de": "Element: ", "fr": "Élément: "},
    "2D → 3D: ": {"en": "2D → 3D: ", "de": "2D → 3D: ", "fr": "2D → 3D: "},
    "已获取 SMILES": {"en": "SMILES retrieved", "de": "SMILES abgerufen", "fr": "SMILES récupéré"},
    "已填入输入栏: ": {"en": "Filled input: ", "de": "Eingabe gefüllt: ", "fr": "Saisi: "},
    "，请手动确认": {"en": ", confirm manually", "de": ", manuell bestätigen", "fr": ", confirmer manuellement"},
    "3D 加载失败: ": {"en": "3D load failed: ", "de": "3D-Laden fehlgeschlagen: ", "fr": "Échec chargement 3D: "},
    "无法自动解析 ": {"en": "Cannot parse: ", "de": "Kann nicht parsen: ", "fr": "Analyse impossible: "},
    "已加载: ": {"en": "Loaded: ", "de": "Geladen: ", "fr": "Chargé: "},
    "Ketcher 就绪": {"en": "Ketcher Ready", "de": "Ketcher bereit", "fr": "Ketcher prêt"},
    "Ketcher 加载失败": {"en": "Ketcher Load Failed", "de": "Ketcher Laden fehlgeschlagen", "fr": "Échec chargement Ketcher"},

    # ── 命令面板 ──
    "命令面板": {"en": "Command Palette", "de": "Befehlspalette", "fr": "Palette de Commandes"},
    "搜索命令... (如: 3D, PubChem, 全屏, 分离)": {
        "en": "Search commands... (e.g. 3D, PubChem, fullscreen)",
        "de": "Befehle suchen... (z.B. 3D, PubChem, Vollbild)",
        "fr": "Rechercher... (ex: 3D, PubChem, plein écran)",
    },
    "↑↓ 选择  Enter 执行  Esc 关闭  输入关键词搜索": {
        "en": "↑↓ Select  Enter Run  Esc Close  Type to search",
        "de": "↑↓ Wählen  Enter Ausführen  Esc Schließen",
        "fr": "↑↓ Sélectionner  Enter Exécuter  Esc Fermer",
    },

    # ── 命令分类 ──
    "文件": {"en": "File", "de": "Datei", "fr": "Fichier"},
    "编辑": {"en": "Edit", "de": "Bearbeiten", "fr": "Édition"},
    "视图": {"en": "View", "de": "Ansicht", "fr": "Affichage"},
    "导航": {"en": "Navigate", "de": "Navigation", "fr": "Navigation"},
    "帮助": {"en": "Help", "de": "Hilfe", "fr": "Aide"},

    # ── 各种状态 ──
    "加载失败": {"en": "Load failed", "de": "Laden fehlgeschlagen", "fr": "Échec du chargement"},
    "无法解析结构": {"en": "Cannot parse structure", "de": "Struktur nicht parsebar", "fr": "Structure non analysable"},
    "力场初始化失败": {"en": "Force field init failed", "de": "Kraftfeld-Init fehlgeschlagen", "fr": "Échec init champ de force"},
    "无法初始化力场 (MMFF94/UFF 均失败)": {
        "en": "Force field unavailable (MMFF94/UFF)",
        "de": "Kraftfeld nicht verfügbar (MMFF94/UFF)",
        "fr": "Champ de force indisponible (MMFF94/UFF)",
    },
    "3D 坐标生成失败": {"en": "3D coordinate generation failed", "de": "3D-Koordinaten fehlgeschlagen", "fr": "Échec génération 3D"},
    "无效 SMILES: ": {"en": "Invalid SMILES: ", "de": "Ungültiges SMILES: ", "fr": "SMILES invalide: "},
    "PDB 解析失败": {"en": "PDB parse failed", "de": "PDB-Parse fehlgeschlagen", "fr": "Échec analyse PDB"},
    "原子位置重叠": {"en": "Atom position overlap", "de": "Atomposition überlappend", "fr": "Positions d'atomes superposées"},

    # ── 结构问题 ──
    " 过长 (": {"en": " too long (", "de": " zu lang (", "fr": " trop long ("},
    " 过短 (": {"en": " too short (", "de": " zu kurz (", "fr": " trop court ("},
    " 过近 (": {"en": " too close (", "de": " zu nah (", "fr": " trop proche ("},
    " Å)": {"en": " Å)", "de": " Å)", "fr": " Å)"},
    "键 ": {"en": "Bond ", "de": "Bindung ", "fr": "Liaison "},
    "结构正常，无明显问题": {"en": "Structure OK, no issues", "de": "Struktur OK, keine Probleme", "fr": "Structure OK, aucun problème"},

    # ── 笔记 ──
    "来自电子书: ": {"en": "From eBook: ", "de": "Aus E-Book: ", "fr": "Du livre: "},
    "无标题": {"en": "Untitled", "de": "Ohne Titel", "fr": "Sans titre"},
    "笔记标题...": {"en": "Note title...", "de": "Notiztitel...", "fr": "Titre de la note..."},
    "在此写笔记...\n支持 Markdown 语法\n公式用 $...$ 或 $$...$$": {
        "en": "Write notes here...\nMarkdown supported\nFormulas with $...$ or $$...$$",
        "de": "Notizen hier...\nMarkdown unterstützt\nFormeln mit $...$ oder $$...$$",
        "fr": "Écrire ici...\nMarkdown supporté\nFormules avec $...$ ou $$...$$",
    },
    "学科:": {"en": "Subject:", "de": "Fach:", "fr": "Matière:"},
    "+ 新建": {"en": "+ New", "de": "+ Neu", "fr": "+ Nouveau"},
    "保存": {"en": "Save", "de": "Speichern", "fr": "Enregistrer"},
    "通用": {"en": "General", "de": "Allgemein", "fr": "Général"},
    "笔记面板 (点击展开)": {"en": "Notes (click to expand)", "de": "Notizen (zum Ausklappen)", "fr": "Notes (cliquer pour agrandir)"},

    # ── 计算器 ──
    "化学计算器": {"en": "Chemical Calculator", "de": "Chemischer Rechner", "fr": "Calculateur Chimique"},
    "分子量/元素分析": {"en": "MW/Elemental Analysis", "de": "MW/Elementaranalyse", "fr": "Masse Molaire/Analyse"},
    "溶液配制": {"en": "Solution Prep", "de": "Lösungszubereitung", "fr": "Préparation Solution"},
    "pH 计算": {"en": "pH Calc", "de": "pH-Berechnung", "fr": "Calcul pH"},
    "产率/稀释": {"en": "Yield/Dilution", "de": "Ausbeute/Verdünnung", "fr": "Rendement/Dilution"},
    "SMILES (如 CCO) 或 分子式": {"en": "SMILES (e.g. CCO) or formula", "de": "SMILES (z.B. CCO) oder Formel", "fr": "SMILES (ex: CCO) ou formule"},
    "计算": {"en": "Calculate", "de": "Berechnen", "fr": "Calculer"},
    "质量 (g):": {"en": "Mass (g):", "de": "Masse (g):", "fr": "Masse (g):"},
    "体积 (L):": {"en": "Volume (L):", "de": "Volumen (L):", "fr": "Volume (L):"},
    "浓度 (mol/L):": {"en": "Conc (mol/L):", "de": "Konz (mol/L):", "fr": "Conc (mol/L):"},
    "摩尔质量:": {"en": "Molar Mass:", "de": "Molmasse:", "fr": "Masse Molaire:"},
    "摩尔质量 (g/mol):": {"en": "Molar Mass (g/mol):", "de": "Molmasse (g/mol):", "fr": "Masse Molaire (g/mol):"},
    "计算 (输入其中三项)": {"en": "Calc (enter 3 of 4)", "de": "Berechnen (3 von 4)", "fr": "Calculer (3 sur 4)"},
    "直接输入 [H+]": {"en": "Direct [H+]", "de": "Direkt [H+]", "fr": "[H+] Direct"},
    "Ka (弱酸)": {"en": "Ka (weak acid)", "de": "Ka (schwache Säure)", "fr": "Ka (acide faible)"},
    "弱酸浓度": {"en": "Weak Acid Conc", "de": "Schwache Säure Konz", "fr": "Conc Acide Faible"},
    "计算 pH": {"en": "Calc pH", "de": "pH berechnen", "fr": "Calculer pH"},
    "理论产量:": {"en": "Theoretical Yield:", "de": "Theoretische Ausbeute:", "fr": "Rendement Théorique:"},
    "实际产量:": {"en": "Actual Yield:", "de": "Tatsächliche Ausbeute:", "fr": "Rendement Réel:"},
    "计算产率": {"en": "Calc Yield", "de": "Ausbeute berechnen", "fr": "Calculer Rendement"},
    "计算稀释": {"en": "Calc Dilution", "de": "Verdünnung berechnen", "fr": "Calculer Dilution"},

    # ── 结构编辑器 ──
    "输入 SMILES / InChI / 化合物名称，回车加载...": {
        "en": "Enter SMILES / InChI / name, press Enter...",
        "de": "SMILES / InChI / Name eingeben, Enter...",
        "fr": "SMILES / InChI / nom, Entrée pour charger...",
    },
    "获取SMILES": {"en": "Get SMILES", "de": "SMILES holen", "fr": "Obtenir SMILES"},
    "→3D": {"en": "→3D", "de": "→3D", "fr": "→3D"},
    "推送当前结构到 3D 分子查看器": {"en": "Push to 3D viewer", "de": "Zum 3D-Viewer senden", "fr": "Pousser vers la vue 3D"},

    # ── 元素名 ──
    "氢": {"en": "Hydrogen", "de": "Wasserstoff", "fr": "Hydrogène"},
    "碳": {"en": "Carbon", "de": "Kohlenstoff", "fr": "Carbone"},
    "氮": {"en": "Nitrogen", "de": "Stickstoff", "fr": "Azote"},
    "氧": {"en": "Oxygen", "de": "Sauerstoff", "fr": "Oxygène"},
    "氟": {"en": "Fluorine", "de": "Fluor", "fr": "Fluor"},
    "硅": {"en": "Silicon", "de": "Silizium", "fr": "Silicium"},
    "磷": {"en": "Phosphorus", "de": "Phosphor", "fr": "Phosphore"},
    "硫": {"en": "Sulfur", "de": "Schwefel", "fr": "Soufre"},
    "氯": {"en": "Chlorine", "de": "Chlor", "fr": "Chlore"},
    "溴": {"en": "Bromine", "de": "Brom", "fr": "Brome"},
    "碘": {"en": "Iodine", "de": "Iod", "fr": "Iode"},
    "硼": {"en": "Boron", "de": "Bor", "fr": "Bore"},
    "钠": {"en": "Sodium", "de": "Natrium", "fr": "Sodium"},
    "镁": {"en": "Magnesium", "de": "Magnesium", "fr": "Magnésium"},
    "铁": {"en": "Iron", "de": "Eisen", "fr": "Fer"},

    # ── Dock 窗口 ──
    "Dock 回主窗口": {"en": "Dock Back", "de": "Andocken", "fr": "Réancrer"},

    # ── 电子书 ──
    "电子书": {"en": "eBook", "de": "eBook", "fr": "eBook"},

    # ── 分离按钮 tooltips ──
    "分离为独立窗口": {"en": "Detach to separate window", "de": "Als Fenster abdocken", "fr": "Détacher en fenêtre"},
    "关闭面板": {"en": "Close panel", "de": "Panel schließen", "fr": "Fermer le panneau"},
    "MMFF94 力场优化结构": {"en": "MMFF94 force field optimization", "de": "MMFF94-Kraftfeld-Optimierung", "fr": "Optimisation MMFF94"},
    "加氢": {"en": "Add Hydrogens", "de": "Wasserstoffe hinzufügen", "fr": "Ajouter Hydrogènes"},
    "去氢": {"en": "Remove Hydrogens", "de": "Wasserstoffe entfernen", "fr": "Retirer Hydrogènes"},
    "检测结构问题": {"en": "Check structure issues", "de": "Strukturprobleme prüfen", "fr": "Vérifier problèmes"},
    "点击空白放置原子 / 点击原子选中": {"en": "Click to place / Click atom to select", "de": "Klicken zum Platzieren / Atom auswählen", "fr": "Cliquer pour placer / sélectionner"},
    "导入结构文件": {"en": "Import structure file", "de": "Strukturdatei importieren", "fr": "Importer fichier structure"},

    # ── 甲基 -CH₃ etc. ──
    "甲基 -CH₃": {"en": "Methyl -CH₃", "de": "Methyl -CH₃", "fr": "Méthyle -CH₃"},
    "乙基 -C₂H₅": {"en": "Ethyl -C₂H₅", "de": "Ethyl -C₂H₅", "fr": "Éthyle -C₂H₅"},
    "苯环": {"en": "Phenyl Ring", "de": "Phenylring", "fr": "Cycle Phényle"},
    "羧基 -COOH": {"en": "Carboxyl -COOH", "de": "Carboxyl -COOH", "fr": "Carboxyle -COOH"},
    "氨基 -NH₂": {"en": "Amino -NH₂", "de": "Amino -NH₂", "fr": "Amino -NH₂"},
    "羟基 -OH": {"en": "Hydroxyl -OH", "de": "Hydroxyl -OH", "fr": "Hydroxyle -OH"},
    "醛基 -CHO": {"en": "Aldehyde -CHO", "de": "Aldehyd -CHO", "fr": "Aldéhyde -CHO"},
    "氰基 -CN": {"en": "Cyano -CN", "de": "Cyano -CN", "fr": "Cyano -CN"},
    "硝基 -NO₂": {"en": "Nitro -NO₂", "de": "Nitro -NO₂", "fr": "Nitro -NO₂"},
    "三氟甲基 -CF₃": {"en": "Trifluoromethyl -CF₃", "de": "Trifluormethyl -CF₃", "fr": "Trifluorométhyle -CF₃"},

    # ── 全屏 ──
    "全屏切换": {"en": "Toggle Fullscreen", "de": "Vollbild umschalten", "fr": "Basculer Plein Écran"},
    "聚焦 SMILES 输入": {"en": "Focus SMILES Input", "de": "SMILES-Eingabe fokussieren", "fr": "Focus Entrée SMILES"},

    # ── 工具面板标题 ──
    "2D 结构编辑器": {"en": "2D Structure Editor", "de": "2D-Struktureditor", "fr": "Éditeur de Structure 2D"},
    "3D 分子查看器": {"en": "3D Molecular Viewer", "de": "3D-Molekülbetrachter", "fr": "Visualiseur Moléculaire 3D"},
    "公式编辑器": {"en": "Formula Editor", "de": "Formeleditor", "fr": "Éditeur de Formules"},
    "化学工具集": {"en": "Chemistry Tools", "de": "Chemiewerkzeuge", "fr": "Outils de Chimie"},

    # ── 补充项 (计算器/编辑器) ──
    "输入:": {"en": "Input:", "de": "Eingabe:", "fr": "Entrée:"},
    "命令": {"en": "Command", "de": "Befehl", "fr": "Commande"},
    "快捷键": {"en": "Shortcut", "de": "Tastenkürzel", "fr": "Raccourci"},
    "分类": {"en": "Category", "de": "Kategorie", "fr": "Catégorie"},
    "已添加教材: ": {"en": "Added textbook: ", "de": "Lehrbuch hinzugefügt: ", "fr": "Manuel ajouté: "},
    "拖放加载: ": {"en": "Drop loaded: ", "de": "Ablage geladen: ", "fr": "Glissé chargé: "},
    "拖放添加教材: ": {"en": "Drop textbook: ", "de": "Lehrbuch abgelegt: ", "fr": "Manuel déposé: "},
    "已聚焦: ": {"en": "Focused: ", "de": "Fokussiert: ", "fr": "Focus: "},
    "已分离: ": {"en": "Detached: ", "de": "Abgedockt: ", "fr": "Détaché: "},
    "已添加到笔记: ": {"en": "Added to notes: ", "de": "Zu Notizen: ", "fr": "Ajouté aux notes: "},
    "已填入输入栏: ": {"en": "Filled input: ", "de": "Eingabe gefüllt: ", "fr": "Saisi: "},
    "已导出: ": {"en": "Exported: ", "de": "Exportiert: ", "fr": "Exporté: "},
    "已导入: ": {"en": "Imported: ", "de": "Importiert: ", "fr": "Importé: "},
    "2D → 3D: ": {"en": "2D → 3D: ", "de": "2D → 3D: ", "fr": "2D → 3D: "},
    "优化完成 — 能量: ": {"en": "Optimized — Energy: ", "de": "Optimiert — Energie: ", "fr": "Optimisé — Énergie: "},
    "优化失败: ": {"en": "Optimization failed: ", "de": "Optimierung fehlgeschlagen: ", "fr": "Échec optimisation: "},
    "加氢失败: ": {"en": "Add H failed: ", "de": "H hinzufügen fehlgeschlagen: ", "fr": "Échec ajout H: "},
    "去氢失败: ": {"en": "Remove H failed: ", "de": "H entfernen fehlgeschlagen: ", "fr": "Échec retrait H: "},
}


class I18nManager(QObject):
    """多语言管理器 — 单例"""
    languageChanged = Signal(str)  # lang_code

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._settings = QSettings("ChemistrySuite", "ChemistrySuite")
        self._lang = self._settings.value("language", "zh")
        if self._lang not in LANGUAGES:
            self._lang = "zh"
        self._initialized = True

    @property
    def current_language(self):
        return self._lang

    def supported_languages(self):
        return list(LANGUAGES.keys())

    def language_name(self, code):
        return LANGUAGES.get(code, code)

    def tr(self, text: str) -> str:
        """翻译字符串"""
        if self._lang == "zh":
            return text
        entry = TRANSLATIONS.get(text)
        if entry:
            return entry.get(self._lang, text)
        return text

    def set_language(self, code: str):
        if code not in LANGUAGES or code == self._lang:
            return
        self._lang = code
        self._settings.setValue("language", code)
        self.languageChanged.emit(code)


# 全局单例
i18n = I18nManager()
