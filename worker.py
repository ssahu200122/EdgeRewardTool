import time
import subprocess
import cv2
import numpy as np
import pyautogui
import pytesseract
import re
import random
import pygetwindow as gw
from PySide6.QtCore import QThread, Signal
from db_model import Session, Profile

# CONFIGURATION
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class Worker(QThread):
    log_signal = Signal(str)            
    card_update_signal = Signal(int, int) 
    finished_signal = Signal()          

    def __init__(self, mode, selected_ids, batch_size=5, search_count=30, scan_url="https://rewards.bing.com/pointsbreakdown"):
        super().__init__()
        self.mode = mode
        self.selected_ids = selected_ids
        self.batch_size = batch_size
        self.search_count = search_count
        self.scan_url = scan_url
        self.is_running = True
        
        self.word_list = [
            "apple", "banana", "cherry", "date", "fig", "grape", "kiwi", "lemon", "mango",
            "weather", "news", "define", "history", "tech", "python", "film", "game", "code",
            "space", "robot", "ai", "physics", "math", "biology", "chemistry", "stars",
            "galaxy", "universe", "planet", "solar", "energy", "power", "light", "speed",
            "sound", "music", "art", "design", "money", "finance", "stock", "market"
        ]

    def run(self):
        session = Session()
        all_profiles = []
        for p_id in self.selected_ids:
            p = session.get(Profile, p_id)
            if p: all_profiles.append(p)

        self.log_signal.emit(f"Starting {self.mode.upper()}. Total: {len(all_profiles)}")
        batches = [all_profiles[i:i + self.batch_size] for i in range(0, len(all_profiles), self.batch_size)]

        for i, batch in enumerate(batches):
            if not self.is_running: break
            self.log_signal.emit(f"--- Batch {i+1}/{len(batches)} ({len(batch)} profiles) ---")
            
            if self.mode == "scan":
                self.run_sequential_scan(batch, session)
                self.close_all_browsers()
                time.sleep(2)
            
            elif self.mode == "start":
                self.run_parallel_searches(batch)
                self.close_all_browsers()
                time.sleep(2)
            
            elif self.mode == "launch":
                # NEW LAUNCH MODE
                self.run_batch_launch(batch)
                # Note: We do NOT close browsers in launch mode
                # Wait a bit before next batch to avoid CPU spike
                if i < len(batches) - 1:
                    self.log_signal.emit("Waiting 5s before next batch...")
                    time.sleep(5)

        session.close()
        self.log_signal.emit("All Batches Complete.")
        self.finished_signal.emit()

    def run_batch_launch(self, batch):
        """Launches profiles to the scan URL without closing them."""
        self.log_signal.emit("Launching browsers...")
        for profile in batch:
            if not self.is_running: break
            # Launch with URL
            cmd = f'start msedge --profile-directory="{profile.edge_profile_directory}" "{self.scan_url}"'
            subprocess.Popen(cmd, shell=True)
            # Stagger slighty so windows don't overlap perfectly
            time.sleep(1)

    def run_parallel_searches(self, batch):
        self.log_signal.emit("Launching browsers...")
        for profile in batch:
            cmd = f'start msedge --profile-directory="{profile.edge_profile_directory}"'
            subprocess.Popen(cmd, shell=True)
            time.sleep(0.5) 
        
        self.log_signal.emit("Waiting for browsers to load...")
        time.sleep(5) 

        windows = [w for w in gw.getAllWindows() if "Edge" in w.title or "Bing" in w.title]
        if not windows:
            self.log_signal.emit("Error: No Edge windows found!")
            return

        self.log_signal.emit(f"Starting Fast Loop: {self.search_count} rounds")

        for i in range(self.search_count):
            if not self.is_running: break
            for win in windows:
                try:
                    win.activate()
                    word = random.choice(self.word_list) + str(random.randint(1, 999))
                    pyautogui.hotkey('ctrl', 'e')
                    pyautogui.write(word)
                    pyautogui.press('enter')
                    time.sleep(1)
                    if len(windows) <= 3: time.sleep(1.5)
                except Exception: pass 
            self.log_signal.emit(f"Batch Progress: {i+1}/{self.search_count}")

    def run_sequential_scan(self, batch, session):
        for profile in batch:
            if not self.is_running: break
            self.log_signal.emit(f"Scanning: {profile.name}")
            
            cmd = f'start msedge --profile-directory="{profile.edge_profile_directory}"'
            subprocess.Popen(cmd, shell=True)
            time.sleep(3)
            
            self.navigate_to_url(self.scan_url)
            time.sleep(4)
            
            points = self.capture_points_ocr()
            if points:
                profile.available_points = points
                session.commit()
                self.card_update_signal.emit(profile.id, points)
                self.log_signal.emit(f"[{profile.name}] Updated: {points}")
            
            self.close_all_browsers() 
            time.sleep(1)

    def close_all_browsers(self):
        try: subprocess.run(["taskkill", "/IM", "msedge.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

    def navigate_to_url(self, url):
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.5)
        pyautogui.write(url)
        pyautogui.press('enter')

    def capture_points_ocr(self):
        try:
            screenshot = pyautogui.screenshot()
            frame = np.array(screenshot)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            text = pytesseract.image_to_string(gray, config='--psm 6')
            match = re.search(r"Available points[^\d]*(\d[\d,]*)", text, re.IGNORECASE)
            if match: return int(match.group(1).replace(",", ""))
            return None
        except: return None

    def stop(self): self.is_running = False