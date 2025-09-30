from typing import List
from pydantic import BaseModel, Field

class LearningPath(BaseModel):
    title: str = Field(description="복습 세션의 핵심 주제를 한 줄로 요약하는 제목. 순서에 따라 1, 2, 3, 4, 5 등 번호를 매길 것.")
    initial_message: str = Field(description="환영 인사 및 해당 복습 세션을 시작하기에 적합한 유도적 최초 메세지. 반드시 적절한 질문으로 마무리할 것.")

class LearningPaths(BaseModel):
    subject: str = Field(description="모든 복습 세션의 핵심 주제를 요약한 짦은 한 문장.")
    learning_paths: List[LearningPath] = Field(description="사용자의 입력에서 추출된 복습 세션들의 목록") 