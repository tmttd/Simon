from typing import TypedDict, Sequence, Annotated, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph.message import add_messages

# 생성 순서: 

#  0. 모든 agent가 공유할 AgentState의 스키마 정의
#  1. prompt 정의
#  2. 모델 생성(필요시 bind_tools까지)
#  3. (필요시) PydanticOutputParser 구성
#  4. (1), (2), (3)을 묶는 chain 생성
#  5. chain을 실행하는 함수 생성

from .prompts import triage_prompt, information_prompt, factor_prompt, answering_prompt
from .prompts import factor_parser
from ..utils import prepare_context_data
from ..tools import nutrition_retriever_tool, insulin_calculation
from ..settings import LLM_MODEL_NAME, THINKING_MODEL_NAME, TEMPERATURE


# 노드 전체가 공유할 데이터의 스키마인 state 설정
class AgentState(TypedDict):
    # 사용자와 모델의 대화 history
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 대화 모드
    dialogue_mode: Optional[str]

    # 각종 보정 계수들
    factors: Optional[dict]

    # 최종 계산된 인슐린
    calculation_result: Optional[str]

    # 음식 영양 성분
    nutrition_facts: Optional[dict]


# 모델 생성
llm = ChatGoogleGenerativeAI(
    model=LLM_MODEL_NAME,
    temperature=TEMPERATURE
)

# 1. 분류 노드 생성을 위한 파츠(triage_node)
# triage 에이전트 생성
triage_agent = triage_prompt | llm

# triage 에이전트 생성 함수 생성(=노드)
def call_triage_agent(state: AgentState):
    """사용자의 입력을 받아 의도를 세 가지(식사 인슐린 계산, 교정 인슐린 계산, 일반 질문) 중 하나로 분류합니다."""
    
    last_message = state['messages'][-1]

    output = triage_agent.invoke(
        {"messages": [last_message]}
        )

    return {"dialogue_mode": output.content}

# 대화 mode에 따라 분기를 설정하는 함수
# workflow.py에서 conditional_edge에 사용됩니다.
def set_mode(state:AgentState) -> str:

    if state['dialogue_mode']:
        return state['dialogue_mode']
    else:
        return 'end'
    
# 그래프 진입점을 dialogue_mode에 따라 선택하는 함수
def entry_point_routing(state:AgentState) -> str:
    """그래프의 진입점을 선택합니다. 상태의 dialogue_mode가 None일 경우 triage_node로, meal이나 correction이면 information_node로
    query면 agent_node로"""

    if not state.get('dialogue_mode'):
        return 'triage_node'
    elif state['dialogue_mode'] in ["meal", "correction"]:
        return "information_node"
    else:
        return "answer_node"

    

# 2. 정보 수집 노드를 위한 파츠(information_node)
information_agent = information_prompt | llm.bind_tools([nutrition_retriever_tool])

# call_information_agent 함수 생성
def call_information_agent(state:AgentState):

    output = information_agent.invoke({
        "messages": state['messages']
    })

    return {"messages": [output]}

# 정보 수집 루프를 계속할지 결정하는 함수
# workflow.py에서 conditional_edge에 사용됩니다.
def continue_information_gathering(state:AgentState) -> str:
    last_message = state['messages'][-1]

    # 도구를 호출했다면 당연히 한 번 더 진행.
    if last_message.tool_calls:
        return "nutrition"
    
    if "complete" in last_message.content:
        return "complete"
    
    else:
        return "continue"
        
    
# 3. 계수 설정 노드를 위한 파츠(factor_node)
# factor_agent 객체를 생성합니다.
factor_agent = (
    factor_prompt 
    | llm
    | factor_parser
)

