# --- 표준 라이브러리 및 외부 라이브러리 임포트 ---
from typing import Annotated, TypedDict, Optional, List, Union, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph.message import add_messages

# --- 로컬 모듈 임포트 ---
# 설정 파일에서 LLM 모델들을 가져옵니다.
from ..settings import gemini_flash_8, gpt_5_mini
# 유틸리티 함수를 가져옵니다.
from ..utils import prepare_contents
# 프롬프트 템플릿들을 가져옵니다.
from .prompts import (
    INITIAL_CLASSIFIER_PROMPT,
    INSTRUCTOR_PROMPT,
    DECIDE_AFTER_INSTRUCTOR_PROMPT,
    TESTER_PROMPT,
    DECIDE_AFTER_TESTER_PROMPT,
)

# --- Pydantic 데이터 모델 정의 ---

class LearningPath(BaseModel):
    """개별 학습 경로(세션)의 구조를 정의합니다."""
    title: str = Field(description="복습 세션의 핵심 주제를 하나의 구로 요약하는 제목. 순서에 따라 1, 2, 3, 4, 5 등 번호를 매길 것. ex) 대명사의 이해")
    completed: bool = Field(default=False, description="해당 학습 경로의 완료 여부")

class LearningPaths(BaseModel):
    """전체 학습 커리큘럼의 구조를 정의합니다."""
    subject: str = Field(description="모든 복습 세션의 핵심 주제를 요약한 짦은 한 문장.")
    learning_paths: List[LearningPath] = Field(description="사용자의 요청 및 입력을 바탕으로 추출된 복습 세션들의 목록")
    initial_message: str = Field(description="""환영 인사 및 해당 복습 세션 시작을 알리는 최초 메세지. 환영 인사와 함께 현재 세션의 주제를 언급하고, '준비되셨으면 "시작"이라고 입력해주세요'라는 문구로 반드시 마무리할 것.""")
    completed: bool = Field(default=False, description="전체 커리큘럼의 완료 여부")

class InstructorDecision(BaseModel):
    """'instructor'의 다음 행동을 결정합니다."""
    next_action: Literal["continue_explaining", "move_to_quiz"] = Field(
        description="설명이 충분하여 퀴즈로 넘어갈 준비가 되면 'move_to_quiz'를, 설명이나 질문/답변이 더 필요하면 'continue_explaining'을 선택하세요."
    )

class TesterDecision(BaseModel):
    """'tester'의 다음 행동을 결정합니다."""
    next_action: Literal["continue_quiz", "finish_path"] = Field(
        description="학생이 정답을 맞혔고 다음 단계로 넘어갈 준비가 되면 'finish_path'를, 퀴즈가 아직 진행 중이거나 오답에 대한 피드백이 필요하면 'continue_quiz'를 선택하세요."
    )

# --- LangGraph 상태(State) 정의 ---

class AgentState(TypedDict):
    """LangGraph 워크플로우 전체에서 공유되는 상태 객체입니다."""
    # 사용자 초기 입력
    files: Optional[List[Union[str, bytes]]]
    user_text: Optional[str]

    # 전체 대화 기록 (add_messages는 새 메시지를 기존 리스트에 추가)
    messages: Annotated[list, add_messages]
    
    # 전체 학습 계획 (전체 세션의 "Source of Truth")
    full_curriculum: Optional[LearningPaths]

    # 현재 실행 중인 LearningPath의 인덱스
    current_path_index: int

    # 현재 작업 (instruct, test)
    current_task: str

    # 세션 완전 종료 여부 플래그
    session_finished: bool


# --- LangGraph 노드(Node) 함수 정의 ---

def initial_classifier(state: AgentState) -> dict:
    """사용자의 최초 입력을 받아 전체 커리큘럼을 생성하고 상태를 초기화합니다."""
    print("--- 노드 실행: initial_classifier ---")

    # 체인 구성: 프롬프트와 Pydantic 출력을 지원하는 LLM 연결
    chain = INITIAL_CLASSIFIER_PROMPT | gemini_flash_8.with_structured_output(LearningPaths)

    # 사용자 입력 처리 및 HumanMessage 생성
    initial_files = state.get("files")
    initial_user_text = state.get("user_text")
    user_contents = prepare_contents(initial_files, initial_user_text)
    user_message = HumanMessage(content=user_contents)

    # 체인 실행
    pydantic_response = chain.invoke({"user_input_message_content": [user_message]})
    
    print("-> initial_classifier: 커리큘럼 생성 완료.")
    return {
        "full_curriculum": pydantic_response,
        "current_path_index": 0,
        "current_task": "instruct",
        "session_finished": False,
        "messages": [user_message, AIMessage(content=pydantic_response.initial_message)],
    }

def instructor(state: AgentState) -> dict:
    """'튜터' LLM이 현재 학습 경로에 대한 설명을 생성합니다."""
    print("--- 노드 실행: instructor ---")

    path_idx = state['current_path_index']
    curriculum = state['full_curriculum']
    current_path = curriculum.learning_paths[path_idx]
    all_paths_str = "\n".join(f"- {i+1}. {c.title} {'(현재 학습 중)' if i == path_idx else ''}" for i, c in enumerate(curriculum.learning_paths))

    # 체인 구성: 프롬프트, LLM, 문자열 출력 파서 연결
    explanation_chain = INSTRUCTOR_PROMPT | gemini_flash_8 | StrOutputParser()

    # 체인 실행
    ai_response_text = explanation_chain.invoke({
        "task": state.get("current_task", "instruct"),
        "all_paths": all_paths_str,
        "subject": curriculum.subject,
        "path_title": current_path.title,
        "messages": state["messages"],
    })
    
    print(f"-> instructor: '{current_path.title}'에 대한 설명 생성 완료.")
    return {"messages": [AIMessage(content=ai_response_text)]}

