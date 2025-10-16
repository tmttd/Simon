from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# .env 파일에서 환경 변수를 로드합니다.
# 이 함수는 애플리케이션 시작 시 한 번만 호출되어야 합니다.
load_dotenv()

# --- LLM 모델 초기화 헬퍼 함수 ---
# 각 모델에 필요한 환경 변수가 설정되어 있는지 확인하고,
# 모델 초기화 과정에서 발생할 수 있는 오류를 처리합니다.

def _initialize_openai_llm(model_name: str, temperature: float):
    """OpenAI 모델을 초기화합니다."""
    if "OPENAI_API_KEY" not in os.environ:
        print(f"경고: 'OPENAI_API_KEY' 환경 변수가 설정되지 않아 {model_name} 모델을 초기화할 수 없습니다.")
        return None
    try:
        return ChatOpenAI(model=model_name, temperature=temperature)
    except Exception as e:
        print(f"오류: {model_name} 모델 초기화 중 오류 발생: {e}")
        return None

def _initialize_google_llm(model_name: str, temperature: float, **kwargs):
    """Google Generative AI 모델을 초기화합니다."""
    if "GOOGLE_API_KEY" not in os.environ:
        print(f"경고: 'GOOGLE_API_KEY' 환경 변수가 설정되지 않아 {model_name} 모델을 초기화할 수 없습니다.")
        return None
    try:
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature, **kwargs)
    except Exception as e:
        print(f"오류: {model_name} 모델 초기화 중 오류 발생: {e}")
        return None

# --- LLM 모델 인스턴스 ---
# 필요한 LLM 모델들을 미리 초기화하여 다른 모듈에서 임포트하여 사용할 수 있도록 합니다.

# Gemini 모델
gemini_flash_8 = _initialize_google_llm("gemini-2.5-flash", 0.8)
gemini_flash_0 = _initialize_google_llm("gemini-2.5-flash", 0.0)
gemini_pro = _initialize_google_llm("gemini-2.5-pro", 1.0)
gemini_flash_lite = _initialize_google_llm(
    "gemini-2.5-flash-lite",
    0.1,
    model_kwargs={
        "generation_config": {
            "thinking_config": {
                "thinking_budget": 0
            }
        }
    }
)

# OpenAI 모델 (결정자 모델은 낮은 temperature를 사용합니다)
gpt_5_mini = _initialize_openai_llm("gpt-5-mini-2025-08-07", 1)
gpt_5_nano = _initialize_openai_llm("gpt-5-nano-2025-08-07", 1)

# --- 기타 설정 ---

# ChromaDB를 저장한 디렉토리 경로 (이전 코드에서 정의된 경로 사용)
CHROMA_DB_PATH_UPSTAGE = "./korean_grammar_chroma_db"

print("✅ settings.py: LLM 모델 및 기타 환경 설정 로드 완료.")