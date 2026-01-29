from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_model import Base, Profile, MembershipLevel
import os
import json

# --- CRITICAL FIX: SAVE DB TO APPDATA ---
# This ensures the database is writable even when installed in "Program Files"
# We use %LOCALAPPDATA% instead of the current folder.
app_data_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'RewardsBotPro')

# Create the folder if it doesn't exist
if not os.path.exists(app_data_dir):
    try:
        os.makedirs(app_data_dir)
    except OSError:
        pass

# Set the database path to this safe folder
DB_NAME = os.path.join(app_data_dir, "profiles.db")

# Initialize Database
engine = create_engine(f"sqlite:///{DB_NAME}")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

class ProfileController:
    def __init__(self):
        self.session = Session()

    def get_all_profiles(self):
        return self.session.query(Profile).all()

    def add_profile(self, name, email=None, edge_dir="Default"):
        new_profile = Profile(
            name=name,
            email=email,
            edge_profile_directory=edge_dir,
            membership=MembershipLevel.MEMBER
        )
        self.session.add(new_profile)
        self.session.commit()
        return new_profile

    def delete_profile(self, profile_id):
        profile = self.session.get(Profile, profile_id)
        if profile:
            self.session.delete(profile)
            self.session.commit()

    def auto_detect_profiles(self):
        """Scans the user's PC for Edge profiles automatically."""
        local_app_data = os.getenv('LOCALAPPDATA')
        if not local_app_data: return 0
        
        edge_user_data = os.path.join(local_app_data, 'Microsoft', 'Edge', 'User Data')
        if not os.path.exists(edge_user_data): return 0

        # Get existing directories to avoid duplicates
        existing_dirs = {p.edge_profile_directory for p in self.get_all_profiles()}
        new_count = 0
        
        try:
            for item in os.listdir(edge_user_data):
                # We look for folders named "Default" or "Profile X"
                if item == "Default" or item.startswith("Profile "):
                    full_path = os.path.join(edge_user_data, item)
                    
                    if os.path.isdir(full_path):
                        # It's a valid profile if it has a 'Preferences' file
                        if os.path.exists(os.path.join(full_path, "Preferences")):
                            
                            if item not in existing_dirs:
                                # Try to grab the email
                                email = "Unknown"
                                try:
                                    with open(os.path.join(full_path, "Preferences"), 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        email = data.get('account_info', [{}])[0].get('email', '')
                                except: pass

                                display_name = item 
                                if not email: email = None

                                self.add_profile(display_name, email, item)
                                new_count += 1
        except Exception as e:
            print(f"Error scanning: {e}")
            
        return new_count

    def close(self):
        self.session.close()