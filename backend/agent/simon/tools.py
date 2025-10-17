# import os
# from langchain_upstage import UpstageEmbeddings
# from langchain_chroma import Chroma
# from langchain_core.documents import Document # 툴의 반환 타입 정의에는 직접 사용되지 않지만, 컨텍스트 상 필요할 수 있음
# from langchain_core.tools import tool # tool 데코레이터를 import 합니다.

# # settings.py에서 ChromaDB 경로를 임포트합니다.
# from .settings import CHROMA_DB_PATH_UPSTAGE

# # --- ChromaDB 및 검색 임베딩 모델 초기화 ---
# # LangGraph 에이전트 외부에서 한 번만 초기화하도록 전역 변수로 설정합니다.
# # 이 초기화 로직은 'tools.py' 모듈이 로드될 때 실행됩니다.
# query_embeddings_for_retriever = None
# vectorstore_for_retriever = None

# if "UPSTAGE_API_KEY" in os.environ and os.path.exists(CHROMA_DB_PATH_UPSTAGE):
#     try:
#         query_embeddings_for_retriever = UpstageEmbeddings(model="solar-embedding-1-large-query")
#         vectorstore_for_retriever = Chroma(
#             persist_directory=CHROMA_DB_PATH_UPSTAGE,
#             embedding_function=query_embeddings_for_retriever
#         )
#         print(f"✅ tools.py: ChromaDB 및 검색 임베딩 모델이 '{CHROMA_DB_PATH_UPSTAGE}'에서 로드되었습니다.")
#     except Exception as e:
#         print(f"❌ tools.py: ChromaDB 로드 중 오류 발생: {e}")
#         vectorstore_for_retriever = None # 오류 발생 시 retriever 사용 불가 상태 표시
# else:
#     print("❌ tools.py: 'UPSTAGE_API_KEY'가 없거나 ChromaDB 경로가 유효하지 않아 retriever를 로드할 수 없습니다.")
#     vectorstore_for_retriever = None # retriever 사용 불가 상태 표시

# @tool
# def document_retriever(query: str) -> str:
#     """
#     사용자의 질문과 관련된 한국어 문법 문서(Chunk)를 검색합니다.
#     주어진 'query'에 가장 관련성이 높은 'k'개의 문서 텍스트를 반환합니다.
#     검색 결과는 한국어 문법에 대한 설명이나 예시를 포함할 수 있습니다.
#     """
#     if vectorstore_for_retriever is None:
#         return "문서 검색 시스템이 초기화되지 않았습니다. 관리자에게 문의해주세요."
    
#     print(f"--- Tool Call: document_retriever 실행 (쿼리: '{query}') ---")
#     retrieved_docs = vectorstore_for_retriever.similarity_search(query, k=5)
    
#     if not retrieved_docs:
#         print(f"--- Tool Call: document_retriever 결과: 관련 문서 없음 ---")
#         return "죄송합니다. 관련 문서를 찾을 수 없습니다."

#     # 검색된 문서 내용을 하나의 문자열로 결합
#     formatted_docs = []
#     for i, doc in enumerate(retrieved_docs):
#         # 문서 내용 앞에 출처 정보를 추가
#         source_info = f"[[문서 출처: {doc.metadata.get('source', '알 수 없음')}, Chunk Index: {doc.metadata.get('chunk_index', '알 수 없음')}]]"
#         formatted_docs.append(f"{source_info}\n{doc.page_content.strip()}")
        
#     print(f"--- Tool Call: document_retriever 결과: {len(retrieved_docs)}개의 문서 검색됨 ---")
#     return "\n\n---\n\n".join(formatted_docs)