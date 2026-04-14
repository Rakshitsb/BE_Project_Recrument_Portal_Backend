"""Seed default interviewers. Run: python -m scripts.seed_interviewers"""

import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from db.collections import INTERVIEWERS

def _build_seed_data() -> list[dict]:
    if not settings.RETELL_AGENT_ID_LISA or not settings.RETELL_AGENT_ID_BOB:
        missing = []
        if not settings.RETELL_AGENT_ID_LISA:
            missing.append("RETELL_AGENT_ID_LISA")
        if not settings.RETELL_AGENT_ID_BOB:
            missing.append("RETELL_AGENT_ID_BOB")
        raise RuntimeError(
            "Missing Retell interviewer agent IDs in .env: "
            + ", ".join(missing)
        )

    return [
        {
            "agent_id": settings.RETELL_AGENT_ID_LISA,
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
            "agent_id": settings.RETELL_AGENT_ID_BOB,
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
        for item in _build_seed_data():
            existing = await col.find_one({"name": item["name"]})
            if existing:
                await col.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": {
                            **item,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
                print(f"Updated: {item['name']}")
                continue

            item["created_at"] = datetime.now(timezone.utc)
            await col.insert_one(item)
            print(f"Seeded: {item['name']}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
