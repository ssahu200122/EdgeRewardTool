from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_model import Base, Profile, MembershipLevel
import os
import json
import sys

# --- DATABASE PATH CONFIGURATION ---
if getattr(sys, 'frozen', False):
    # If running as a compiled EXE, put DB next to the .exe file
    base_path = os.path.dirname(sys.executable)
else:
    # If running as a Python script, put DB next to this script file
    base_path = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(base_path, "profiles.db")

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
                                display_name = item # Fallback name

                                try:
                                    with open(os.path.join(full_path, "Preferences"), 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        
                                        # Attempt to get Email and Real Name
                                        accounts = data.get('account_info', [])
                                        if accounts and len(accounts) > 0:
                                            email = accounts[0].get('email', 'Unknown')
                                            full_name = accounts[0].get('full_name', '')
                                            given_name = accounts[0].get('given_name', '')
                                            
                                            if full_name: display_name = full_name
                                            elif given_name: display_name = given_name
                                            
                                        # Fallback to Profile Name if no account info
                                        if display_name == item:
                                            prof_name = data.get('profile', {}).get('name', '')
                                            if prof_name: display_name = prof_name

                                except Exception as e:
                                    pass

                                if not email: email = None

                                self.add_profile(display_name, email, item)
                                new_count += 1
        except Exception as e:
            print(f"Error scanning: {e}")
            
        return new_count

    def close(self):
        self.session.close()