from typing import List, Union
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from .prompts import parser
from .chain import prepare

load_dotenv()

def initiate_learning_session(files: List[Union[str, bytes]], user_text: str):
    """다중 이미지 + 텍스트를 받아 학습 세션 분할 결과를 반환"""
    # input 값 생성
    input_msg = prepare(files, user_text)

    # llm 객체 생성
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=1.0,
    )

    # 모델 호출 및 파싱
    print("AI가 학습 세션을 생성 중입니다...")
    ai_response = llm.invoke([input_msg])
    parsed = parser.parse(ai_response.content)
    return parsed

if __name__ == "__main__":
    FILES = ['backend/agent/classify/test_note_2.png', 'backend/agent/classify/test_note.jpg']
    USER_TEXT = "체언에 대한 복습을 자세하게 도와 줘."

    result = initiate_learning_session(FILES, USER_TEXT)
    print("\n--- 생성된 복습 세션 ---")
    print(f"전체 요약 문장: {result.subject}")
    for lp in result.learning_paths:
        print(f"제목: {lp.title}")
        print(f"첫 메세지: {lp.initial_message}")
        print("-" * 20)