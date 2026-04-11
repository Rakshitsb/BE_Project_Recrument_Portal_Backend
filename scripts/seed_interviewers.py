"""Seed default interviewers. Run: python -m scripts.seed_interviewers"""

import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from db.collections import INTERVIEWERS

SEED_DATA: list[dict] = [
    {
        "agent_id": "REPLACE_WITH_RETELL_AGENT_ID_LISA",
        "name": "Explorer Lisa",
        "description": (
            "Hi! I'm Lisa, an enthusiastic and empathetic"
            " interviewer who loves to explore. With a perfect"
            " balance of empathy and rapport, I delve deep into"
            " conversations while maintaining a steady pace."
        ),
        "image": "/interviewers/Lisa.png",
        "audio": "Lisa.wav",
        "empathy": 7,
        "exploration": 10,
        "rapport": 7,
        "speed": 5,
    },
    {
        "agent_id": "REPLACE_WITH_RETELL_AGENT_ID_BOB",
        "name": "Empathetic Bob",
        "description": (
            "Hi! I'm Bob, your go-to empathetic interviewer."
            " I excel at understanding and connecting with"
            " people on a deeper level, ensuring every"
            " conversation is insightful and meaningful."
        ),
        "image": "/interviewers/Bob.png",
        "audio": "Bob.wav",
        "empathy": 10,
        "exploration": 7,
        "rapport": 7,
        "speed": 5,
    },
]


async def main() -> None:
    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        db = client[settings.DB_NAME]
        col = db[INTERVIEWERS]
        for item in SEED_DATA:
            exists = await col.find_one(
                {"agent_id": item["agent_id"]}
            )
            if exists:
                print(f"Skipped (already exists): {item['name']}")
                continue
            item["created_at"] = datetime.now(timezone.utc)
            await col.insert_one(item)
            print(f"Seeded: {item['name']}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
