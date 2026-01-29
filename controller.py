from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_model import Base, Profile, MembershipLevel
import os
import json

app_data_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'RewardsBotPro')
if not os.path.exists(app_data_dir):
    try:
        os.makedirs(app_data_dir)
    except OSError: pass

DB_NAME = os.path.join(app_data_dir, "profiles.db")
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
        local_app_data = os.getenv('LOCALAPPDATA')
        if not local_app_data: return 0
        edge_user_data = os.path.join(local_app_data, 'Microsoft', 'Edge', 'User Data')
        if not os.path.exists(edge_user_data): return 0

        existing_dirs = {p.edge_profile_directory for p in self.get_all_profiles()}
        new_count = 0
        
        try:
            for item in os.listdir(edge_user_data):
                if item == "Default" or item.startswith("Profile "):
                    full_path = os.path.join(edge_user_data, item)
                    if os.path.isdir(full_path):
                        pref_path = os.path.join(full_path, "Preferences")
                        if os.path.exists(pref_path):
                            if item not in existing_dirs:
                                
                                # --- IMPROVED NAME PARSING ---
                                display_name = item # Fallback
                                email = "Unknown"
                                
                                try:
                                    with open(pref_path, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        
                                        # Attempt to get Email
                                        accounts = data.get('account_info', [])
                                        if accounts and len(accounts) > 0:
                                            email = accounts[0].get('email', 'Unknown')
                                            
                                            # Attempt to get Real Name from account
                                            full_name = accounts[0].get('full_name', '')
                                            given_name = accounts[0].get('given_name', '')
                                            
                                            if full_name: display_name = full_name
                                            elif given_name: display_name = given_name
                                            
                                        # Fallback to Profile Name if no account info
                                        if display_name == item:
                                            prof_name = data.get('profile', {}).get('name', '')
                                            if prof_name: display_name = prof_name

                                except Exception as e: 
                                    print(f"Error parsing JSON for {item}: {e}")

                                if not email: email = None
                                self.add_profile(display_name, email, item)
                                new_count += 1
        except Exception as e:
            print(f"Error scanning: {e}")
        return new_count

    def close(self): self.session.close()