from langchain_core.messages import AIMessage, HumanMessage

from .workflow import app

if __name__ == "__main__":

    # 1. 대화를 위한 고유 ID 설정
    config = {"configurable": {"thread_id": "test_1"}}

    # 2. 대화 관리 루프 시작
    while True:
        try:
            # 사용자로부터 입력을 받습니다.
            user_input = input("당신: ")
            if user_input.lower() == "exit":
                break

            # 그래프에 전달할 입력.
            # ★★★ 핵심: 전체 대화 기록이 아닌, '이번 턴의 사용자 입력'만 전달합니다. ★★★
            inputs = {"messages": [HumanMessage(content=user_input)]}

            # app.stream을 사용하여 AI의 응답을 실시간으로 출력합니다.
            print("AI: ", end="", flush=True)
            for chunk in app.stream(inputs, config=config):
                # 청크 전체를 출력하여 어떤 노드가 실행되었는지 확인
                print("----- NEW CHUNK -----")
                print(chunk)
                print("---------------------")
                # chunk는 {'node_name': {'state_key': ...}} 형태의 딕셔너리입니다.
                # .values()를 사용하여 내부 딕셔너리 (상태 업데이트)에 접근합니다.
                for state_update in chunk.values():
                    
                    # 이제 상태 업데이트 딕셔너리에 'messages' 키가 있는지 확인합니다.
                    if "messages" in state_update:
                        
                        # 새로 추가된 메시지가 있다면, 그 내용을 출력합니다.
                        last_message = state_update["messages"][-1]
                        
                        # AIMessage이면서, 내용이 비어있지 않은 경우에만 출력합니다.
                        if isinstance(last_message, AIMessage) and last_message.content:
                            print(last_message.content, end="", flush=True)
                        
                        print()

        except KeyboardInterrupt:
            print("\n\n대화를 종료합니다.")
            break
        except Exception as e:
            print(f"\n오류가 발생했습니다: {e}")
            break