import asyncio
import os
import sys

# Add backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import get_settings
from app.db.connection import init_db
from app.models.user import User
from app.models.organization import Organization
from app.core.security import get_password_hash

async def create_admin():
    settings = get_settings()
    
    print("Connecting to MongoDB...")
    await init_db(settings)
    
    email = "admin@buildknowledge.ai"
    password = "ChangeMe123!"
    
    existing_admin = await User.find_one({"email": email})
    if existing_admin:
        print(f"Admin user {email} already exists!")
        return
        
    org = Organization(name="Build Knowledge Administration", subscription_tier="enterprise")
    await org.insert()
    
    admin = User(
        email=email,
        full_name="System Administrator",
        hashed_password=get_password_hash(password),
        organization_id=str(org.id),
        role="Administrator"
    )
    await admin.insert()
    
    org.owner_id = str(admin.id)
    await org.save()
    
    print(f"Successfully created default administrator.")
    print(f"Email: {email}")
    print(f"Password: {password}")

if __name__ == "__main__":
    asyncio.run(create_admin())
