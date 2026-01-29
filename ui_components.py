import subprocess
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QCheckBox, QFrame, QPushButton)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

# 1. Base64 PNG Checkmark (Standard White Tick)
# We store just the raw B64 string here to inject it cleanly later
B64_DATA = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAY0lEQVQ4T2NkoBAwUqifgWoG/P/P8J+QOBPDf0D8n4H0AAsjAxTAxLBzcHgVw41fd4A0IzY3EJMjjjCAMCM2N1BCCMiph2fAy6878JmH1wyqRPS0Hzm8CImR52cDAwMDw38AZmAk53669KAAAAAASUVORK5CYII="

# 2. STYLESHEET
# Notice the double quotes inside url("...") - This prevents the Windows path bug.
CARD_STYLE = f"""
    QFrame#CardFrame {{
        background-color: #2b2b2b;
        border-radius: 6px;
        border: 1px solid #3d3d3d;
    }}
    QFrame#CardFrame:hover {{
        border: 1px solid #5a5a5a;
        background-color: #323232;
    }}
    QLabel {{
        color: #e0e0e0;
        font-family: 'Segoe UI', sans-serif;
    }}
    QLabel#NameLabel {{ font-size: 13px; font-weight: bold; }}
    
    QLabel#EmailLabel {{ color: #888888; font-size: 10px; }}
    QLabel#EmailLabel:hover {{ 
        color: #3daee9; 
        text-decoration: underline;
    }}

    QLabel#PointsLabel {{ color: #00e676; font-size: 14px; font-weight: bold; }}
    
    /* --- CHECKBOX STYLING --- */
    QCheckBox {{ spacing: 8px; }}
    
    QCheckBox::indicator {{
        width: 18px; 
        height: 18px;
        border-radius: 4px;
        border: 2px solid #555; 
        background-color: #2b2b2b;
    }}
    
    QCheckBox::indicator:hover {{ border-color: #888; }}
    
    /* CHECKED STATE */
    QCheckBox::indicator:checked {{
        background-color: #0e639c; 
        border: 2px solid #0e639c;
        /* Double quotes around data URI are CRITICAL for Windows */
        image: url("data:image/png;base64,{B64_DATA}");
    }}
"""

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class ProfileCard(QWidget):
    membership_changed = Signal(int, str)
    launch_requested = Signal(object) 

    def __init__(self, profile_data):
        super().__init__()
        self.profile = profile_data 
        self.current_membership = profile_data.membership.value
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(0)

        self.frame = QFrame()
        self.frame.setObjectName("CardFrame")
        self.frame.setStyleSheet(CARD_STYLE)
        
        self.frame_layout = QHBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(8, 5, 8, 5)
        self.frame_layout.setSpacing(10)

        # 1. Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setCursor(QCursor(Qt.PointingHandCursor))
        self.frame_layout.addWidget(self.checkbox)

        # 2. Name & Email
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignVCenter)
        
        self.name_label = QLabel(profile_data.name)
        self.name_label.setObjectName("NameLabel")
        
        email_text = profile_data.email if profile_data.email else "No Email"
        self.email_label = ClickableLabel(email_text)
        self.email_label.setObjectName("EmailLabel")
        self.email_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.email_label.setToolTip(f"Launch {profile_data.name}")
        self.email_label.clicked.connect(self.request_launch)
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.email_label)
        self.frame_layout.addLayout(info_layout)
        
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
        self.points_label.setObjectName("PointsLabel")
        self.points_label.setFixedWidth(70) 
        self.points_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.frame_layout.addWidget(self.points_label)

        self.layout.addWidget(self.frame)

    def request_launch(self):
        self.launch_requested.emit(self.profile)

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
        
        self.badge_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color}; color: {text_color};
                border-radius: 10px; font-size: 10px; font-weight: bold; border: none;
            }}
            QPushButton:hover {{ opacity: 0.8; }}
        """)