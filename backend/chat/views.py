from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .ai_connector import get_ai_response
from .models import ChatMessage


class ChatAgentView(APIView):
    """사용자의 채팅 메시지를 받아 AI의 응답을 반환합니다."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:
        user_message = request.data.get('message')
        # TODO: thread_id를 사용자 세션이나 다른 방식으로 관리하도록 수정 필요
        thread_id = request.data.get('thread_id', 'test_1') 

        if not user_message:
            return Response(
                {'error': '사용자 메세지가 누락되었습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # DB에 사용자 메세지 저장
            ChatMessage.objects.create(
                thread_id=thread_id,
                sender='user',
                message=user_message,
            )

            # AI 응답 가져오기
            ai_response = get_ai_response(user_message, thread_id)

            # DB에 AI 메세지 저장
            ChatMessage.objects.create(
                thread_id=thread_id,
                sender='ai',
                message=ai_response
            )

            return Response({'response': ai_response}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatHistoryView(APIView):
    """특정 대화(thread)의 전체 대화 기록을 반환합니다."""
    permission_classes = [IsAuthenticated]

    def get(self, request, thread_id, *args, **kwargs) -> Response:
        try:
            # DB에서 해당 thread_id의 모든 메시지를 시간순으로 조회
            messages = ChatMessage.objects.filter(thread_id=thread_id).order_by('timestamp')
            
            # 프론트엔드에서 사용할 형태로 데이터 직렬화
            history = [
                {'sender': msg.sender, 'text': msg.message}
                for msg in messages
            ]

            return Response({'history': history}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )