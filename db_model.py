from sqlalchemy import create_engine, String, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import datetime
import enum
import os

# 1. Define the Database File
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "profiles.db")

engine = create_engine(f"sqlite:///{DB_FILE}", echo=False)
Session = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class MembershipLevel(enum.Enum):
    MEMBER = "Member"
    SILVER = "Silver"
    GOLD = "Gold"

class Profile(Base):
    __tablename__ = "profiles"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Profile Name: e.g., "Personal 1"
    name: Mapped[str] = mapped_column(String(100), unique=True)

    # Email Address: e.g., "example@outlook.com"
    # nullable=True allows us to save a profile even if we don't know the email yet
    email: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Edge Folder: e.g., "Profile 1"
    edge_profile_directory: Mapped[str] = mapped_column(String(100))
    
    # Membership Status
    membership: Mapped[MembershipLevel] = mapped_column(default=MembershipLevel.MEMBER)
    
    # Available Points (from Dashboard)
    available_points: Mapped[int] = mapped_column(Integer, default=0)
    
    # Last Run Timestamp
    last_run: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Profile(name={self.name}, email={self.email})>"

def init_db():
    # This creates the tables defined above
    Base.metadata.create_all(engine)
    print(f"Database initialized at: {DB_FILE}")

if __name__ == "__main__":
    # If the file exists, we print a warning so you know to delete it if the schema changed
    if os.path.exists(DB_FILE):
        print(f"Note: {DB_FILE} already exists.") 
    init_db()