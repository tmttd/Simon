from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

## 4. Workflow(그래프 구조) 생성

# * 그래프 생성(작업 흐름) 및 컴파일을 통해 `app`을 만듭니다!

# * 작업순서:
#   1. `StateGraph(AgentState)` 초기화
#   2. `add_node`를 통해 node 추가
#   3. `set_entry_point`를 통해 시작 지점 설정
#   4. `conditional_edge`의 분기 판단을 위한 함수 생성
#   5. `add_edge`를 통해 분기 없이 진행되는 경우 설정
#   6. `END`와 연결하며 workflow 마무리

from .nodes.nodes import (
    AgentState, set_mode, entry_point_routing, continue_information_gathering,
    call_triage_agent, call_information_agent, call_factor_agent, call_answering_agent,
    call_nutirion_agent, call_insulin_agent, call_cleanup_node, call_cleanup_node,)


# workflow 클래스 생성
workflow = StateGraph(AgentState)

# 노드 생성 및 추가
workflow.add_node("triage_node", call_triage_agent)
workflow.add_node("information_node", call_information_agent)
workflow.add_node("factor_node", call_factor_agent)
workflow.add_node("nutrition_node", call_nutirion_agent)
workflow.add_node("insulin_node", call_insulin_agent)
workflow.add_node("answer_node", call_answering_agent)
workflow.add_node("cleanup_node", call_cleanup_node)

# 엣지 생성(workflow 흐름 설계)
workflow.set_conditional_entry_point(
    entry_point_routing,
    {
        "triage_node": "triage_node",
        "information_node": "information_node",
        "answer_node": "answer_node" 
    }
)
workflow.add_conditional_edges(
    "triage_node",
    set_mode,
    {
        "meal": "information_node",
        "correction": "information_node",
        "query": "answer_node"
    }
)
workflow.add_conditional_edges(
    "information_node",
    continue_information_gathering,
    {
        "nutrition": "nutrition_node",
        "continue": END,
        "complete": "factor_node"
    }
)
workflow.add_edge("nutrition_node", "information_node")
workflow.add_edge("factor_node", "insulin_node")
workflow.add_edge("insulin_node", "answer_node")
workflow.add_edge("answer_node", "cleanup_node")
workflow.add_edge("cleanup_node", END)

# 메모리는 MemorySaver에 저장합니다. state를 저장한다는 의미입니다.
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

print("WorkFlow 생성 완료!! ^^; b")