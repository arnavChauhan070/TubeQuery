import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

EMBEDDING_MODEL = "models/gemini-embedding-001"
CHAT_MODEL = "gemini-3.5-flash-lite"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RETRIEVAL_K = 5
RETRIEVER_SEARCH_TYPE = "similarity"

VECTOR_STORE_BATCH_SIZE = 40

