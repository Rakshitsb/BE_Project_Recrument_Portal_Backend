"""MongoDB index definitions for all collections — interview bot + chatbot sessions."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel

from db.collections import (
    CHATBOT_SESSIONS,
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

    # chatbot_sessions indexes (added in Prompt 4)
    await db[CHATBOT_SESSIONS].create_indexes([
        # One session per candidate-job pair — enforced at DB level
        IndexModel([("job_id", ASCENDING), ("candidate_id", ASCENDING)], unique=True),
        # Candidate listing their own sessions
        IndexModel([("candidate_id", ASCENDING)]),
        # HR listing all sessions on their jobs
        IndexModel([("hr_id", ASCENDING)]),
        # Fast filtering for active sessions
        IndexModel([("is_enabled", ASCENDING)]),
    ])
