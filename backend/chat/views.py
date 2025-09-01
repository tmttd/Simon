from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Min

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
            # DB에 사용자 메세지 저장 (현재 로그인한 user와 연결)
            ChatMessage.objects.create(
                user=request.user,
                thread_id=thread_id,
                sender='user',
                message=user_message,
            )

            # AI 응답 가져오기
            ai_response = get_ai_response(user_message, thread_id)

            # DB에 AI 메세지 저장 (현재 로그인한 user와 연결)
            ChatMessage.objects.create(
                user=request.user,
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
            # 현재 로그인한 사용자의 메시지만 조회하도록 user 필터 추가
            messages = ChatMessage.objects.filter(
                user=request.user,
                thread_id=thread_id
            ).order_by('timestamp')
            
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


class ThreadListView(APIView):
    """현재 로그인한 사용자의 모든 대화(thread) 목록을 반환합니다."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs) -> Response:
        try:
            # 1. 현재 사용자의 메시지 중 삭제되지 않은 것만 필터링합니다.
            # 2. `thread_id`로 그룹화하고, 각 그룹의 첫 메시지 시간(Min('timestamp'))을 계산합니다.
            # 3. 첫 메시지 시간을 기준으로 최신순(-first_message_time)으로 정렬합니다.
            # 4. 정렬된 순서대로 `thread_id` 값만 가져옵니다.
            threads_query = ChatMessage.objects.filter(
                user=request.user,
                is_deleted=False
            ).values('thread_id').annotate(
                first_message_time=Min('timestamp')
            ).order_by('-first_message_time').values_list('thread_id', flat=True)
            
            # 2. 각 thread_id를 순회하며 제목을 부여합니다.
            threads = []
            # 전체 스레드 수를 기반으로 역순으로 번호를 매깁니다.
            total_threads = len(threads_query)
            for i, thread_id in enumerate(threads_query):
                threads.append({
                    'id': thread_id,
                    'title': f'대화 {total_threads - i}'
                })

            return Response(threads, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )