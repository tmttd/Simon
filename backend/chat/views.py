from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .ai_connector import get_ai_response
from .models import ChatMessage
import json

@csrf_exempt
def chat_with_agent(request) -> JsonResponse:
    """사용자의 채팅을 body로 담은 POST 요청이 들어오면 ai의 메세지를 반환합니다."""

    if request.method == "POST":
        try:
            # 요청의 body를 json으로 파싱합니다.
            data = json.loads(request.body)
            user_message = data.get('message')

            # 대화의 식별 id인 thread_id를 생성합니다.
            thread_id = data.get('thread_id', 'test_1')

            # 필수 값이 없는 경우 오류를 반환합니다.
            if not user_message:
                return JsonResponse('error', '사용자 메세지가 누락되었습니다.', status=400)

            # DB에 사용자 메세지를 저장합니다.
            ChatMessage.objects.create(
                thread_id=thread_id,
                sender='user',
                message=user_message,
            )

            # ai의 응답을 반환합니다.
            ai_response = get_ai_response(user_message, thread_id)

            # DB에 AI 메세지를 저장합니다.
            ChatMessage.objects.create(
                thread_id=thread_id,
                sender='ai',
                message=ai_response
            )

            return JsonResponse({'response': ai_response})
        
        except json.JSONDecodeError:
            return JsonResponse({'error', '잘못된 JSON 형식입니다.'}, status=400)
        except Exception as e:
            return JsonResponse({'error', f'서버 내부 오류 {e}'}, status=500)

    return JsonResponse({'error': 'POST요청만 지원합니다.'}, status=405)

@csrf_exempt
def get_chat_history(request, thread_id):
    """클라이언트로부터 전송된 thread_id를 바탕으로 
    chatMessage객체의 List를 DB에서 찾아 JSON 형태로 반환합니다."""

    if request.method == "GET":
        try:
            # DB에서 해당 thread_id에 해당하는 모든 객체를 추출하기.
            messages = ChatMessage.objects.filter(thread_id=thread_id).order_by('timestamp')
            
            # 프론트엔드(React)에서 활용할 수 있도록 Dictionary의 List로 만들기
            history = [
                {'sender': msg.sender,
                'text': msg.message}
                for msg in messages
            ]

            return JsonResponse({'history': history})
        except Exception as e:
            return JsonResponse({'error': f'서버 내부 오류: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': "GET 요청만 지원하는 엔드포인트입니다."}, status=405)