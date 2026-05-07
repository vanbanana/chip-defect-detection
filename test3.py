import sys
import cv2
import numpy as np
import time
import json
import os
import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGroupBox, QFileDialog, 
    QSlider, QSpinBox, QGridLayout, QScrollArea, QMessageBox,
    QInputDialog, QComboBox, QDoubleSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, 
    QAbstractItemView, QSizePolicy, QTabWidget  # <--- 已补全 QTabWidget
)
from PySide6.QtCore import Qt, Signal, QThread, QSize, QEvent, QRectF, QPointF
from PySide6.QtGui import QImage, QPixmap, QFont, QWheelEvent, QColor, QPainter, QPaintEvent

# ==========================================
# 0. 样式表 (Cyber-Industrial Theme)
# ==========================================
STYLE_SHEET = """
/* 全局设定 */
QMainWindow, QWidget { 
    background-color: #121212; 
    color: #E0E0E0; 
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 12px;
}

/* Tab 样式 */
QTabWidget::pane { border: 1px solid #333; top: -1px; }
QTabBar::tab { 
    background: #222; 
    color: #888; 
    padding: 8px 25px; 
    min-width: 80px;
    border-right: 1px solid #121212;
    font-weight: bold;
}
QTabBar::tab:selected { 
    background: #007ACC; 
    color: white; 
}

/* 分组框 */
QGroupBox { 
    border: 1px solid #333; 
    border-radius: 4px; 
    margin-top: 10px; 
    padding-top: 15px; 
    font-weight: bold;
}
QGroupBox::title { 
    subcontrol-origin: margin; 
    left: 10px; 
    padding: 0 5px; 
    color: #00B0FF; 
}

/* 按钮 */
QPushButton { 
    background-color: #2D2D2D; 
    border: 1px solid #444; 
    color: white; 
    padding: 6px 12px; 
    border-radius: 3px;
    font-weight: bold;
}
QPushButton:hover { background-color: #3E3E3E; border-color: #00B0FF; }
QPushButton:pressed { background-color: #00B0FF; border-color: #00B0FF; }

QPushButton#BtnRun { background-color: #FF9800; border: none; color: black; font-size: 14px; }
QPushButton#BtnRun:hover { background-color: #FFB74D; }
QPushButton#BtnRun:disabled { background-color: #555; color: #888; }

QPushButton#BtnLoad { background-color: #0063B1; border: none; font-weight: bold; }
QPushButton#BtnLoad:hover { background-color: #007ACC; }

/* 输入控件 */
QSpinBox, QDoubleSpinBox, QComboBox { 
    background-color: #1E1E1E; 
    border: 1px solid #444; 
    color: #00E676; 
    padding: 4px;
    border-radius: 2px;
    font-weight: bold;
}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; }

/* 滑块 */
QSlider::groove:horizontal { height: 4px; background: #333; border-radius: 2px; }
QSlider::handle:horizontal { 
    background: #00B0FF; 
    width: 14px; height: 14px; 
    margin: -5px 0; 
    border-radius: 7px; 
}

/* 表格 */
QTableWidget { background-color: #1E1E1E; border: 1px solid #333; gridline-color: #333; }
QHeaderView::section { background-color: #2D2D2D; color: #AAA; border: none; padding: 4px; font-weight: bold; }
QTableWidget::item:selected { background-color: #004C8C; color: white; }

/* 状态灯箱 */
QLabel#StatusBox {
    background-color: #000;
    border: 2px solid #333;
    border-radius: 6px;
}
"""

# ==========================================
# Part 1: 禁止滚轮的参数控件
# ==========================================

class NoWheelSlider(QSlider):
    def wheelEvent(self, event): event.ignore()
class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event): event.ignore()
class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event): event.ignore()
class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event): event.ignore()