def decide_after_instructor(state: AgentState) -> dict:
    """instructor의 설명을 바탕으로 다음 행동(추가 설명 or 퀴즈)을 결정합니다."""
    print("--- 노드 실행: decide_after_instructor ---")

    # 체인 구성: 결정자 프롬프트와 Pydantic 출력을 지원하는 LLM 연결
    classifier_chain = DECIDE_AFTER_INSTRUCTOR_PROMPT | gpt_5_mini.with_structured_output(InstructorDecision)
    
    # 체인 실행
    decision = classifier_chain.invoke({"messages_for_classification": state["messages"]})
    
    next_task = "test" if decision.next_action == "move_to_quiz" else "instruct"
    
    if next_task == "test":
        print("-> 결정자(instructor): 설명 완료. 다음 작업을 'test'로 설정합니다.")
    else:
        print("-> 결정자(instructor): 추가 설명 필요. 다음 작업을 'instruct'로 유지합니다.")

    return {"current_task": next_task}

def tester(state: AgentState) -> dict:
    """'튜터' LLM이 퀴즈를 진행하고 학생의 답변을 평가합니다."""
    print("--- 노드 실행: tester ---")
    
    path_idx = state["current_path_index"]
    curriculum = state['full_curriculum']
    current_path = curriculum.learning_paths[path_idx]

    next_path_idx = path_idx + 1
    next_path_title = "없음 (이번이 마지막 학습입니다)"
    if next_path_idx < len(curriculum.learning_paths):
        next_path_title = curriculum.learning_paths[next_path_idx].title

    # 체인 구성
    tutor_chain = TESTER_PROMPT | gemini_flash_8 | StrOutputParser()
    ai_response_text = tutor_chain.invoke({
        "current_path_topic": current_path.title,
        "next_path_topic": next_path_title,
        "messages": state["messages"],
    })
    
    print(f"-> tester: '{current_path.title}'에 대한 퀴즈 진행/피드백 생성 완료.")
    
    # 세션이 종료된 경우 최종 메시지를 추가합니다.
    if state.get("session_finished"):
        final_message = ai_response_text + "\n\n축하합니다! 모든 학습 내용을 성공적으로 마치셨습니다. 이번 학습 세션을 종료하겠습니다."
        return {"messages": [AIMessage(content=final_message)]}
    else:
        return {"messages": [AIMessage(content=ai_response_text)]}

def decide_after_tester(state: AgentState) -> dict:
    """tester의 퀴즈 진행 상황을 바탕으로 다음 행동(퀴즈 계속 or 다음 경로)을 결정합니다."""
    print("--- 노드 실행: decide_after_tester ---")

    path_idx = state["current_path_index"]
    curriculum = state['full_curriculum']

    # 체인 구성
    classifier_chain = DECIDE_AFTER_TESTER_PROMPT | gpt_5_mini.with_structured_output(TesterDecision)
    decision = classifier_chain.invoke({"messages_for_classification": state["messages"]})
    
    if decision.next_action == "finish_path":
        current_path_title = curriculum.learning_paths[path_idx].title
        print(f"-> 결정자(tester): 테스트 완료. '{current_path_title}' 학습을 완료 처리합니다.")
        
        # 현재 학습 경로 완료 처리
        # Pydantic 모델은 불변(immutable)이므로 직접 수정하는 대신 복사본을 만들어 업데이트
        updated_curriculum = curriculum.copy(deep=True)
        updated_curriculum.learning_paths[path_idx].completed = True
        
        next_path_idx = path_idx + 1
        
        if next_path_idx < len(curriculum.learning_paths):
            next_path_title = curriculum.learning_paths[next_path_idx].title
            print(f"-> 다음 학습 경로 '{next_path_title}'(으)로 이동합니다.")
            return {
                "full_curriculum": updated_curriculum,
                "current_path_index": next_path_idx,
                "current_task": "instruct",
            }
        else:
            print("-> 모든 학습 경로가 완료되었습니다. 세션을 종료합니다.")
            updated_curriculum.completed = True
            return {
                "full_curriculum": updated_curriculum,
                "session_finished": True,
            }
    else: # continue_quiz
        print("-> 결정자(tester): 테스트 계속 진행. 다음 작업을 'test'로 유지합니다.")
        return {"current_task": "test"}

# --- 라우터(Router) 함수 정의 ---

def route_tasks(state: AgentState) -> str:
    """AgentState를 기반으로 다음에 실행할 노드를 결정합니다."""
    print("--- 라우터(route_tasks) 실행 ---")

    if "full_curriculum" not in state or state["full_curriculum"] is None:
        print("-> 라우팅: initial_classifier")
        return "initial_classifier"
    
    task = state.get("current_task")
    if task == "instruct":
        print("-> 라우팅: instructor")
        return "instructor"
    elif task == "test":
        print("-> 라우팅: tester")
        return "tester"
    else:
        print(f"-> 경고: 예상치 못한 작업({task})입니다. instructor로 라우팅합니다.")
        return "instructor"

print("✅ nodes/nodes.py: 상태, Pydantic 모델, 노드, 라우터 함수 정의 로드 완료.")