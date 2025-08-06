import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB 접속 관련 정보
MONGODB_URI = os.environ.get("MONGODB_URI")

# LLM 관련 정보
LLM_MODEL_NAME = "gemini-2.5-flash"
THINKING_MODEL_NAME = "gemini-2.5-pro"
TEMPERATURE = 0.6

# 개인 당뇨 관리 profile
ISR = 6.5
CF = 35
TARGET = 120


# Documnet Retriever 구성 정보
PERSIST_DIRECTORY = 'C:/Users/pqstv/bluetorch/insuLin_Guide/agent/chroma_db'
COLLECTION_NAME = 'nutrition_facts'
QUERY_EMBEDDING_MODEL_NAME = 'solar-embedding-1-large-query'
DOCUMENT_EMBEDDING_MODEL_NAME = 'solar-embedding-1-large-passage'
