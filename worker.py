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
from db_model import Session, Profile, MembershipLevel

from wonderwords import RandomWord

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
    card_update_signal = Signal(int, int, str) 
    finished_signal = Signal()          

    def __init__(self, mode, selected_ids, batch_size=5, search_count=30, scan_url="https://rewards.bing.com/pointsbreakdown", update_after=True):
        super().__init__()
        self.mode = mode
        self.selected_ids = selected_ids
        self.batch_size = batch_size
        self.search_count = search_count 
        self.scan_url = scan_url
        self.update_after = update_after 
        self.is_running = True
        self.r = RandomWord()

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
                    time.sleep(1)
                
                elif self.mode == "start":
                    self.run_parallel_searches(batch)
                    self.close_all_browsers()
                    time.sleep(1)
                    
                    if self.is_running and self.update_after:
                        self.log_signal.emit("Searches finished. Verifying details...")
                        self.run_sequential_scan(batch, session)
                        self.close_all_browsers()
                        time.sleep(1)
                
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

    def run_batch_launch(self, batch):
        self.log_signal.emit("Launching browsers...")
        for profile in batch:
            if not self.is_running: break
            cmd = f'start msedge --start-maximized --profile-directory="{profile.edge_profile_directory}" "{self.scan_url}"'
            subprocess.Popen(cmd, shell=True)
            time.sleep(1)

    def run_parallel_searches(self, batch):
        self.log_signal.emit("Cleaning up previous windows...")
        self.close_all_browsers()
        time.sleep(2) 

        self.log_signal.emit("Launching browsers...")
        for profile in batch:
            cmd = f'start msedge --start-maximized --profile-directory="{profile.edge_profile_directory}"'
            subprocess.Popen(cmd, shell=True)
            time.sleep(0.5) 
        
        self.log_signal.emit("Waiting for browsers to load...")
        time.sleep(5) 

        all_wins = gw.getAllWindows()
        windows = []
        for w in all_wins:
            t = w.title
            if "Edge" in t and "Reward" not in t and "Py" not in t and "Visual Studio" not in t:
                windows.append(w)
        
        if not windows:
            self.log_signal.emit("Error: No valid Edge windows found!")
            return

        total_searches_needed = int(self.search_count / 3)
        self.log_signal.emit(f"Target: {self.search_count} Pts ({total_searches_needed} searches)")

        for i in range(total_searches_needed):
            if not self.is_running: break
            for win in windows:
                try:
                    win.activate()
                    word = self.r.word()
                    pyautogui.hotkey('ctrl', 'e')
                    pyautogui.write(word)
                    pyautogui.press('enter')
                    time.sleep(1)
                except Exception: pass 
            self.log_signal.emit(f"Progress: {i+1}/{total_searches_needed}")

    def run_sequential_scan(self, batch, session):
        for profile in batch:
            if not self.is_running: break
            self.log_signal.emit(f"Scanning: {profile.name}")
            
            cmd = f'start msedge --start-maximized --profile-directory="{profile.edge_profile_directory}" "{self.scan_url}"'
            subprocess.Popen(cmd, shell=True)
            
            self.log_signal.emit(f"Waiting for page load...")
            time.sleep(5) 
            
            found_points = None
            found_mem = None
            
            # Basic Retry Loop (Single Pass)
            for attempt in range(15):
                if not self.is_running: break
                
                points, mem = self.capture_dashboard_data()
                
                if points is not None:
                    found_points = points
                    if mem: found_mem = mem
                    break
                time.sleep(1.5)
            
            if found_points is not None:
                profile.available_points = found_points
                final_mem = found_mem if found_mem else "Member"
                try: profile.membership = MembershipLevel(final_mem)
                except: profile.membership = MembershipLevel.Member

                session.commit()
                self.card_update_signal.emit(profile.id, found_points, final_mem)
                self.log_signal.emit(f"[{profile.name}] Success: {found_points} Pts | {final_mem}")
            else:
                self.log_signal.emit(f"[{profile.name}] Failed: Timed out")
            
            self.close_all_browsers() 
            time.sleep(1)

    def close_all_browsers(self):
        try: subprocess.run(["taskkill", "/IM", "msedge.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

    def capture_dashboard_data(self):
        try:
            screenshot = pyautogui.screenshot()
            frame = np.array(screenshot)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Native Resolution (The method that worked best for you)
            custom_config = r'--psm 6' 
            text = pytesseract.image_to_string(gray, config=custom_config)
            
            points = self._parse_points(text)
            membership = self._parse_membership(text)
            return points, membership

        except Exception:
            return None, None

    def _parse_points(self, text):
        # The regex that was working for you
        match = re.search(r"Available points[^\d]*(\d[\d,]*)", text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except:
                pass
        return None

    def _parse_membership(self, text):
        if re.search(r"\bGold\b", text, re.IGNORECASE) or "Level 2" in text: return "Gold"
        if re.search(r"\bSilver\b", text, re.IGNORECASE) or "Level 1" in text: return "Silver"
        if "Member" in text: return "Member"
        return None

    def stop(self): self.is_running = False