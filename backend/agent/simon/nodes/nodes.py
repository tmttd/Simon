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
# 도구 모듈에서 document_retriever를 가져옵니다.
from ..tools import document_retriever
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


# --- 헬퍼 함수: 규칙 기반 판단 ---

def check_move_to_quiz_by_rules(messages: list) -> str:
    """
    사용자 입력 기반으로 퀴즈 전환을 판단합니다.
    사용자가 '/퀴즈' 또는 '퀴즈 시작' 입력하면 즉시 전환.
    """
    if len(messages) < 1:
        return "unclear"
    
    # 마지막 사용자 메시지 찾기
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content.lower()
            break
    
    # 사용자 명령어 키워드 체크
    quiz_commands = ["/퀴즈", "/quiz", "퀴즈 시작", "퀴즈시작"]
    if any(cmd in last_user_msg for cmd in quiz_commands):
        print(f"   [규칙 판단] 사용자가 퀴즈 명령어 입력 → move_to_quiz")
        return "move_to_quiz"
    
    return "unclear"

def check_finish_path_by_rules(messages: list) -> str:
    """
    사용자 입력 기반으로 학습 경로 완료를 판단합니다.
    사용자가 '/다음' 또는 '다음으로' 입력하면 즉시 완료.
    """
    if len(messages) < 1:
        return "unclear"
    
    # 마지막 사용자 메시지 찾기
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content.lower()
            break
    
    # 사용자 명령어 키워드 체크
    next_commands = ["/다음", "/next", "다음으로", "다음단계"]
    if any(cmd in last_user_msg for cmd in next_commands):
        print(f"   [규칙 판단] 사용자가 다음 단계 명령어 입력 → finish_path")
        return "finish_path"
    
    return "unclear"

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
    
    # ChromaDB에서 전체 학습 내용에 대한 참고 자료 검색 (한 번만)
    reference_text = ""
    if document_retriever:
        try:
            # 전체 주제 + 모든 학습 경로의 제목을 합쳐서 하나의 쿼리 생성
            all_titles = " ".join([path.title for path in pydantic_response.learning_paths])
            combined_query = f"{pydantic_response.subject} {all_titles}"
            
            print(f"-> ChromaDB 검색 쿼리: {combined_query[:100]}...")
            
            # k=3개 문서 검색
            retrieved_docs = document_retriever.similarity_search_with_score(combined_query, k=3)
            
            # 검색 결과를 포맷팅
            reference_text = "# 학습 교안\n\n"
            for doc_idx, (doc, score) in enumerate(retrieved_docs):
                reference_text += f"## 참고 자료 {doc_idx+1}\n\n"
                reference_text += f"{doc.page_content}\n\n"
                
                # 검색된 문서 정보 로그 출력
                preview = doc.page_content[:100].replace('\n', ' ')
                doc_id = getattr(doc, 'id', 'N/A')
                metadata = getattr(doc, 'metadata', {})
                print(f"   문서 {doc_idx+1}:")
                print(f"      - 유사도: {score:.4f}")
                print(f"      - ID: {doc_id}")
                print(f"      - 메타데이터: {metadata}")
                print(f"      - 내용: {preview}...")
            
            print(f"-> ChromaDB 검색 완료: 총 {len(retrieved_docs)}개 문서")
            
        except Exception as e:
            print(f"-> 경고: ChromaDB 검색 중 오류 발생: {e}")
            reference_text = f"# 참고 자료\n\n검색 실패: {str(e)}"
    else:
        print("-> 경고: document_retriever를 사용할 수 없습니다.")
        reference_text = "# 참고 자료\n\n(retriever 사용 불가)"
    
    # 최종 상태 로그 출력
    print(f"\n-> initial_classifier 완료: 상태 초기화")
    print(f"   - 학습 경로 개수: {len(pydantic_response.learning_paths)}")
    print(f"   - 교안 길이: {len(reference_text)}자")
    
    # 메시지 구성: 교안을 먼저 제공
    initial_messages = [user_message]
    
    # 교안을 AIMessage로 추가 (한 번만)
    if reference_text:
        reference_message = AIMessage(
            content=f"학습을 시작하기 전에, 전체 학습에 필요한 교안을 먼저 확인해주세요:\n\n{reference_text}"
        )
        initial_messages.append(reference_message)
        print(f"   - 전체 학습 교안을 AIMessage로 추가했습니다.")
    
    # initial_message 추가 (환영 메시지)
    initial_messages.append(AIMessage(content=pydantic_response.initial_message))
    
    return {
        "full_curriculum": pydantic_response,
        "current_path_index": 0,
        "current_task": "instruct",
        "session_finished": False,
        "messages": initial_messages,
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

    # 프롬프트 변수 준비
    prompt_variables = {
        "task": state.get("current_task", "instruct"),
        "all_paths": all_paths_str,
        "subject": curriculum.subject,
        "path_title": current_path.title,
        "messages": state["messages"],
    }
    
    # 체인 실행
    ai_response_text = explanation_chain.invoke(prompt_variables)
    
    print(f"-> instructor: '{current_path.title}'에 대한 설명 생성 완료.")
    
    return {"messages": [AIMessage(content=ai_response_text)]}

def decide_after_instructor(state: AgentState) -> dict:
    """instructor의 설명을 바탕으로 다음 행동(추가 설명 or 퀴즈)을 결정합니다."""
    print("--- 노드 실행: decide_after_instructor (하이브리드 판단) ---")

    # 1단계: 규칙 기반 판단
    rule_decision = check_move_to_quiz_by_rules(state["messages"])
    
    if rule_decision != "unclear":
        # 규칙으로 명확히 판단됨
        next_task = "test" if rule_decision == "move_to_quiz" else "instruct"
        
        if next_task == "test":
            print("-> 결정자(instructor): [규칙 기반] 설명 완료. 다음 작업을 'test'로 설정합니다.")
        else:
            print("-> 결정자(instructor): [규칙 기반] 추가 설명 필요. 다음 작업을 'instruct'로 유지합니다.")
        
        return {"current_task": next_task}
    
    # 2단계: LLM 판단 (애매한 경우)
    print("   [LLM에 위임] 규칙으로 판단 불가, LLM 분류 시작...")
    
    classifier_chain = DECIDE_AFTER_INSTRUCTOR_PROMPT | gpt_5_mini.with_structured_output(InstructorDecision)
    decision = classifier_chain.invoke({"messages_for_classification": state["messages"]})
    
    next_task = "test" if decision.next_action == "move_to_quiz" else "instruct"
    
    if next_task == "test":
        print("-> 결정자(instructor): [LLM 기반] 설명 완료. 다음 작업을 'test'로 설정합니다.")
    else:
        print("-> 결정자(instructor): [LLM 기반] 추가 설명 필요. 다음 작업을 'instruct'로 유지합니다.")

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
    print("--- 노드 실행: decide_after_tester (하이브리드 판단) ---")

    path_idx = state["current_path_index"]
    curriculum = state['full_curriculum']

    # 1단계: 규칙 기반 판단
    rule_decision = check_finish_path_by_rules(state["messages"])
    
    next_action = None
    
    if rule_decision != "unclear":
        # 규칙으로 명확히 판단됨
        next_action = rule_decision
        
        if next_action == "finish_path":
            print("-> 결정자(tester): [규칙 기반] 테스트 완료. 다음 학습 경로로 이동합니다.")
        else:
            print("-> 결정자(tester): [규칙 기반] 테스트 계속 진행. 다음 작업을 'test'로 유지합니다.")
    else:
        # 2단계: LLM 판단 (애매한 경우)
        print("   [LLM에 위임] 규칙으로 판단 불가, LLM 분류 시작...")
        
        classifier_chain = DECIDE_AFTER_TESTER_PROMPT | gpt_5_mini.with_structured_output(TesterDecision)
        decision = classifier_chain.invoke({"messages_for_classification": state["messages"]})
        next_action = decision.next_action
        
        if next_action == "finish_path":
            print("-> 결정자(tester): [LLM 기반] 테스트 완료. 다음 학습 경로로 이동합니다.")
        else:
            print("-> 결정자(tester): [LLM 기반] 테스트 계속 진행. 다음 작업을 'test'로 유지합니다.")
    
    # 판단 결과에 따라 처리
    if next_action == "finish_path":
        current_path_title = curriculum.learning_paths[path_idx].title
        print(f"-> '{current_path_title}' 학습을 완료 처리합니다.")
        
        # 현재 학습 경로 완료 처리
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
    else:  # continue_quiz
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