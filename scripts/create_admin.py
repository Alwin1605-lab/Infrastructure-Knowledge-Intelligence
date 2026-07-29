"""Database seed script for Infrastructure Knowledge Intelligence.

Creates the default Administrator user and their Organization.
Run this script to initialize the database with an admin account.
"""

import asyncio
import os
import sys

# Add the backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.config import get_settings
from app.db.connection import init_db, close_db
from app.models.user import User
from app.models.organization import Organization
from app.core.security import get_password_hash

async def seed_admin():
    settings = get_settings()
    
    print("Initializing MongoDB connection...")
    await init_db(settings)
    
    try:
        admin_email = "admin@buildknowledge.ai"
        
        # Check if admin already exists
        existing_user = await User.find_one({"email": admin_email})
        if existing_user:
            print(f"Admin user '{admin_email}' already exists. Skipping.")
            return

        print("Creating Administrator Organization...")
        org = Organization(
            name="BuildKnowledge System Admin",
            domain="buildknowledge.ai",
            tier="Enterprise",
            max_workspaces=9999
        )
        await org.insert()
        
        print(f"Creating Administrator User '{admin_email}'...")
        admin_user = User(
            email=admin_email,
            full_name="System Administrator",
            organization_id=str(org.id),
            role="Administrator",
            password_hash=get_password_hash("admin123"), # Default password
            is_active=True
        )
        await admin_user.insert()
        
        print("Success! Admin seeded successfully.")
        print(f"Login: {admin_email}")
        print("Password: admin123")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        print("Closing MongoDB connection...")
        await close_db()


if __name__ == "__main__":
    asyncio.run(seed_admin())
