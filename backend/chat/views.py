from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .ai_connector import get_ai_response
from .models import ChatMessage, Thread, StudyGroup
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count, Q


class ChatAgentView(APIView):
    """사용자의 채팅 메시지를 받아 AI의 응답을 반환합니다."""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs) -> Response:
        user_message = request.data.get('message')
        thread_id = request.data.get('thread_id')
        group_id = request.data.get('group_id')

        if not user_message:
            return Response(
                {'error': '사용자 메세지가 누락되었습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 그룹 파라미터가 있으면 유효성 체크
            group = None
            if group_id:
                try:
                    group = StudyGroup.objects.get(id=group_id, user=request.user, is_deleted=False)
                except StudyGroup.DoesNotExist:
                    return Response({'error': '그룹이 존재하지 않거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

            if thread_id:
                thread, created = Thread.objects.get_or_create(
                    id=thread_id,
                    defaults={'user': request.user, 'title': user_message[:20], 'group': group}
                )
                if not created and thread.user != request.user:
                    return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
                # 기존 스레드에 그룹이 없고 유효한 그룹이 전달되면 지정
                if group and thread.group_id is None:
                    thread.group = group
                    thread.save()
            else:
                # 새 대화: 첫 메시지의 일부를 제목으로 사용
                title = user_message[:20]
                thread = Thread.objects.create(user=request.user, title=title, group=group)

            # 첫 턴 여부 계산: 해당 스레드의 기존 메시지 존재 여부로 판단
            is_first_turn = not ChatMessage.objects.filter(thread=thread).exists()

            # 첫 턴에 업로드된 파일 있으면 바이트 리스트로 수집
            files = None
            if is_first_turn:
                upload_list = request.FILES.getlist('files')
                if upload_list:
                    files = [f.read() for f in upload_list]

            ChatMessage.objects.create(
                user=request.user,
                thread=thread,
                sender='user',
                message=user_message,
            )

            start_time = timezone.now()
            ai_response = get_ai_response(user_message, str(thread.id), is_first_turn=is_first_turn, files=files)
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
            qs = Thread.objects.filter(user=request.user, is_deleted=False)
            # ?ungrouped=1 이면 그룹 없는 스레드만 → 오래된 순(오름차순)
            if request.query_params.get('ungrouped') in ('1', 'true', 'True'):
                qs = qs.filter(group__isnull=True).order_by('updated_at')
            else:
                # 그 외 목록은 기존처럼 최신순
                qs = qs.order_by('-updated_at')
            threads = qs.values('id', 'title', 'group_id', 'updated_at')
            return Response(list(threads), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class Simon_InitialClassiferView(APIView):
    """텍스트/이미지 입력을 받아 학습 세션을 분할하고 그룹+스레드를 생성합니다."""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs) -> Response:
        try:
            note_text = request.data.get('note_text', '')
            files = request.FILES.getlist('files')

            file_bytes_list = []
            for f in files:
                file_bytes_list.append(f.read())

            # 분류 수행
            result = initiate_learning_session(file_bytes_list, note_text)

            # 그룹 생성
            group_title = getattr(result, 'subject', None) or '학습 세션 묶음'
            group = StudyGroup.objects.create(user=request.user, title=group_title)

            # 자식 스레드 생성 + 초기 메시지 시드
            threads_payload = []
            for item in result.learning_paths:
                thread = Thread.objects.create(
                    user=request.user,
                    group=group,
                    title=item.title[:200]
                )
                ChatMessage.objects.create(
                    user=request.user,
                    thread=thread,
                    sender='ai',
                    message=item.initial_message,
                )
                threads_payload.append({
                    'id': str(thread.id),
                    'title': thread.title,
                })

            return Response({
                'group': {'id': str(group.id), 'title': group.title},
                'threads': threads_payload,
                'count': len(threads_payload),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudyGroupDetailView(APIView):
    """특정 StudyGroup과 하위 스레드 목록을 반환합니다."""
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id, *args, **kwargs) -> Response:
        try:
            group = StudyGroup.objects.get(id=group_id, user=request.user, is_deleted=False)
            # 그룹 내부는 오래된 순(오름차순)
            threads = Thread.objects.filter(
                user=request.user, group=group, is_deleted=False
            ).values('id', 'title').order_by('updated_at')
            return Response({
                'group': {'id': str(group.id), 'title': group.title},
                'threads': list(threads),
                'count': len(threads),
            }, status=status.HTTP_200_OK)
        except StudyGroup.DoesNotExist:
            return Response({'error': '존재하지 않거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, group_id, *args, **kwargs) -> Response:
        """그룹을 삭제(soft delete)하고 하위 스레드도 함께 삭제 처리합니다."""
        try:
            group = StudyGroup.objects.get(id=group_id, user=request.user, is_deleted=False)
            group.is_deleted = True
            group.save()
            # 하위 스레드 soft delete
            Thread.objects.filter(user=request.user, group=group, is_deleted=False).update(is_deleted=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except StudyGroup.DoesNotExist:
            return Response({'error': '존재하지 않거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'서버 내부 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudyGroupListView(APIView):
    """사용자의 StudyGroup 목록을 반환합니다."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs) -> Response:
        try:
            groups = (
                StudyGroup.objects
                .filter(user=request.user, is_deleted=False)
                .annotate(count=Count('threads', filter=Q(threads__is_deleted=False)))
                .values('id', 'title', 'count', 'updated_at')
                .order_by('-updated_at')
            )
            return Response(list(groups), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudyGroupCreateView(APIView):
    """StudyGroup 생성"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:
        title = request.data.get('title')
        if not title:
            return Response({'error': '제목이 누락되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        group = StudyGroup.objects.create(user=request.user, title=title[:200])
        return Response({'id': str(group.id), 'title': group.title}, status=status.HTTP_201_CREATED)


class ThreadDetailView(APIView):
    """특정 대화(thread)를 수정하거나 삭제합니다."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, thread_id, *args, **kwargs) -> Response:
        """대화 제목 또는 그룹 지정/해제를 수정합니다."""
        thread = get_object_or_404(Thread, id=thread_id, user=request.user)
        new_title = request.data.get('title')
        group_id = request.data.get('group_id', None)

        if new_title is not None:
            thread.title = new_title

        if group_id is not None:
            if group_id in ('', 'null', None):
                thread.group = None
            else:
                try:
                    group = StudyGroup.objects.get(id=group_id, user=request.user, is_deleted=False)
                except StudyGroup.DoesNotExist:
                    return Response({'error': '그룹이 존재하지 않거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
                thread.group = group

        thread.save()
        return Response({'id': thread.id, 'title': thread.title, 'group_id': str(thread.group.id) if thread.group else None}, status=status.HTTP_200_OK)

    def delete(self, request, thread_id, *args, **kwargs) -> Response:
        """대화를 삭제 처리(soft delete)합니다."""
        thread = get_object_or_404(Thread, id=thread_id, user=request.user)
        thread.is_deleted = True
        thread.save()
        # 그룹 내 모든 스레드가 삭제되었으면 그룹도 자동 삭제 처리
        if thread.group_id:
            remaining = Thread.objects.filter(user=request.user, group_id=thread.group_id, is_deleted=False).exists()
            if not remaining:
                try:
                    group = StudyGroup.objects.get(id=thread.group_id, user=request.user)
                    group.is_deleted = True
                    group.save()
                except StudyGroup.DoesNotExist:
                    pass
        return Response(status=status.HTTP_204_NO_CONTENT)