class SmartSlider(QWidget):
    value_changed = Signal(float)
    def __init__(self, name, min_val, max_val, init_val, scale=1.0, parent=None):
        super().__init__(parent)
        self.scale = scale; self.is_float = scale != 1.0
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 2, 0, 2); layout.setSpacing(8)
        self.lbl = QLabel(name); self.lbl.setFixedWidth(80); self.lbl.setStyleSheet("color: #AAA; font-weight: bold;")
        self.slider = NoWheelSlider(Qt.Horizontal); self.slider.setRange(int(min_val), int(max_val)); self.slider.setValue(int(init_val)); self.slider.setCursor(Qt.PointingHandCursor)
        if self.is_float:
            self.spin = NoWheelDoubleSpinBox(); self.spin.setDecimals(1); self.spin.setSingleStep(0.1); self.spin.setRange(min_val * scale, max_val * scale)
        else:
            self.spin = NoWheelSpinBox(); self.spin.setRange(int(min_val), int(max_val))
        self.spin.setFixedWidth(60); self.spin.setValue(init_val * scale); self.spin.setKeyboardTracking(False) 
        layout.addWidget(self.lbl); layout.addWidget(self.slider); layout.addWidget(self.spin)
        self.slider.valueChanged.connect(self._on_slider); self.spin.valueChanged.connect(self._on_spin)
    def _on_slider(self, val):
        real = val * self.scale
        if abs(self.spin.value() - real) > 0.0001: self.spin.blockSignals(True); self.spin.setValue(real); self.spin.blockSignals(False); self.value_changed.emit(real)
    def _on_spin(self, val):
        sval = int(val / self.scale) if self.scale != 1.0 else int(val)
        if self.slider.value() != sval: self.slider.blockSignals(True); self.slider.setValue(sval); self.slider.blockSignals(False); self.value_changed.emit(val)
    def get_value(self): return self.spin.value()
    def set_value(self, val): self.spin.setValue(val)

# ==========================================
# Part 2: 核心 - CanvasEngine (画布引擎)
# ==========================================
class CanvasWidget(QWidget):
    """
    基于 QPainter 的高性能绘图控件
    - 布局固定：控件大小由 Layout 决定，不会因为图片变大而撑大
    - 内部缩放：图片只在 Paint 事件中缩放，不影响控件物理尺寸
    - 自动居中：图片永远在黑底中央
    """
    def __init__(self, placeholder_text="NO SIGNAL", parent=None):
        super().__init__(parent)
        self.setMinimumSize(350, 350) # 强制最小尺寸
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pixmap = None
        self.scale = 1.0
        self.placeholder_text = placeholder_text
        self.setMouseTracking(True) 

    def set_pixmap(self, p):
        self.pixmap = p
        self.fit_to_window()
        self.update() 

    def fit_to_window(self):
        if self.pixmap and not self.pixmap.isNull():
            ratio_w = self.width() / self.pixmap.width()
            ratio_h = self.height() / self.pixmap.height()
            self.scale = min(ratio_w, ratio_h) * 0.95 

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景
        painter.fillRect(self.rect(), QColor("#000000"))
        painter.setPen(QColor("#333333"))
        painter.drawRect(0, 0, self.width()-1, self.height()-1)

        if self.pixmap and not self.pixmap.isNull():
            target_w = self.pixmap.width() * self.scale
            target_h = self.pixmap.height() * self.scale
            x = (self.width() - target_w) / 2
            y = (self.height() - target_h) / 2
            
            target_rect = QRectF(x, y, target_w, target_h)
            painter.drawPixmap(target_rect, self.pixmap, QRectF(self.pixmap.rect()))
            
            # 比例提示
            painter.setPen(QColor("#00B0FF"))
            painter.drawText(10, 20, f"Zoom: {self.scale:.2f}x")
        else:
            painter.setPen(QColor("#555555"))
            font = painter.font(); font.setPointSize(14); font.setBold(True); painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, self.placeholder_text)

    def wheelEvent(self, event: QWheelEvent):
        if not self.pixmap: return
        angle = event.angleDelta().y()
        factor = 1.1 if angle > 0 else 0.9
        new_scale = self.scale * factor
        if 0.1 <= new_scale <= 10.0:
            self.scale = new_scale
            self.update() 

# ==========================================
# Part 3: 核心算法
# ==========================================
class InspectRes:
    def __init__(self):
        self.ok = False; self.img_orig = None; self.img_res = None; self.area = 0
        self.name = ""; self.path = ""

