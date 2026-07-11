from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from core.config import settings
from bson.codec_options import CodecOptions
import pytz

client = AsyncMongoClient(settings.MONGO_URI)
db = client.get_database(
    "note_tube_db",
    codec_options=CodecOptions(
        tz_aware=True,
        tzinfo=pytz.timezone('Asia/Kolkata')
    )
)

def get_user_collection() -> AsyncCollection:
    return db["users"]

def get_otp_collection() -> AsyncCollection:
    return db["otp_verification"]

def get_group_collection() -> AsyncCollection:
    return db["groups"]

def get_subgroup_collection() -> AsyncCollection:
    return db["subgroups"]

def get_tutorial_collection() -> AsyncCollection:
    return db["tutorials"]

def get_note_collection() -> AsyncCollection:
    return db["notes"]

def get_chat_collection() -> AsyncCollection:
    return db["chats"]

def get_quiz_collection() -> AsyncCollection:
    return db["quizzes"]

async def setup_indexes():
    """Create necessary database indexes."""
    users_coll = get_user_collection()
    otp_coll = get_otp_collection()
    groups_coll = get_group_collection()
    subgroups_coll = get_subgroup_collection()
    tutorials_coll = get_tutorial_collection()
    notes_coll = get_note_collection()

    # Index on email for users (unique)
    await users_coll.create_index("email", unique=True)
    
    # Index on email for OTPs
    await otp_coll.create_index("email")
    
    # TTL Index on OTPs (expires after 2 minutes)
    await otp_coll.create_index("createdAt", expireAfterSeconds=120)
    
    # Unique compound index for Groups (user_id + group_name)
    await groups_coll.create_index([("user_id", 1), ("group_name", 1)], unique=True)
    
    # Unique compound index for SubGroups (group_id + subgroup_name)
    await subgroups_coll.create_index([("group_id", 1), ("subgroup_name", 1)], unique=True)
    
    # Simple indexes for faster querying
    await groups_coll.create_index("user_id")
    await subgroups_coll.create_index("group_id")
    await tutorials_coll.create_index("user_id")
    await tutorials_coll.create_index("group_id")
    await tutorials_coll.create_index("subgroup_id")
    await tutorials_coll.create_index([("user_id", 1), ("url", 1)])
    await notes_coll.create_index("tutorial_id")
    
    chats_coll = get_chat_collection()
    await chats_coll.create_index("tutorial_id")
    
    quizzes_coll = get_quiz_collection()
    await quizzes_coll.create_index("tutorial_id")
    
    print("Database indexes setup completed.")
