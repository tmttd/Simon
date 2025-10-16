from langchain_core.messages import HumanMessage, AIMessage
from agent.simon.workflow import simon_agent


def get_ai_response(user_message: str, thread_id: str, is_first_turn: bool = False, files=None) -> str:
    """
    사용자의 메세지를 받아 ai의 응답을 가져오는 함수.

    Args:
        user_message: 사용자가 입력한 메세지
        thread_id: 대화를 식별하기 위한 고유 id
        is_first_turn: 해당 thread의 첫 턴 여부. 첫 턴이면 user_text/files로 초기화
        files: 첫 턴에 전달할 업로드 파일 바이트 리스트(선택)

    Returns:
        final_response: ai의 답변
    """

    config = {"configurable": {"thread_id": thread_id}}

    # 첫 턴이면 initial_classifier가 기대하는 입력 형식으로 전달
    if is_first_turn:
        inputs = {"user_text": user_message, "files": files}
    else:
        inputs = {"messages": [HumanMessage(content=user_message)]}

    final_response = ""
    for chunk in simon_agent.stream(inputs, config=config):
        for state_update in chunk.values():
            if "messages" in state_update:
                last_message = state_update['messages'][-1]
                if isinstance(last_message, AIMessage) and last_message.content:
                    final_response += last_message.content
    
    return final_response if final_response else "죄송합니다. 오류가 발생하여 응답을 생성하지 못했습니다."