import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.user import User
import bcrypt
from app.config import get_settings

settings = get_settings()

async def seed_users():
    # Initialize DB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DATABASE], document_models=[User])

    users_to_create = [
        {
            "email": "engineer1@example.com",
            "full_name": "Senior Engineer",
            "password": "BuildTest!45",
            "role": "Engineer",
            "organization_id": "org-1"
        },
        {
            "email": "reviewer@example.com",
            "full_name": "Code Reviewer",
            "password": "CheckPlz890",
            "role": "Reviewer",
            "organization_id": "org-1"
        },
        {
            "email": "guest@example.com",
            "full_name": "Guest User",
            "password": "GuestAccess11",
            "role": "Guest",
            "organization_id": "org-1",
            "is_guest": True
        }
    ]
    
    for user_data in users_to_create:
        existing = await User.find_one(User.email == user_data["email"])
        if not existing:
            password = user_data.pop("password")
            user = User(
                **user_data,
                hashed_password=bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            )
            await user.insert()
            print(f"Created user: {user.email}")
        else:
            print(f"User {user_data['email']} already exists.")

if __name__ == "__main__":
    asyncio.run(seed_users())
