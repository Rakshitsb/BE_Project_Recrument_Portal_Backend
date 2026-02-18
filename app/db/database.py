from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("DATABASE_URL")

if not MONGO_URL:
    raise ValueError("DATABASE_URL not found")

# Sync Database (PyMongo) - REQUIRED for legacy modules (auth, user, resume)
client = MongoClient(MONGO_URL)
db = client.hr_portal

user_collection = db.users
job_collection = db.jobs
application_collection = db.applications
candidate_collection = db.candidates

# Async Database (Motor) - For new HR Job APIs
async_client = AsyncIOMotorClient(MONGO_URL)
async_db = async_client.hr_portal

async_user_collection = async_db.users
async_job_collection = async_db.jobs
async_application_collection = async_db.applications
async_candidate_collection = async_db.candidates

print("Database connected successfully")
