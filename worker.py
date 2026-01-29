import time
import subprocess
import cv2
import numpy as np
import pyautogui
import pytesseract
import re
import random
import os
import sys
import pygetwindow as gw
from PySide6.QtCore import QThread, Signal
from db_model import Session, Profile

# --- TESSERACT CONFIG ---
def setup_tesseract():
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.join(os.getenv('LOCALAPPDATA'), r'Tesseract-OCR\tesseract.exe')
    ]
    if hasattr(sys, '_MEIPASS'):
        possible_paths.append(os.path.join(sys._MEIPASS, 'Tesseract-OCR', 'tesseract.exe'))
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return True
    return False

setup_tesseract()

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
        self.word_list = ["apple", "banana", "tech", "python", "finance", "news", "weather", "money"]

    def run(self):
        try:
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
                    self.run_batch_launch(batch)
                    if i < len(batches) - 1:
                        self.log_signal.emit("Waiting 5s before next batch...")
                        time.sleep(5)

            session.close()
            self.log_signal.emit("All Batches Complete.")
        
        except Exception as e:
            self.log_signal.emit(f"Worker Error: {str(e)}")
        
        finally:
            self.finished_signal.emit()

    # ... [Keep your existing methods: run_batch_launch, run_parallel_searches, run_sequential_scan, etc.] ...
    # IMPORTANT: Ensure NO 'print()' statements are in the methods below. Use self.log_signal.emit() or nothing.
    
    def run_batch_launch(self, batch):
        self.log_signal.emit("Launching browsers...")
        for profile in batch:
            if not self.is_running: break
            cmd = f'start msedge --start-maximized --profile-directory="{profile.edge_profile_directory}" "{self.scan_url}"'
            subprocess.Popen(cmd, shell=True)
            time.sleep(1)

    def run_parallel_searches(self, batch):
        self.log_signal.emit("Launching browsers...")
        for profile in batch:
            cmd = f'start msedge --start-maximized --profile-directory="{profile.edge_profile_directory}"'
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
                except Exception: pass 
            self.log_signal.emit(f"Batch Progress: {i+1}/{self.search_count}")

    def run_sequential_scan(self, batch, session):
        for profile in batch:
            if not self.is_running: break
            self.log_signal.emit(f"Scanning: {profile.name}")
            
            cmd = f'start msedge --start-maximized --profile-directory="{profile.edge_profile_directory}"'
            subprocess.Popen(cmd, shell=True)
            time.sleep(4)
            
            self.navigate_to_url(self.scan_url)
            self.log_signal.emit(f"Waiting for points...")
            found_points = None
            for attempt in range(15):
                if not self.is_running: break
                points = self.capture_points_ocr()
                if points is not None:
                    found_points = points
                    break
                time.sleep(2)
            
            if found_points is not None:
                profile.available_points = found_points
                session.commit()
                self.card_update_signal.emit(profile.id, found_points)
                self.log_signal.emit(f"[{profile.name}] Success: {found_points}")
            else:
                self.log_signal.emit(f"[{profile.name}] Failed: Timed out")
            
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
        except Exception:
            # DO NOT PRINT HERE
            return None

    def stop(self): self.is_running = False