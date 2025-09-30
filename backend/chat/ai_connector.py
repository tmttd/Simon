from langchain_core.messages import HumanMessage, AIMessage
from agent.simon.workflow import app

def get_ai_response(user_message:str, thread_id:str) -> str:
    """
    사용자의 메세지를 받아 ai의 응답을 가져오는 함수.

    Args:
        user_message: 사용자가 입력한 메세지
        id: 대화를 식별하기 위한 고유 id

    Returns:
        final_response: ai의 답변
    """

    config = {"configurable": {"thread_id": thread_id}}

    inputs = {"messages": [HumanMessage(content=user_message)]}


    final_response = ""
    for chunk in app.stream(inputs, config=config):
        for state_update in chunk.values():
            if "messages" in state_update:
                last_message = state_update['messages'][-1]
                if isinstance(last_message, AIMessage) and last_message.content:
                    final_response += last_message.content
    
    return final_response if final_response else "죄송합니다. 오류가 발생하여 응답을 생성하지 못했습니다."