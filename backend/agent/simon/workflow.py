import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

# --- 로컬 모듈 임포트 ---
# 상태 정의, 노드 함수, 라우터 함수를 가져옵니다.
from simon.nodes.nodes import (
    AgentState,
    initial_classifier,
    instructor,
    decide_after_instructor,
    tester,
    decide_after_tester,
    route_tasks
)

def create_workflow() -> StateGraph:
    """
    Simon AI 에이전트의 StateGraph 워크플로우를 생성하고 구성합니다.
    
    Returns:
        구성된 StateGraph 객체. 컴파일 전 상태입니다.
    """
    # StateGraph 객체를 생성합니다. AgentState를 상태 스키마로 사용합니다.
    workflow = StateGraph(AgentState)

    # 1. 'worker' 노드들을 그래프에 추가합니다.
    # 각 노드는 (노드 이름, 실행할 함수) 형태로 추가됩니다.
    workflow.add_node("initial_classifier", initial_classifier)
    workflow.add_node("instructor", instructor)
    workflow.add_node("decide_after_instructor", decide_after_instructor)
    workflow.add_node("tester", tester)
    workflow.add_node("decide_after_tester", decide_after_tester)

    # 2. 라우터를 조건부 "진입점"으로 설정합니다.
    # route_tasks 함수의 반환값에 따라 시작 노드가 결정됩니다.
    workflow.set_conditional_entry_point(
        route_tasks,
        {
            "initial_classifier": "initial_classifier",
            "instructor": "instructor",
            "tester": "tester",
        }
    )

    # 3. 노드 간의 엣지(연결)를 정의합니다.
    
    # initial_classifier는 진입점에서 직접 호출되므로, 별도의 출발 엣지가 필요 없습니다.
    # initial_classifier 실행 후에는 상태가 업데이트되고, 다음 `invoke` 시 `route_tasks`가 
    # 'instructor'나 'tester'로 라우팅을 결정합니다.
    # (원본 코드에서는 이 부분에 대한 명시적 엣지가 없었고, 이것이 올바른 설계입니다.)
    
    # instructor 노드 실행 후에는 항상 decide_after_instructor 노드로 이동합니다.
    workflow.add_edge("instructor", "decide_after_instructor")
    
    # tester 노드 실행 후에는 항상 decide_after_tester 노드로 이동합니다.
    workflow.add_edge("tester", "decide_after_tester")

    # 결정자 노드(decide_after_instructor, decide_after_tester)는 상태만 업데이트합니다.
    # 이 노드들 다음에는 명시적인 엣지가 없습니다.
    # 대신 상태가 업데이트된 후, 다음 `invoke`가 들어올 때 다시 `route_tasks` 진입점을
    # 통해 다음 작업 노드('instructor' 또는 'tester')가 결정됩니다.
    # 세션이 종료('session_finished' == True)되면, END로 라우팅하는 로직은 
    # conditional entry point 또는 별도의 라우터에서 처리할 수 있으나,
    # 현재 구조에서는 사용자의 다음 입력이 없을 때 자연스럽게 종료됩니다.

    return workflow

# --- 워크플로우 컴파일 ---
# 1. PostgreSQL 데이터베이스 연결 정보 설정
# Django의 settings.py나 OS 환경 변수에서 연결 문자열을 가져옵니다.
conn_string = os.environ.get("POSTGRES_CONNECTION_STRING")
if not conn_string:
    raise ValueError("POSTGRES_CONNECTION_STRING 환경 변수가 설정되지 않았습니다. 예: 'postgresql+psycopg2://user:pass@host:port/dbname'")

# 2. PostgresSaver 인스턴스 생성 (암호화 serde 인자 없이)
checkpointer = PostgresSaver.from_conn_string(conn_string)

# 3. 데이터베이스 테이블 확인 및 생성
# LangGraph가 상태를 저장하는 데 필요한 테이블을 확인하고, 없으면 생성합니다.
# 애플리케이션이 시작될 때 한 번만 호출하면 됩니다.
checkpointer.setup()
print("✅ workflow.py: 데이터베이스 체크포인터 테이블 설정을 확인/완료했습니다.")

# 4. 워크플로우 그래프 생성 및 컴파일
# checkpointer를 연결하여 대화 상태가 DB에 저장되도록 합니다.
simon_graph = create_workflow()
simon_agent = simon_graph.compile(checkpointer=checkpointer)

print("✅ workflow.py: LangGraph 워크플로우 생성 및 PostgreSQL checkpointer로 컴파일 완료.")