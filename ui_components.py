from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QCheckBox, QFrame, QPushButton)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QFont

# Base64 PNG Checkmark
B64_DATA = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAY0lEQVQ4T2NkoBAwUqifgWoG/P/P8J+QOBPDf0D8n4H0AAsjAxTAxLBzcHgVw41fd4A0IzY3EJMjjjCAMCM2N1BCCMiph2fAy6878JmH1wyqRPS0Hzm8CImR52cDAwMDw38AZmAk53669KAAAAAASUVORK5CYII="
CHECKMARK_PNG = f"url('data:image/png;base64,{B64_DATA}')"

class ClickableLabel(QLabel):
    clicked = Signal()
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        # --- FIX: Enable Hover for the Label ---
        self.setAttribute(Qt.WA_Hover)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.clicked.emit()
        super().mousePressEvent(event)

class ProfileCard(QWidget):
    membership_changed = Signal(int, str)
    launch_requested = Signal(object) 

    def __init__(self, profile_data, font_size=13):
        super().__init__()
        self.profile = profile_data 
        self.current_membership = profile_data.membership.value
        self.font_size = font_size
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(0)

        self.frame = QFrame()
        self.frame.setObjectName("CardFrame")
        self.frame.setAttribute(Qt.WA_Hover) 
        
        # Frame Stylesheet
        self.frame.setStyleSheet(f"""
            #CardFrame {{ 
                background-color: #2b2b2b; 
                border-radius: 6px; 
                border: 1px solid #3d3d3d; 
            }}
            #CardFrame:hover {{ 
                border: 1px solid #5a5a5a; 
                background-color: #323232; 
            }}
            QCheckBox {{ spacing: 8px; }}
            QCheckBox::indicator {{ 
                width: 18px; height: 18px; 
                border-radius: 4px; 
                border: 2px solid #555; 
                background-color: #2b2b2b; 
            }}
            QCheckBox::indicator:hover {{ border-color: #888; }}
            QCheckBox::indicator:checked {{ 
                background-color: #0e639c; 
                border: 2px solid #0e639c; 
                background-image: {CHECKMARK_PNG}; 
                background-position: center; 
                background-repeat: no-repeat; 
            }}
        """)
        
        self.frame_layout = QHBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(10, 5, 10, 5)
        self.frame_layout.setSpacing(15)

        # 1. Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setCursor(QCursor(Qt.PointingHandCursor))
        self.frame_layout.addWidget(self.checkbox)

        # 2. Name & Email (Single Line)
        name_font = QFont("Segoe UI", self.font_size, QFont.Bold)
        email_font = QFont("Segoe UI", self.font_size, QFont.Normal)
        
        self.name_label = QLabel(profile_data.name)
        self.name_label.setFont(name_font)
        self.name_label.setStyleSheet("color: #e0e0e0; background: transparent; border: none;")
        
        email_text = f"({profile_data.email})" if profile_data.email else ""
        self.email_label = ClickableLabel(email_text)
        self.email_label.setFont(email_font)
        self.email_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.email_label.clicked.connect(self.request_launch)
        
        # --- FIX: Specific Hover Style for Email ---
        self.email_label.setStyleSheet("""
            QLabel { 
                color: #888888; 
                background: transparent; 
                border: none; 
            }
            QLabel:hover { 
                color: #3daee9; 
                text-decoration: underline; 
            }
        """)
        
        self.frame_layout.addWidget(self.name_label)
        self.frame_layout.addWidget(self.email_label)
        
        self.frame_layout.addStretch()

        # 3. Badge
        self.badge_btn = QPushButton(self.current_membership)
        self.badge_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.badge_btn.setFixedSize(60, 20)
        self.badge_btn.clicked.connect(self.toggle_membership)
        self.update_badge_style()
        self.frame_layout.addWidget(self.badge_btn)

        # 4. Points
        self.points_label = QLabel(f"{profile_data.available_points:,}")
        self.points_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.points_label.setStyleSheet("color: #00e676; background: transparent; border: none;")
        self.points_label.setFixedWidth(80) 
        self.points_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.frame_layout.addWidget(self.points_label)

        self.layout.addWidget(self.frame)

    def request_launch(self): self.launch_requested.emit(self.profile)

    def toggle_membership(self):
        if self.current_membership == "Member": self.current_membership = "Silver"
        elif self.current_membership == "Silver": self.current_membership = "Gold"
        else: self.current_membership = "Member"
        self.badge_btn.setText(self.current_membership)
        self.update_badge_style()
        self.membership_changed.emit(self.profile.id, self.current_membership)

    def update_badge_style(self):
        color_map = {"Member": "#555555", "Silver": "#90a4ae", "Gold": "#ffb300"}
        text_color = "#000000" if self.current_membership == "Gold" else "#ffffff"
        bg_color = color_map.get(self.current_membership, "#555555")
        self.badge_btn.setStyleSheet(f"QPushButton {{ background-color: {bg_color}; color: {text_color}; border-radius: 10px; font-size: 10px; font-weight: bold; border: none; }} QPushButton:hover {{ opacity: 0.8; }}")