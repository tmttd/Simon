from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .ai_connector import get_ai_response
from .models import ChatMessage, Thread


class ChatAgentView(APIView):
    """사용자의 채팅 메시지를 받아 AI의 응답을 반환합니다."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:
        user_message = request.data.get('message')
        thread_id = request.data.get('thread_id')

        if not user_message:
            return Response(
                {'error': '사용자 메세지가 누락되었습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if thread_id:
                thread, created = Thread.objects.get_or_create(
                    id=thread_id,
                    defaults={'user': request.user, 'title': user_message[:20]}
                )
                if not created and thread.user != request.user:
                    return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
            else:
                # 새 대화: 첫 메시지의 일부를 제목으로 사용
                title = user_message[:20] 
                thread = Thread.objects.create(user=request.user, title=title)

            ChatMessage.objects.create(
                user=request.user,
                thread=thread,
                sender='user',
                message=user_message,
            )

            start_time = timezone.now()
            ai_response = get_ai_response(user_message, str(thread.id))
            end_time = timezone.now()
            response_duration = (end_time - start_time).total_seconds()

            ChatMessage.objects.create(
                user=request.user,
                thread=thread,
                sender='ai',
                message=ai_response,
                duration=response_duration
            )

            return Response({
                'response': ai_response,
                'thread_id': thread.id # 새 대화인 경우 thread_id 반환
            }, status=status.HTTP_200_OK)
        
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
            # Foreign Key 관계를 통해 메시지 조회
            messages = ChatMessage.objects.filter(
                user=request.user,
                thread__id=thread_id
            ).order_by('timestamp')
            
            history = [
                {'sender': msg.sender, 'text': msg.message, 'duration': msg.duration if msg.duration is not None else 0}
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
            threads = Thread.objects.filter(
                user=request.user, 
                is_deleted=False
            ).values('id', 'title').order_by('-updated_at')

            return Response(list(threads), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ThreadDetailView(APIView):
    """특정 대화(thread)를 수정하거나 삭제합니다."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, thread_id, *args, **kwargs) -> Response:
        """대화 제목을 수정합니다."""
        thread = get_object_or_404(Thread, id=thread_id, user=request.user)
        new_title = request.data.get('title')
        if not new_title:
            return Response(
                {'error': '제목이 누락되었습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        thread.title = new_title
        thread.save()
        return Response({'id': thread.id, 'title': thread.title}, status=status.HTTP_200_OK)

    def delete(self, request, thread_id, *args, **kwargs) -> Response:
        """대화를 삭제 처리(soft delete)합니다."""
        thread = get_object_or_404(Thread, id=thread_id, user=request.user)
        thread.is_deleted = True
        thread.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


