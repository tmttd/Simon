import os
from langchain_upstage import UpstageEmbeddings
from langchain_chroma import Chroma

# settings.py에서 ChromaDB 경로를 임포트합니다.
from .settings import CHROMA_DB_PATH_UPSTAGE

# --- ChromaDB 및 검색 임베딩 모델 초기화 ---
# LangGraph 에이전트 외부에서 한 번만 초기화하도록 전역 변수로 설정합니다.
# 이 초기화 로직은 'tools.py' 모듈이 로드될 때 실행됩니다.
document_retriever = None

if "UPSTAGE_API_KEY" in os.environ and os.path.exists(CHROMA_DB_PATH_UPSTAGE):
    try:
        query_embeddings = UpstageEmbeddings(model="solar-embedding-1-large-query")
        document_retriever = Chroma(
            persist_directory=CHROMA_DB_PATH_UPSTAGE,
            embedding_function=query_embeddings
        )
        print(f"✅ tools.py: document_retriever(ChromaDB)가 '{CHROMA_DB_PATH_UPSTAGE}'에서 로드되었습니다.")
    except Exception as e:
        print(f"❌ tools.py: ChromaDB 로드 중 오류 발생: {e}")
        document_retriever = None
else:
    print("❌ tools.py: 'UPSTAGE_API_KEY'가 없거나 ChromaDB 경로가 유효하지 않아 document_retriever를 로드할 수 없습니다.")
    document_retriever = None

print("✅ tools.py: 도구 모듈 로드 완료.")