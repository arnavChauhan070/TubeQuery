import asyncio
from pymongo import AsyncMongoClient
from config import DATABASE_PASSWORD
from fastapi import HTTPException

password = DATABASE_PASSWORD
mongo_url = f"mongodb+srv://arnavchauhan070_db_user:{password}@proejcts.svrzpfy.mongodb.net/"
client = AsyncMongoClient(mongo_url)

db = client["TubeQuery"]

user_collection = db["user"]
youtube_collection = db["youtube"]
question_collection = db["question"]

async def create_index():

    try:
        await user_collection.create_index(
            "email",
            unique = True
        )

        await youtube_collection.create_index(
            [
                ("user_id",1),
                ("video_url",1)
            ],
            unique = True
        )
    except Exception as e:
        raise HTTPException(status_code=404,detail="Index not Created!!")
    

