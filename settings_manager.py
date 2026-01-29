import json
import os

SETTINGS_FILE = "user_settings.json"

class SettingsManager:
    DEFAULT_SETTINGS = {
        "window_width": 850,
        "window_height": 400,
        "parallel_browsers": 5,
        "search_count_min": 30,
        "search_count_max": 45,
        "last_search_val": 30,
        "scan_url": "https://rewards.bing.com/pointsbreakdown",
        "always_on_top": False,
        "font_size": 13  # <--- NEW SETTING
    }

    @staticmethod
    def load():
        if not os.path.exists(SETTINGS_FILE): return SettingsManager.DEFAULT_SETTINGS.copy()
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
            defaults = SettingsManager.DEFAULT_SETTINGS.copy()
            defaults.update(data)
            return defaults
        except: return SettingsManager.DEFAULT_SETTINGS.copy()

    @staticmethod
    def save(data):
        try:
            with open(SETTINGS_FILE, 'w') as f: json.dump(data, f, indent=4)
        except: pass