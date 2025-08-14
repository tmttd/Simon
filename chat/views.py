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