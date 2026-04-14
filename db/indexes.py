"""MongoDB index definitions for all interview bot collections."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel

from db.collections import (
    INTERVIEW_FEEDBACK,
    INTERVIEW_RESPONSES,
    INTERVIEWERS,
    INTERVIEWS,
)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all required indexes. Call once at app startup."""

    await db[INTERVIEWERS].create_indexes([
        IndexModel([("agent_id", ASCENDING)], unique=True),
    ])

    await db[INTERVIEWS].create_indexes([
        IndexModel([("interview_token", ASCENDING)], unique=True),
        IndexModel([("application_id", ASCENDING)]),
        IndexModel([("hr_id", ASCENDING)]),
        IndexModel([
            ("candidate_id", ASCENDING),
            ("is_active", ASCENDING),
        ]),
    ])

    await db[INTERVIEW_RESPONSES].create_indexes([
        IndexModel([("call_id", ASCENDING)], unique=True),
        IndexModel([("interview_id", ASCENDING)]),
        IndexModel([("candidate_id", ASCENDING)]),
        IndexModel([
            ("interview_id", ASCENDING),
            ("is_ended", ASCENDING),
        ]),
    ])

    await db[INTERVIEW_FEEDBACK].create_indexes([
        IndexModel([("interview_id", ASCENDING)]),
    ])