class CoreAlgo:
    def __init__(self):
        self.p = {'h_min':100, 'h_max':130, 's_min':90, 'v_thresh':100, 'area_max':150, 'margin':20, 'min_blob':5}
    def update(self, p): self.p.update(p)
    def run(self, path):
        res = InspectRes(); res.name = Path(path).name; res.path = path
        try:
            arr = np.fromfile(path, np.uint8); img = cv2.imdecode(arr, -1)
        except: img = None
        if img is None: return res
        vis = img.copy(); res.img_orig = self.cv2pix(img); h, w = img.shape[:2]
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_chip = cv2.inRange(hsv, np.array([self.p['h_min'], self.p['s_min'], 50]), np.array([self.p['h_max'], 255, 255]))
        mask_chip = cv2.morphologyEx(mask_chip, cv2.MORPH_CLOSE, np.ones((7,7),np.uint8))
        cnts, _ = cv2.findContours(mask_chip, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask_safe = np.zeros((h,w), np.uint8)
        
        if cnts:
            max_c = max(cnts, key=cv2.contourArea)
            mask_solid = np.zeros((h,w), np.uint8)
            cv2.drawContours(mask_solid, [max_c], -1, 255, -1)
            m = int(self.p['margin'])
            mask_safe = cv2.erode(mask_solid, np.ones((m,m), np.uint8)) if m > 0 else mask_solid
            cv2.drawContours(vis, [max_c], -1, (255, 0, 0), 2, cv2.LINE_AA) 
            safe_cnts, _ = cv2.findContours(mask_safe, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(vis, safe_cnts, -1, (0, 255, 255), 1, cv2.LINE_AA)

        mask_dark = cv2.inRange(hsv[:,:,2], 0, self.p['v_thresh'])
        mask_final = cv2.bitwise_and(mask_dark, mask_dark, mask=mask_safe)
        defect_cnts, _ = cv2.findContours(mask_final, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        total_area = 0; valid_defects = []
        for c in defect_cnts:
            a = cv2.contourArea(c)
            if a >= self.p['min_blob']: 
                total_area += a
                valid_defects.append(c)
        res.area = total_area

        if total_area > self.p['area_max']:
            res.ok = False
            cv2.drawContours(vis, valid_defects, -1, (0, 0, 255), -1)
            cv2.drawContours(vis, valid_defects, -1, (0, 255, 255), 1)
            cv2.putText(vis, f"NG: {int(total_area)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        else:
            res.ok = True
            cv2.putText(vis, "PASS", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        res.img_res = self.cv2pix(vis)
        return res

    def cv2pix(self, img):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB); h, w, c = rgb.shape
        return QPixmap.fromImage(QImage(rgb.data, w, h, c*w, QImage.Format_RGB888))

class Worker(QThread):
    prog = Signal(int, int); item = Signal(object); done = Signal()
    def __init__(self, algo, files):
        super().__init__(); self.algo = algo; self.files = files; self.running = True
    def run(self):
        n = len(self.files)
        for i, f in enumerate(self.files):
            if not self.running: break
            self.item.emit(self.algo.run(f)); self.prog.emit(i+1, n)
        self.done.emit()
    def stop(self): self.running = False

# ==========================================
# Part 4: 主界面
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Industrial Inspector v19.1 Final Fixed")
        self.resize(1600, 950)
        self.algo = CoreAlgo()
        self.files = []; self.results = []; self.history = []
        self.idx = 0
        self.cfg_path = "configs"
        if not os.path.exists(self.cfg_path): os.makedirs(self.cfg_path)
        self.init_ui()
        self.load_cfgs()

    def init_ui(self):
        QApplication.instance().setStyleSheet(STYLE_SHEET)
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QVBoxLayout(central); main_layout.setContentsMargins(5,5,5,5); main_layout.setSpacing(5)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.tab_run = QWidget(); self.setup_run_ui()
        self.tabs.addTab(self.tab_run, "生产运行 (RUN)")
        
        self.tab_gallery = QWidget(); self.setup_gallery_ui()
        self.tabs.addTab(self.tab_gallery, "结果图库 (GALLERY)")

    def setup_run_ui(self):
        layout = QHBoxLayout(self.tab_run); layout.setContentsMargins(5,5,5,5)
        
        img_splitter = QSplitter(Qt.Vertical)
        
        c1 = QWidget(); l1 = QVBoxLayout(c1); l1.setContentsMargins(0,0,0,0); l1.setSpacing(0)
        l1.addWidget(QLabel("原始图像 (Original)", styleSheet="color:#888; font-weight:bold; padding:2px; background:#181818;"))
        self.view_orig = CanvasWidget("等待加载..."); l1.addWidget(self.view_orig)
        img_splitter.addWidget(c1)
        
        c2 = QWidget(); l2 = QVBoxLayout(c2); l2.setContentsMargins(0,0,0,0); l2.setSpacing(0)
        l2.addWidget(QLabel("检测结果 (Result)", styleSheet="color:#00B0FF; font-weight:bold; padding:2px; background:#181818;"))
        self.view_res = CanvasWidget("等待加载..."); l2.addWidget(self.view_res)
        img_splitter.addWidget(c2)
        
        layout.addWidget(img_splitter, 1)

        ctrl_panel = QWidget(); ctrl_panel.setFixedWidth(380)
        clayout = QVBoxLayout(ctrl_panel); clayout.setContentsMargins(0,0,0,0); clayout.setSpacing(10)
        
        self.status_box = QLabel("READY"); self.status_box.setObjectName("StatusBox")
        self.status_box.setAlignment(Qt.AlignCenter); self.status_box.setFixedHeight(100)
        self.status_box.setStyleSheet("background-color:#000; color:#555; font-size:50px; font-weight:900; border-radius:6px;")
        clayout.addWidget(self.status_box)
        
        stat_box = QGroupBox("实时统计"); sg = QGridLayout(stat_box); sg.setVerticalSpacing(5)
        self.l_total = QLabel("0"); self.l_total.setStyleSheet("color:#FFF;font-size:16px;font-weight:bold;")
        self.l_ok = QLabel("0"); self.l_ok.setStyleSheet("color:#00E676;font-size:16px;font-weight:bold;")
        self.l_ng = QLabel("0"); self.l_ng.setStyleSheet("color:#FF1744;font-size:16px;font-weight:bold;")
        self.l_rate = QLabel("0.0%"); self.l_rate.setStyleSheet("color:#00B0FF;font-size:16px;font-weight:bold;")
        sg.addWidget(QLabel("总数:"),0,0); sg.addWidget(self.l_total,0,1)
        sg.addWidget(QLabel("合格:"),1,0); sg.addWidget(self.l_ok,1,1)
        sg.addWidget(QLabel("不良:"),2,0); sg.addWidget(self.l_ng,2,1)
        sg.addWidget(QLabel("良率:"),3,0); sg.addWidget(self.l_rate,3,1)
        clayout.addWidget(stat_box)
        
        prod_box = QGroupBox("生产控制"); pl = QVBoxLayout(prod_box)
        h_btn = QHBoxLayout()
        self.btn_run = QPushButton("▶ 批量检测"); self.btn_run.setObjectName("BtnRun"); self.btn_run.setFixedHeight(45)
        self.btn_run.clicked.connect(self.run_batch)
        self.btn_stop = QPushButton("停止"); self.btn_stop.setFixedHeight(45); self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_batch)
        h_btn.addWidget(self.btn_run, 2); h_btn.addWidget(self.btn_stop, 1)
        pl.addLayout(h_btn)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setFixedHeight(5)
        pl.addWidget(self.progress)
        
        file_box = QGroupBox("配置与文件"); fl = QVBoxLayout(file_box)
        h_cfg = QHBoxLayout(); h_cfg.addWidget(QLabel("模式:"))
        self.cb_cfg = NoWheelComboBox(); self.cb_cfg.currentIndexChanged.connect(self.on_cfg_change)
        h_cfg.addWidget(self.cb_cfg, 1); btn_save = QPushButton("保存"); btn_save.clicked.connect(self.save_cfg)
        h_cfg.addWidget(btn_save); fl.addLayout(h_cfg)
        
        btn_load = QPushButton("加载文件夹"); btn_load.setObjectName("BtnLoad"); btn_load.clicked.connect(self.load_dir)
        fl.addWidget(btn_load)
        h_nav = QHBoxLayout(); bp = QPushButton("◀"); bp.clicked.connect(self.prev_img)
        bn = QPushButton("▶"); bn.clicked.connect(self.next_img)
        self.lbl_file = QLabel("未加载"); self.lbl_file.setAlignment(Qt.AlignCenter)
        h_nav.addWidget(bp); h_nav.addWidget(self.lbl_file, 1); h_nav.addWidget(bn); fl.addLayout(h_nav)
        clayout.addWidget(prod_box); clayout.addWidget(file_box)
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        param_w = QWidget(); param_l = QVBoxLayout(param_w); param_l.setSpacing(10)
        
        g_hsv = QGroupBox("检测区域 (HSV)"); gl1 = QVBoxLayout(g_hsv)
        self.s_hm = SmartSlider("H 下限",0,180,100); gl1.addWidget(self.s_hm)
        self.s_hx = SmartSlider("H 上限",0,180,130); gl1.addWidget(self.s_hx)
        self.s_sm = SmartSlider("S 下限",0,255,90); gl1.addWidget(self.s_sm)
        param_l.addWidget(g_hsv)
        
        g_roi = QGroupBox("检测区域"); gl2 = QVBoxLayout(g_roi)
        self.s_mg = SmartSlider("边缘内缩",0,50,15); gl2.addWidget(self.s_mg)
        param_l.addWidget(g_roi)
        
        g_def = QGroupBox("缺陷判定"); gl3 = QVBoxLayout(g_def)
        self.s_vt = SmartSlider("亮度阈值",1,255,100); gl3.addWidget(self.s_vt)
        self.s_mb = SmartSlider("忽略噪点",0,50,5); gl3.addWidget(self.s_mb)
        self.s_am = SmartSlider("允许面积",10,2000,150); gl3.addWidget(self.s_am)
        param_l.addWidget(g_def)
        
        param_l.addStretch()
        scroll.setWidget(param_w)
        clayout.addWidget(scroll, 1)
        layout.addWidget(ctrl_panel)

        self.sliders = [self.s_hm, self.s_hx, self.s_sm, self.s_vt, self.s_mb, self.s_am, self.s_mg]
        for s in self.sliders: s.value_changed.connect(self.run_one)

    def setup_gallery_ui(self):
        layout = QHBoxLayout(self.tab_gallery); layout.setContentsMargins(5,5,5,5)
        
        left = QWidget(); ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0)
        h_bar = QHBoxLayout()
        h_bar.addWidget(QLabel("筛选:")); self.cb_fil = NoWheelComboBox(); self.cb_fil.addItems(["全部", "仅合格", "仅不合格"])
        self.cb_fil.currentIndexChanged.connect(self.refresh_gallery_table)
        h_bar.addWidget(self.cb_fil); h_bar.addStretch()
        btn_exp = QPushButton(" 导出检测数据 (CSV)"); btn_exp.setFixedHeight(30); btn_exp.clicked.connect(self.export_data)
        h_bar.addWidget(btn_exp); ll.addLayout(h_bar)
        
        self.table = QTableWidget(0, 3); self.table.setHorizontalHeaderLabels(["状态", "文件名", "缺陷面积"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemClicked.connect(self.on_table_click)
        ll.addWidget(self.table)
        layout.addWidget(left, 4)
        
        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0)
        rl.addWidget(QLabel("选定预览 (Preview)", styleSheet="font-weight:bold; color:#00B0FF;"))
        self.view_gal = CanvasWidget("点击左侧表格查看"); rl.addWidget(self.view_gal)
        layout.addWidget(right, 6)

    def get_p(self): return {'h_min':self.s_hm.get_value(), 'h_max':self.s_hx.get_value(), 's_min':self.s_sm.get_value(), 'v_thresh':self.s_vt.get_value(), 'area_max':self.s_am.get_value(), 'margin':self.s_mg.get_value(), 'min_blob':self.s_mb.get_value()}
    def set_p(self, p): self.s_hm.set_value(p.get('h_min',100)); self.s_hx.set_value(p.get('h_max',130)); self.s_sm.set_value(p.get('s_min',90)); self.s_vt.set_value(p.get('v_thresh',100)); self.s_am.set_value(p.get('area_max',150)); self.s_mg.set_value(p.get('margin',20)); self.s_mb.set_value(p.get('min_blob',5))
    def load_cfgs(self):
        self.cb_cfg.blockSignals(True); self.cb_cfg.clear()
        fs = list(Path(self.cfg_path).glob("*.json"))
        if not fs:
            with open(f"{self.cfg_path}/Default.json",'w') as f: json.dump(self.get_p(), f); fs = list(Path(self.cfg_path).glob("*.json"))
        for f in fs: self.cb_cfg.addItem(f.stem)
        self.cb_cfg.blockSignals(False); self.on_cfg_change()
    def on_cfg_change(self):
        path = f"{self.cfg_path}/{self.cb_cfg.currentText()}.json"
        if os.path.exists(path):
            with open(path,'r') as f: self.set_p(json.load(f))
            self.run_one()
    def save_cfg(self):
        name, ok = QInputDialog.getText(self,"保存","配方名称:", text=self.cb_cfg.currentText())
        if ok and name:
            with open(f"{self.cfg_path}/{name}.json",'w') as f: json.dump(self.get_p(), f, indent=4); self.load_cfgs(); self.cb_cfg.setCurrentText(name)
    def load_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if d:
            self.files = sorted([str(p) for p in Path(d).glob('*') if p.suffix.lower() in ['.jpg','.png','.bmp']])
            if self.files: 
                self.idx=0; self.run_one(); QMessageBox.information(self,"就绪",f"已加载 {len(self.files)} 张图片")
    def prev_img(self):
        if self.files and self.idx>0: self.idx-=1; self.run_one()
    def next_img(self):
        if self.files and self.idx<len(self.files)-1: self.idx+=1; self.run_one()
    def refresh_gallery_table(self):
        self.table.setRowCount(0); md = self.cb_fil.currentIndex()
        for i, r in enumerate(self.history):
            if md==1 and not r.ok: continue
            if md==2 and r.ok: continue
            row = self.table.rowCount(); self.table.insertRow(row)
            it_st = QTableWidgetItem("合格" if r.ok else "NG"); it_st.setForeground(QColor("#00E676" if r.ok else "#FF1744")); it_st.setData(Qt.UserRole, i)
            self.table.setItem(row, 0, it_st); self.table.setItem(row, 1, QTableWidgetItem(r.name)); self.table.setItem(row, 2, QTableWidgetItem(str(int(r.area))))
    def on_table_click(self, item):
        idx = self.table.item(item.row(), 0).data(Qt.UserRole)
        self.view_gal.set_pixmap(self.history[idx].img_res)
    def export_data(self):
        if not self.history: QMessageBox.warning(self, "警告", "无数据"); return
        path, _ = QFileDialog.getSaveFileName(self, "导出CSV", "report.csv", "CSV (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f); w.writerow(["Filename", "Status", "Area", "Path"])
                    for r in self.history: w.writerow([r.name, "OK" if r.ok else "NG", int(r.area), r.path])
                QMessageBox.information(self, "成功", f"导出至:\n{path}")
            except Exception as e: QMessageBox.critical(self, "错误", str(e))
    def run_one(self, _=None):
        if not self.files: return
        self.algo.update(self.get_p()); path = self.files[self.idx]; self.lbl_file.setText(f"{Path(path).name} ({self.idx+1}/{len(self.files)})")
        res = self.algo.run(path)
        self.view_orig.set_pixmap(res.img_orig); self.view_res.set_pixmap(res.img_res)
        if res.ok: self.status_box.setText("OK"); self.status_box.setStyleSheet("background-color:#00C853; color:white; font-size:60px; font-weight:bold; border-radius:8px;")
        else: self.status_box.setText("NG"); self.status_box.setStyleSheet("background-color:#D50000; color:white; font-size:60px; font-weight:bold; border-radius:8px;")
    def run_batch(self):
        if not self.files: return
        self.results = []; self.history = []; self.refresh_gallery_table()
        self.btn_run.setEnabled(False); self.btn_stop.setEnabled(True)
        self.algo.update(self.get_p())
        self.worker = Worker(self.algo, self.files)
        self.worker.prog.connect(self.progress.setValue); self.worker.item.connect(self.on_res); self.worker.done.connect(self.on_done)
        self.worker.start()
    def stop_batch(self):
        if self.worker: self.worker.stop()
    def on_res(self, res):
        self.results.append(res); self.history.append(res)
        self.view_res.set_pixmap(res.img_res); self.view_orig.set_pixmap(res.img_orig)
        tot = len(self.results); ok = sum(1 for r in self.results if r.ok); ng = tot - ok
        self.l_total.setText(str(tot)); self.l_ok.setText(str(ok)); self.l_ng.setText(str(ng))
        if tot>0: self.l_rate.setText(f"{ok/tot*100:.1f}%")
        if res.ok: self.status_box.setText("OK"); self.status_box.setStyleSheet("background-color:#00C853; color:white; font-size:60px; font-weight:bold; border-radius:8px;")
        else: self.status_box.setText("NG"); self.status_box.setStyleSheet("background-color:#D50000; color:white; font-size:60px; font-weight:bold; border-radius:8px;")
        self.refresh_gallery_table()
    def on_done(self):
        self.btn_run.setEnabled(True); self.btn_stop.setEnabled(False)
        QMessageBox.information(self,"完成","批量检测结束")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())