# simon 패키지가 임포트될 때 실행되는 초기화 코드
print("✅ simon/__init__.py: 'simon' 패키지 초기화 중...")

# 선택적으로, 자주 사용되는 모듈이나 클래스를 패키지 레벨로 노출할 수 있습니다.
# 예를 들어, LangGraph Agent 객체를 직접적으로 임포트할 수 있도록
# from .workflow import simon_agent
# 또는 상태 정의를 위해
# from .nodes.nodes import AgentState, LearningPaths

# 현재는 단순히 패키지 초기화를 알리는 메시지만 포함합니다.
# 추후 필요에 따라 내용 추가 가능합니다.