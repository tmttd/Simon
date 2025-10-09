from typing import List
from pydantic import BaseModel, Field

class LearningPath(BaseModel):
    title: str = Field(description="복습 세션의 핵심 주제를 하나의 구로 요약하는 제목. 순서에 따라 1, 2, 3, 4, 5 등 번호를 매길 것. ex) 대명사의 이해")
    initial_message: str = Field(description="""환영 인사 및 해당 복습 세션 시작을 알리는 최초 메세지. 환영 인사와 함께 현재 세션의 주제를 언급하고, '준비되셨으면 "시작"이라고 입력해주세요'라는 문구로 반드시 마무리할 것.""")

class LearningPaths(BaseModel):
    subject: str = Field(description="모든 복습 세션의 핵심 주제를 요약한 짦은 한 문장.")
    learning_paths: List[LearningPath] = Field(description="사용자의 입력에서 추출된 복습 세션들의 목록") 