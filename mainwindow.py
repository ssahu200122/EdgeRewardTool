import sys
import random
import math
import subprocess
import os 
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QScrollArea, QStatusBar, QToolBar, QLabel, QFrame, 
                               QSizePolicy, QSpinBox, QDialog, QFormLayout, QDialogButtonBox, 
                               QGroupBox, QMenu, QToolButton, QInputDialog, QLineEdit, QMenuBar, QMessageBox, QCheckBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QColor, QFont, QScreen

from controller import ProfileController
from db_model import MembershipLevel, Profile
from ui_components import ProfileCard
from worker import Worker
from settings_manager import SettingsManager 

# --- SILENCE PRINT STATEMENTS ---
class NullWriter:
    def write(self, text): pass
    def flush(self): pass

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

# --- HELPER: RESOURCE PATH FOR ASSETS ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- FILTER DIALOG ---
class FilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Selection")
        self.resize(250, 150)
        self.setStyleSheet("""
            QDialog { background-color: #252526; color: white; }
            QLabel { color: #ccc; font-weight: bold; }
            QSpinBox { background: #333; border: 1px solid #555; color: white; padding: 4px; }
            QPushButton { background: #0e639c; color: white; border: none; padding: 6px; border-radius: 4px; }
            QPushButton:hover { background: #1177bb; }
        """)
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Select profiles with points:"))
        form = QFormLayout()
        self.spin_min = QSpinBox(); self.spin_min.setRange(0, 1000000); self.spin_min.setSingleStep(500); self.spin_min.setValue(0)
        self.spin_max = QSpinBox(); self.spin_max.setRange(0, 1000000); self.spin_max.setSingleStep(500); self.spin_max.setValue(100000)
        form.addRow("Min Points:", self.spin_min); form.addRow("Max Points:", self.spin_max)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); layout.addWidget(btns)
    def get_range(self): return self.spin_min.value(), self.spin_max.value()