# factor_agent 호출 함수를 생성합니다.
def call_factor_agent(state:AgentState):
    """state의 모든 대화 기록을 제공하여 필요한 보정 계수들을 생성하는 함수입니다."""

    # 1. 컨텍스트 데이터 준비
    context_data = prepare_context_data()

    # 2. 메시지 필터링
    all_messages = state.get('messages') # .get()을 사용해 더 안전하게 접근

    # all_messages가 None인지 확인
    if all_messages is None:
        # 임시로 빈 리스트를 할당하여 오류를 피하게 할 수 있습니다.
        all_messages = [] 

    messages_for_llm = [
        msg for msg in all_messages
        if not (isinstance(msg, AIMessage) and msg.content.strip().lower() == "complete")
    ]

    # 3. LLM 입력 데이터 구성
    input_data = {
        "messages": messages_for_llm,
        "time": context_data.get('time'),
        "blood_sugar": context_data.get('blood_sugar'),
        "iob": context_data.get('iob')
    }

    # 4. LLM 호출 및 결과 확인
    try:
        output = factor_agent.invoke(input_data)
    except Exception as e:
        raise e # 오류를 다시 발생시켜서 실행을 중단합니다.

    # 5. 최종 반환값 확인
    result = {"factors": output.dict()}
    return result

# 4. 최종 답변 생성 노드를 위한 파츠(answer_node)
answering_agent = answering_prompt | llm

# 에이전트 호출 함수
def call_answering_agent(state:AgentState) -> dict:
    """
    지금까지 수집된 모든 정보(대화, 계수, 계산결과)를 종합하여
    사용자에게 보여줄 최종 답변을 생성합니다.
    """
    print("--- 최종 답변 생성 중 ---")
    
    # 상태에서 필요한 모든 정보를 추출합니다.
    factors = state.get('factors', {})
    calculation_result = state.get('calculation_result', "계산 결과를 찾을 수 없습니다.")
    
    # LLM에게 전달할 입력 데이터를 구성합니다.
    # 딕셔너리인 factors를 문자열로 변환하여 LLM이 쉽게 읽도록 합니다.
    input_data = {
        "messages": state['messages'],
        "factors": str(factors),
        "calculation_result": calculation_result
    }

    # Answering Agent를 호출하여 최종 답변을 생성합니다.
    final_answer = answering_agent.invoke(input_data)

    # 생성된 답변을 대화 기록에 추가합니다.
    return {"messages": [final_answer]}


# 5. 영양 성분 검색 노드를 위한 파츠
def call_nutirion_agent(state:AgentState):

    last_message = state['messages'][-1]

    tool_args = last_message.tool_calls[0]['args']

    result = nutrition_retriever_tool.invoke(tool_args)

    return {
        "messages": 
        [ToolMessage(
            content=str(result), 
            tool_call_id=last_message.tool_calls[0]['id'])
        ]}


# 6. 최종 인슐린 용량 계산을 위한 노드의 파츠
def call_insulin_agent(state: AgentState) -> dict:
    """
    state['factors']에 준비된 모든 인자를 사용하여 insulin_calculation 도구를 호출하고
    결과를 calculation_result에 저장합니다.
    """
    
    # 1. Factor_agent가 준비한 모든 인자를 가져옵니다.
    calculation_args = state.get('factors')
    
    if not calculation_args:
        # 혹시 모를 예외 처리
        return {"calculation_result": "오류: 계산에 필요한 정보가 준비되지 않았습니다."}
        
    # 2. 'insulin_calculation' 도구를 ** (언패킹)을 사용하여 호출합니다.
    #    이렇게 하면 딕셔너리의 키가 함수의 파라미터 이름과 일치하여 자동으로 매핑됩니다.
    result_string = insulin_calculation.invoke(calculation_args)
    
    # 3. 결과를 상태에 저장합니다.
    return {"calculation_result": result_string}


# 7. 모든 해결 과정을 종결하는 초기화 노드의 파츠
# 문제가 해결되면 dialogue_mode를 None으로 초기화합니다.
def call_cleanup_node(state: AgentState) -> dict:
    """
    하나의 작업 사이클이 끝났을 때, 다음 대화를 위해 상태를 초기화합니다.
    구체적으로 dialogue_mode를 None으로 설정합니다.
    """
    print("--- A task cycle is complete. Cleaning up state. ---")
    return {"dialogue_mode": None}