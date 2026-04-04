import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"])


async def seed_admin():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("DB_NAME")]
    existing = await db.users.find_one({"email": "admin@portal.com"})
    if existing:
        print("Admin already exists")
        return
    await db.users.insert_one(
        {
            "name": "Admin",
            "email": "admin@portal.com",
            "hashed_password": pwd_context.hash("admin123"),
            "role": "admin",
            "created_at": datetime.utcnow(),
        }
    )
    print("Admin seeded successfully")


asyncio.run(seed_admin())