# --- SETTINGS DIALOG ---
class SettingsDialog(QDialog):
    def __init__(self, current_min, current_max, current_w, current_h, current_url, is_on_top, current_font_size, resize_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("App Settings")
        self.resize(400, 450)
        self.resize_callback = resize_callback 
        self.setStyleSheet("""
            QDialog { background-color: #252526; color: white; }
            QLabel { font-size: 13px; font-weight: bold; color: #ddd; }
            QSpinBox { 
                background-color: #333; border: 2px solid #555; border-radius: 6px; padding: 6px; color: white; font-size: 14px; font-weight: bold; 
            }
            QLineEdit { background-color: #333; border: 2px solid #555; border-radius: 6px; padding: 6px; color: #00e676; font-family: 'Consolas', monospace; }
            QCheckBox { spacing: 8px; color: #ddd; font-weight: bold; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #555; background-color: #333; }
            QCheckBox::indicator:checked { background-color: #0e639c; border-color: #0e639c; }
            QGroupBox { border: 1px solid #444; border-radius: 6px; margin-top: 10px; font-weight: bold; color: #aaa; }
            QPushButton { background-color: #0e639c; color: white; border: none; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #1177bb; }
        """)
        layout = QVBoxLayout(self); layout.setSpacing(15)
        
        grp_random = QGroupBox("Search Randomization")
        form_rnd = QFormLayout(grp_random); form_rnd.setSpacing(10)
        def to_mult_3(v): return int(v / 3) * 3
        self.spin_min = QSpinBox(); self.spin_min.setRange(3, 300); self.spin_min.setSingleStep(3); self.spin_min.setValue(to_mult_3(current_min))
        self.spin_max = QSpinBox(); self.spin_max.setRange(3, 300); self.spin_max.setSingleStep(3); self.spin_max.setValue(to_mult_3(current_max))
        form_rnd.addRow("Minimum:", self.spin_min); form_rnd.addRow("Maximum:", self.spin_max); layout.addWidget(grp_random)

        grp_win = QGroupBox("Window & Display")
        form_win = QFormLayout(grp_win); form_win.setSpacing(10)
        self.spin_w = QSpinBox(); self.spin_w.setRange(400, 2000); self.spin_w.setSingleStep(10); self.spin_w.setValue(current_w)
        self.spin_w.valueChanged.connect(self.trigger_resize)
        self.spin_h = QSpinBox(); self.spin_h.setRange(200, 1500); self.spin_h.setSingleStep(10); self.spin_h.setValue(current_h)
        self.spin_h.valueChanged.connect(self.trigger_resize)
        
        self.spin_font = QSpinBox(); self.spin_font.setRange(8, 24); self.spin_font.setValue(current_font_size)
        
        form_win.addRow("Width (px):", self.spin_w); form_win.addRow("Height (px):", self.spin_h)
        form_win.addRow("Font Size:", self.spin_font)
        layout.addWidget(grp_win)

        grp_scan = QGroupBox("General & Scanner")
        form_scan = QFormLayout(grp_scan)
        self.edit_url = QLineEdit(current_url)
        form_scan.addRow("Scan URL:", self.edit_url)
        self.chk_ontop = QCheckBox("Keep Window Always on Top")
        self.chk_ontop.setChecked(is_on_top)
        form_scan.addRow("", self.chk_ontop)
        layout.addWidget(grp_scan)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); layout.addWidget(btns)

    def trigger_resize(self):
        if self.resize_callback: self.resize_callback(self.spin_w.value(), self.spin_h.value())
    
    def get_values(self): 
        return (int(self.spin_min.value()/3)*3, int(self.spin_max.value()/3)*3, self.edit_url.text().strip(), self.chk_ontop.isChecked(), self.spin_font.value())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rewards Bot Pro")
        self.settings = SettingsManager.load()
        
        # --- LOAD WINDOW SETTINGS ---
        self.target_w = self.settings.get("window_width", 850)
        self.target_h = self.settings.get("window_height", 400)
        self.resize(self.target_w, self.target_h)
        
        if os.path.exists("logo.png"): self.setWindowIcon(QIcon("logo.png"))
        elif os.path.exists("logo.ico"): self.setWindowIcon(QIcon("logo.ico"))
        
        self.is_always_on_top = self.settings.get("always_on_top", False)
        self.current_font_size = self.settings.get("font_size", 13)
        self.apply_on_top_mode()

        self.apply_styles()
        self.move_to_bottom_right()
        self.controller = ProfileController()
        self.cards = {} 
        self.worker = None 
        self.launch_batch_index = 0
        self.launch_ids = []
        self.rnd_min = self.settings.get("search_count_min", 30)
        self.rnd_max = self.settings.get("search_count_max", 45)
        self.scan_url = self.settings.get("scan_url", "https://rewards.bing.com/")
        self.init_ui()
        self.load_profile_data()
        self.randomize_search_box()

    def apply_styles(self):
        img_plus = resource_path("assets/plus.png").replace("\\", "/")
        img_minus = resource_path("assets/minus.png").replace("\\", "/")

        self.setStyleSheet(f"""
            QMainWindow {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e1e1e, stop:1 #181818); }}
            QMenuBar {{ background-color: #2b2b2b; color: #ddd; }}
            QMenuBar::item {{ padding: 5px 10px; background-color: transparent; }}
            QMenuBar::item:selected {{ background-color: #3e3e42; }}
            QMenu {{ background-color: #252526; color: white; border: 1px solid #444; }}
            QMenu::item {{ padding: 5px 20px; }}
            QMenu::item:selected {{ background-color: #0e639c; }}
            
            QToolBar {{ background-color: #252526; border-bottom: 2px solid #0e639c; spacing: 10px; padding: 5px; }}
            QToolButton {{ background-color: #444; border: 1px solid #555; color: #f0f0f0; border-radius: 6px; padding: 6px; margin: 2px; }}
            QToolButton:hover {{ background-color: #230; border: 1px solid #555; }}
            QToolButton:pressed {{ background-color: #0e639c; color: white; }}

            QCheckBox {{ color: #ccc; font-weight: bold; spacing: 5px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #555; border-radius: 3px; background: #333; }}
            QCheckBox::indicator:checked {{ background-color: #0e639c; border-color: #0e639c; }}

            /* --- COMPACT PILL SHAPE SPINBOX --- */
            QSpinBox {{
                background-color: #ffffff;
                color: #5856D6;         /* Purple Text */
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 13px;        
                border-radius: 15px;    /* Half of height (30px) */
                padding: 0px 30px;      /* Reduced padding */
                min-height: 30px;       /* Compact Height */
                max-height: 30px;
                min-width: 80px;        
                max-width: 100px;
                selection-background-color: transparent;
                selection-color: #5856D6;
            }}

            /* DOWN BUTTON (Left Purple Circle) */
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: center left;
                width: 30px;
                height: 30px;
                background-color: #4b49b6; 
                border-top-left-radius: 15px;
                border-bottom-left-radius: 15px;
                border: none;
            }}
            QSpinBox::down-button:hover {{ background-color: #3d3b94; }}
            QSpinBox::down-button:pressed {{ background-color: #2a2970; }}

            /* UP BUTTON (Right Purple Circle) */
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: center right;
                width: 30px;
                height: 30px;
                background-color: #4b49b6; 
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
                border: none;
            }}
            QSpinBox::up-button:hover {{ background-color: #3d3b94; }}
            QSpinBox::up-button:pressed {{ background-color: #2a2970; }}

            /* ARROWS - Using Assets from Folder */
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                width: 16px;
                height: 16px;
                image: none;
            }}
            
            /* Plus Icon */
            QSpinBox::up-arrow {{
                image: url("{img_plus}");
            }}

            /* Minus Icon */
            QSpinBox::down-arrow {{
                 image: url("{img_minus}");
            }}

            /* SCROLLBAR & OTHERS */
            QScrollArea {{ border: none; background: transparent; }}
            QWidget#ScrollContents {{ background: transparent; }}
            QScrollBar:vertical {{ border: none; background: #1e1e1e; width: 10px; }}
            QScrollBar::handle:vertical {{ background: #444; min-height: 20px; border-radius: 5px; }}
            QStatusBar {{ background-color: #181818; color: #666; border-top: 1px solid #333; }}
            QLabel#StatusRight {{ color: #00e676; font-weight: bold; padding-right: 15px; }}
        """)

    def move_to_bottom_right(self):
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(geo.width() - self.width() - 10, geo.height() - self.height() - 40)

    def update_size_anchor(self, w, h):
        curr = self.geometry()
        self.resize(w, h)
        self.move(curr.x() - (w - curr.width()), curr.y() - (h - curr.height()))

    def apply_on_top_mode(self):
        flags = Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        if self.is_always_on_top: flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags); self.show()

    def init_ui(self):
        main_menu = self.menuBar()
        select_menu = main_menu.addMenu("Select")
        select_menu.addAction("All", lambda: self.apply_selection("all"))
        select_menu.addAction("None", lambda: self.apply_selection("none"))
        select_menu.addAction("Inverse", lambda: self.apply_selection("inverse"))
        select_menu.addSeparator()
        self.batch_menu = QMenu("By Batch", self)
        self.batch_menu.aboutToShow.connect(self.populate_batch_menu)
        select_menu.addMenu(self.batch_menu)
        select_menu.addAction("Range (e.g. 1-5, 8)...", self.open_range_dialog)
        select_menu.addSeparator()
        select_menu.addAction("Gold Members", lambda: self.apply_selection("gold"))
        select_menu.addAction("Silver Members", lambda: self.apply_selection("silver"))
        select_menu.addAction("Free Members", lambda: self.apply_selection("member"))
        select_menu.addSeparator()
        select_menu.addAction("By Points...", self.open_filter_dialog)
        settings_menu = main_menu.addMenu("Settings")
        settings_action = QAction("Preferences...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(settings_action)

        self.toolbar = QToolBar("Main Actions")
        self.toolbar.setMovable(True); self.toolbar.setFloatable(True)
        self.toolbar.setIconSize(QSize(28, 28)) 
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # ICONS
        self.act_start = QAction(QIcon(resource_path("assets/start.png")), "", self); self.act_start.setToolTip("Start Grinding"); self.act_start.triggered.connect(self.on_start_clicked); self.toolbar.addAction(self.act_start)
        self.act_scan = QAction(QIcon(resource_path("assets/scan.png")), "", self); self.act_scan.setToolTip("Scan Points"); self.act_scan.triggered.connect(self.on_scan_clicked); self.toolbar.addAction(self.act_scan)
        self.act_launch = QAction(QIcon(resource_path("assets/launch.png")), "", self); self.act_launch.setToolTip("Launch Profiles"); self.act_launch.triggered.connect(self.on_launch_clicked); self.toolbar.addAction(self.act_launch)
        self.act_stop = QAction(QIcon(resource_path("assets/stop.png")), "", self); self.act_stop.setToolTip("Stop Process"); self.act_stop.triggered.connect(self.on_stop_clicked); self.toolbar.addAction(self.act_stop)
        self.toolbar.addSeparator()
        self.act_kill = QAction(QIcon(resource_path("assets/close.png")), "", self); self.act_kill.setToolTip("Force Close All Edge Browsers"); self.act_kill.triggered.connect(self.on_kill_clicked); self.toolbar.addAction(self.act_kill)
        self.act_detect = QAction(QIcon(resource_path("assets/search.png")), "", self); self.act_detect.setToolTip("Scan PC for new Edge Profiles"); self.act_detect.triggered.connect(self.on_detect_clicked); self.toolbar.addAction(self.act_detect)

        self.toolbar.addSeparator()
        
        # --- PARALLEL WIDGET GROUP (Label on Top) ---
        container_batch = QWidget()
        layout_batch = QVBoxLayout(container_batch)
        layout_batch.setContentsMargins(0, 0, 0, 0)
        layout_batch.setSpacing(1)
        layout_batch.setAlignment(Qt.AlignCenter)
        
        lbl_batch = QLabel("Parallel")
        lbl_batch.setAlignment(Qt.AlignCenter)
        lbl_batch.setStyleSheet("color: #ccc; font-size: 11px; font-weight: bold; margin-bottom: 2px;")
        
        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(1, 15)
        self.spin_batch.setToolTip("Parallel Browsers")
        self.spin_batch.setValue(self.settings.get("parallel_browsers", 5))
        self.spin_batch.setAlignment(Qt.AlignCenter)
        
        layout_batch.addWidget(lbl_batch)
        layout_batch.addWidget(self.spin_batch)
        self.toolbar.addWidget(container_batch)
        
        # --- POINTS WIDGET GROUP (Label on Top) ---
        container_search = QWidget()
        layout_search = QVBoxLayout(container_search)
        layout_search.setContentsMargins(5, 0, 5, 0)
        layout_search.setSpacing(1)
        layout_search.setAlignment(Qt.AlignCenter)
        
        lbl_search = QLabel("Points")
        lbl_search.setAlignment(Qt.AlignCenter)
        lbl_search.setStyleSheet("color: #ccc; font-size: 11px; font-weight: bold; margin-bottom: 2px;")
        
        self.spin_search = QSpinBox()
        self.spin_search.setRange(3, 300)
        self.spin_search.setSingleStep(3)
        self.spin_search.setToolTip("Total Points (1 search = 3 pts)")
        self.spin_search.setAlignment(Qt.AlignCenter)
        self.spin_search.setValue(self.settings.get("last_search_val", 30)) # Restore last search value
        
        layout_search.addWidget(lbl_search)
        layout_search.addWidget(self.spin_search)
        self.toolbar.addWidget(container_search)
        
        self.toolbar.addSeparator()
        
        # --- NEW OPTIONS ---
        self.chk_update_status = QCheckBox("Scan")
        self.chk_update_status.setToolTip("Scan points after searching?")
        self.chk_update_status.setChecked(self.settings.get("scan_after_search", True)) # Restore state
        self.toolbar.addWidget(self.chk_update_status)

        self.chk_shutdown = QCheckBox("Off")
        self.chk_shutdown.setToolTip("Shutdown PC when done?")
        self.chk_shutdown.setChecked(self.settings.get("shutdown_after", False)) # Restore state
        self.toolbar.addWidget(self.chk_shutdown)
        
        empty = QWidget(); empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding); self.toolbar.addWidget(empty)
        
        central = QWidget(); self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central); self.main_layout.setContentsMargins(0,0,0,0)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content); self.cards_layout.setContentsMargins(15,15,15,15); self.cards_layout.setSpacing(10); self.cards_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.scroll_content); self.main_layout.addWidget(self.scroll)
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.lbl_selection_status = QLabel("Selected: 0 / 0"); self.lbl_selection_status.setObjectName("StatusRight")
        self.status_bar.addPermanentWidget(self.lbl_selection_status)
        self.log("Ready.")

    def on_kill_clicked(self):
        try: subprocess.run(["taskkill", "/IM", "msedge.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); self.log("All Edge instances closed.")
        except Exception as e: self.log(f"Error closing: {e}")

    def on_detect_clicked(self):
        self.log("Scanning for new profiles...")
        count = self.controller.auto_detect_profiles()
        if count > 0: self.log(f"Found {count} new profiles! Reloading..."); self.load_profile_data(); QMessageBox.information(self, "Scan Complete", f"Successfully added {count} new profiles.")
        else: self.log("No new profiles found."); QMessageBox.information(self, "Scan Complete", "No new profiles found.")

    def set_launch_active_style(self, active=True):
        widget = self.toolbar.widgetForAction(self.act_launch)
        if widget: widget.setStyleSheet("QToolButton { background-color: #2e7d32; border: 1px solid #1b5e20; } QToolButton:hover { background-color: #388e3c; }" if active else "")

    def launch_single_profile(self, profile):
        self.log(f"Launching {profile.name}...")
        try: subprocess.Popen(f'start msedge --start-maximized --profile-directory="{profile.edge_profile_directory}" "{self.scan_url}"', shell=True)
        except Exception as e: self.log(f"Error launching: {e}")

    def update_selection_counter(self):
        total = len(self.cards); selected = sum(1 for c in self.cards.values() if c.checkbox.isChecked()); self.lbl_selection_status.setText(f"Selected: {selected} / {total}")
    def apply_selection(self, mode):
        for pid, card in self.cards.items():
            cb = card.checkbox; cb.blockSignals(True)
            if mode == "all": cb.setChecked(True)
            elif mode == "none": cb.setChecked(False)
            elif mode == "inverse": cb.setChecked(not cb.isChecked())
            elif mode == "gold": cb.setChecked(card.current_membership == "Gold")
            elif mode == "silver": cb.setChecked(card.current_membership == "Silver")
            elif mode == "member": cb.setChecked(card.current_membership == "Member")
            cb.blockSignals(False)
        self.update_selection_counter(); self.log(f"Selection applied: {mode.title()}")
    def open_range_dialog(self):
        text, ok = QInputDialog.getText(self, "Range Selection", "Enter ranges (e.g., 1-5, 8):\nSeparated by commas.")
        if ok and text:
            for c in self.cards.values(): c.checkbox.blockSignals(True); c.checkbox.setChecked(False); c.checkbox.blockSignals(False)
            all_ids = list(self.cards.keys()); total = len(all_ids); parts = text.split(',')
            for part in parts:
                part = part.strip()
                try:
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        for i in range(max(1, start)-1, min(total, end)): self.cards[all_ids[i]].checkbox.setChecked(True)
                    else:
                        idx = int(part); 
                        if 1 <= idx <= total: self.cards[all_ids[idx-1]].checkbox.setChecked(True)
                except: pass
            self.update_selection_counter(); self.log("Range selection applied.")
    def populate_batch_menu(self):
        self.batch_menu.clear(); batch_size = self.spin_batch.value(); total_profiles = len(self.cards)
        if total_profiles == 0: return
        num_batches = math.ceil(total_profiles / batch_size)
        for i in range(num_batches):
            batch_num = i + 1; start_idx = i * batch_size + 1; end_idx = min((i + 1) * batch_size, total_profiles)
            action = QAction(f"Batch {batch_num} ({start_idx}-{end_idx})", self)
            action.triggered.connect(lambda checked=False, b_idx=i: self.select_batch_index(b_idx)); self.batch_menu.addAction(action)
    def select_batch_index(self, batch_index):
        batch_size = self.spin_batch.value(); all_ids = list(self.cards.keys()); start_idx = batch_index * batch_size; end_idx = start_idx + batch_size
        for c in self.cards.values(): c.checkbox.blockSignals(True); c.checkbox.setChecked(False); c.checkbox.blockSignals(False)
        for i in range(start_idx, min(end_idx, len(all_ids))): self.cards[all_ids[i]].checkbox.setChecked(True)
        self.update_selection_counter(); self.log(f"Selected Batch {batch_index + 1}")
    def open_filter_dialog(self):
        dlg = FilterDialog(self); 
        if dlg.exec():
            min_p, max_p = dlg.get_range()
            for pid, card in self.cards.items():
                card.checkbox.blockSignals(True)
                try: txt = card.points_label.text().replace(",", ""); pts = int(txt); select = min_p <= pts <= max_p; card.checkbox.setChecked(select)
                except: card.checkbox.setChecked(False)
                card.checkbox.blockSignals(False)
            self.update_selection_counter(); self.log(f"Filtered: {min_p}-{max_p} pts.")
    def randomize_search_box(self):
        if self.rnd_min > self.rnd_max: self.rnd_min, self.rnd_max = self.rnd_max, self.rnd_min
        raw = random.randint(self.rnd_min, self.rnd_max); val = int(raw/3)*3
        if val < self.rnd_min and val!=0: val+=3
        self.spin_search.setValue(val); self.log(f"Randomized: {val}")
    
    def open_settings_dialog(self):
        dlg = SettingsDialog(self.rnd_min, self.rnd_max, self.width(), self.height(), self.scan_url, self.is_always_on_top, self.current_font_size, self.update_size_anchor, self)
        if dlg.exec():
            self.rnd_min, self.rnd_max, self.scan_url, new_top_state, new_font = dlg.get_values()
            if new_top_state != self.is_always_on_top:
                self.is_always_on_top = new_top_state
                self.apply_on_top_mode()
            
            if new_font != self.current_font_size:
                self.current_font_size = new_font
                self.load_profile_data() 
            
            self.randomize_search_box()

    def load_profile_data(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()
        profs = self.controller.get_all_profiles()
        for p in profs:
            c = ProfileCard(p, self.current_font_size)
            c.membership_changed.connect(self.update_membership_in_db)
            c.checkbox.toggled.connect(self.update_selection_counter)
            c.launch_requested.connect(self.launch_single_profile)
            self.cards_layout.addWidget(c)
            self.cards[p.id] = c
        self.update_selection_counter()

    def update_membership_in_db(self, pid, lvl):
        sess = self.controller.session; p = sess.get(Profile, pid)
        if p: p.membership = MembershipLevel(lvl); sess.commit(); self.log(f"Updated {p.name}")
    def log(self, msg): self.status_bar.showMessage(msg, 3000)
    
    def on_launch_clicked(self):
        if self.worker and self.worker.isRunning(): return
        batch_size = self.spin_batch.value()
        if self.launch_batch_index == 0:
            self.launch_ids = [pid for pid, c in self.cards.items() if c.checkbox.isChecked()]
            if not self.launch_ids: self.log("No selection!"); return
            self.set_launch_active_style(True)
        start = self.launch_batch_index * batch_size; end = start + batch_size; current_batch_ids = self.launch_ids[start:end]
        if not current_batch_ids: self.reset_launch_state(); self.log("All batches finished."); return
        self.log(f"Launching Batch {self.launch_batch_index + 1}...")
        self.worker = Worker("launch", current_batch_ids, batch_size, self.spin_search.value(), scan_url=self.scan_url)
        self.worker.log_signal.connect(self.log); self.worker.finished_signal.connect(self.on_batch_launched); self.worker.start()
        self.act_start.setEnabled(False); self.act_scan.setEnabled(False); self.act_launch.setEnabled(False)

    def on_batch_launched(self):
        self.launch_batch_index += 1; batch_size = self.spin_batch.value(); start = self.launch_batch_index * batch_size
        if start < len(self.launch_ids): 
            self.log(f"Ready for Batch {self.launch_batch_index + 1}")
        else: self.reset_launch_state(); self.log("Done. All profiles launched.")
        self.act_start.setEnabled(True); self.act_scan.setEnabled(True); self.act_launch.setEnabled(True); self.worker = None

    def reset_launch_state(self):
        self.launch_batch_index = 0; self.launch_ids = []; self.set_launch_active_style(False)

    def start_worker(self, mode):
        if self.worker and self.worker.isRunning(): return
        ids = [pid for pid, c in self.cards.items() if c.checkbox.isChecked()]
        if not ids: self.log("No selection!"); return
        
        # --- PASS CHECKBOX STATE TO WORKER ---
        should_update = self.chk_update_status.isChecked()
        
        self.worker = Worker(mode, ids, self.spin_batch.value(), self.spin_search.value(), scan_url=self.scan_url, update_after=should_update)
        self.worker.log_signal.connect(self.log); self.worker.card_update_signal.connect(self.update_card_ui)
        self.worker.finished_signal.connect(self.on_worker_finished); self.worker.start()
        self.act_start.setEnabled(False); self.act_scan.setEnabled(False); self.act_launch.setEnabled(False)
    
    def on_start_clicked(self): self.start_worker("start")
    def on_scan_clicked(self): self.start_worker("scan")
    def on_stop_clicked(self): 
        if self.worker: self.worker.stop()
        self.reset_launch_state(); self.log("Stopping...")
    def update_card_ui(self, pid, pts, membership): 
        if pid in self.cards: 
            card = self.cards[pid]
            card.points_label.setText(f"{pts:,}")
            
            # --- UPDATE MEMBERSHIP BADGE DYNAMICALLY ---
            if membership and membership != card.current_membership:
                card.current_membership = membership
                card.badge_btn.setText(membership)
                card.update_badge_style()
        
    def on_worker_finished(self): 
        self.log("Done.")
        self.act_start.setEnabled(True); self.act_scan.setEnabled(True); self.act_launch.setEnabled(True); self.worker = None
        
        # --- SHUTDOWN LOGIC ---
        if self.chk_shutdown.isChecked():
            self.log("Shutting down in 60s...")
            os.system("shutdown /s /t 60")
    
    def closeEvent(self, e):
        # --- SAVE SETTINGS ON EXIT ---
        SettingsManager.save({
            "window_width": self.width(), 
            "window_height": self.height(), 
            "parallel_browsers": self.spin_batch.value(), 
            "search_count_min": self.rnd_min, 
            "search_count_max": self.rnd_max, 
            "last_search_val": self.spin_search.value(), 
            "scan_url": self.scan_url,
            "always_on_top": self.is_always_on_top,
            "font_size": self.current_font_size,
            "scan_after_search": self.chk_update_status.isChecked(), # Save Checkbox
            "shutdown_after": self.chk_shutdown.isChecked()          # Save Checkbox
        })
        self.controller.close(); e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec())