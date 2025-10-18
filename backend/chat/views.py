from adrf.views import APIView  # Async Django REST Framework
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from asgiref.sync import sync_to_async
from .ai_connector import get_ai_response
from .models import ChatMessage, Thread, StudySession
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q
from agent.simon.workflow import simon_agent
from langchain_core.messages import HumanMessage
from agent.simon.nodes.nodes import LearningPaths
from agent.simon.nodes.prompts import INITIAL_CLASSIFIER_PROMPT
from agent.simon.settings import gemini_flash_8
from agent.simon.utils import prepare_contents
import json


class ChatAgentView(APIView):
    """사용자의 채팅 메시지를 받아 AI의 응답을 반환합니다."""
    permission_classes = [IsAuthenticated]
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    async def post(self, request, *args, **kwargs) -> Response:
        user_message = request.data.get('message')
        thread_id = request.data.get('thread_id')
        session_id = request.data.get('session_id')

        if not user_message:
            return Response(
                {'error': '사용자 메세지가 누락되었습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 세션 파라미터가 있으면 유효성 체크 (비동기)
            session = None
            if session_id:
                try:
                    session = await sync_to_async(StudySession.objects.get)(id=session_id, user=request.user, is_deleted=False)
                except StudySession.DoesNotExist:
                    return Response({'error': '세션이 존재하지 않거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

            if thread_id:
                # Thread 조회를 비동기로 래핑
                thread, created = await sync_to_async(Thread.objects.get_or_create)(
                    id=thread_id,
                    defaults={'user': request.user, 'title': user_message[:20], 'session': session}
                )
                if not created and thread.user != request.user:
                    return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
                # 기존 스레드에 세션이 없고 유효한 세션이 전달되면 지정
                if session and thread.session_id is None:
                    thread.session = session
                    await sync_to_async(thread.save)()
            else:
                # 새 대화: 첫 메시지의 일부를 제목으로 사용 (비동기)
                title = user_message[:20]
                thread = await sync_to_async(Thread.objects.create)(user=request.user, title=title, session=session)

            # 첫 턴 여부 계산 (비동기)
            is_first_turn = not await sync_to_async(ChatMessage.objects.filter(thread=thread).exists)()

            # 첫 턴에 업로드된 파일 있으면 바이트 리스트로 수집
            files = None
            if is_first_turn:
                upload_list = request.FILES.getlist('files')
                if upload_list:
                    files = [f.read() for f in upload_list]

            # 사용자 메시지 저장 (비동기)
            await sync_to_async(ChatMessage.objects.create)(
                user=request.user,
                thread=thread,
                sender='user',
                message=user_message,
            )

            start_time = timezone.now()
            # AI 호출을 비동기로 래핑 - 핵심!
            ai_response = await sync_to_async(get_ai_response)(user_message, str(thread.id), is_first_turn=is_first_turn, files=files)
            end_time = timezone.now()
            response_duration = (end_time - start_time).total_seconds()

            # AI 응답 저장 (비동기)
            await sync_to_async(ChatMessage.objects.create)(
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

    async def get(self, request, thread_id, *args, **kwargs) -> Response:
        try:
            # Foreign Key 관계를 통해 메시지 조회 (비동기)
            messages = await sync_to_async(list)(
                ChatMessage.objects.filter(
                    user=request.user,
                    thread__id=thread_id
                ).order_by('timestamp')
            )
            
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

    async def get(self, request, *args, **kwargs) -> Response:
        try:
            qs = Thread.objects.filter(user=request.user, is_deleted=False)
            # ?ungrouped=1 이면 세션 없는 스레드만 → 오래된 순(오름차순)
            if request.query_params.get('ungrouped') in ('1', 'true', 'True'):
                qs = qs.filter(session__isnull=True).order_by('updated_at')
            else:
                # 그 외 목록은 기존처럼 최신순
                qs = qs.order_by('-updated_at')
            # 비동기로 조회
            threads = await sync_to_async(list)(qs.values('id', 'title', 'session_id', 'updated_at'))
            return Response(threads, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class Simon_InitialClassiferView(APIView):
    """텍스트/이미지 입력을 받아 학습 세션을 생성하고 초기 메시지를 시드합니다."""
    permission_classes = [IsAuthenticated]
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    async def post(self, request, *args, **kwargs) -> Response:
        try:
            note_text = request.data.get('note_text', '')
            files = request.FILES.getlist('files')

            file_bytes_list = []
            for f in files:
                file_bytes_list.append(f.read())

            # 1) 세션/스레드 생성 (비동기)
            session = await sync_to_async(StudySession.objects.create)(user=request.user, title='학습 세션')
            thread = await sync_to_async(Thread.objects.create)(user=request.user, session=session, title='학습 세션')

            # 2) LangGraph를 통해 해당 thread_id로 초기 분류 실행 (비동기)
            config = {"configurable": {"thread_id": str(thread.id)}}
            inputs = {"user_text": note_text or None, "files": file_bytes_list or None}
            state = await sync_to_async(simon_agent.invoke)(inputs, config=config)

            # 3) 상태에서 커리큘럼/제목/초기 메시지 추출
            curriculum = state.get('full_curriculum')
            subject = None
            if curriculum is not None and hasattr(curriculum, 'model_dump'):
                subject = (curriculum.model_dump() or {}).get('subject')
            elif isinstance(curriculum, dict):
                subject = curriculum.get('subject')
            if subject:
                session.title = subject
                await sync_to_async(session.save)(update_fields=['title'])
                thread.title = subject[:200]
                await sync_to_async(thread.save)(update_fields=['title'])

            initial_message_text = ""
            try:
                msgs = state.get('messages') or []
                if msgs:
                    last = msgs[-1]
                    # last는 AIMessage일 것
                    initial_message_text = getattr(last, 'content', '') or ''
            except Exception:
                initial_message_text = ''

            if initial_message_text:
                await sync_to_async(ChatMessage.objects.create)(
                    user=request.user,
                    thread=thread,
                    sender='ai',
                    message=initial_message_text,
                )

            return Response({
                'session': {'id': str(session.id), 'title': session.title},
                'thread': {'id': str(thread.id), 'title': thread.title},
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudySessionDetailView(APIView):
    """특정 StudySession과 하위 스레드 목록을 반환합니다."""
    permission_classes = [IsAuthenticated]

    async def get(self, request, session_id, *args, **kwargs) -> Response:
        try:
            session = await sync_to_async(StudySession.objects.get)(id=session_id, user=request.user, is_deleted=False)
            # 세션 내부는 오래된 순(오름차순)
            threads = await sync_to_async(list)(
                Thread.objects.filter(
                    user=request.user, session=session, is_deleted=False
                ).values('id', 'title').order_by('updated_at')
            )
            return Response({
                'session': {'id': str(session.id), 'title': session.title},
                'threads': threads,
                'count': len(threads),
            }, status=status.HTTP_200_OK)
        except StudySession.DoesNotExist:
            return Response({'error': '존재하지 않거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def delete(self, request, session_id, *args, **kwargs) -> Response:
        """세션을 삭제(soft delete)하고 하위 스레드도 함께 삭제 처리합니다."""
        try:
            session = await sync_to_async(StudySession.objects.get)(id=session_id, user=request.user, is_deleted=False)
            session.is_deleted = True
            await sync_to_async(session.save)()
            # 하위 스레드 soft delete
            await sync_to_async(Thread.objects.filter(user=request.user, session=session, is_deleted=False).update)(is_deleted=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except StudySession.DoesNotExist:
            return Response({'error': '존재하지 않거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'서버 내부 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudySessionListView(APIView):
    """사용자의 StudySession 목록을 반환합니다."""
    permission_classes = [IsAuthenticated]

    async def get(self, request, *args, **kwargs) -> Response:
        try:
            sessions = await sync_to_async(list)(
                StudySession.objects
                .filter(user=request.user, is_deleted=False)
                .annotate(count=Count('threads', filter=Q(threads__is_deleted=False)))
                .values('id', 'title', 'count', 'created_at', 'updated_at')
                .order_by('-updated_at')
            )
            return Response(sessions, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'서버 내부 오류: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudySessionCreateView(APIView):
    """StudySession 생성"""
    permission_classes = [IsAuthenticated]

    async def post(self, request, *args, **kwargs) -> Response:
        title = request.data.get('title')
        if not title:
            return Response({'error': '제목이 누락되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        session = await sync_to_async(StudySession.objects.create)(user=request.user, title=title[:200])
        return Response({'id': str(session.id), 'title': session.title}, status=status.HTTP_201_CREATED)


class ThreadDetailView(APIView):
    """특정 대화(thread)를 수정하거나 삭제합니다."""
    permission_classes = [IsAuthenticated]

    async def patch(self, request, thread_id, *args, **kwargs) -> Response:
        """대화 제목 또는 세션 지정/해제를 수정합니다."""
        thread = await sync_to_async(get_object_or_404)(Thread, id=thread_id, user=request.user)
        new_title = request.data.get('title')
        session_id = request.data.get('session_id', None)

        if new_title is not None:
            thread.title = new_title

        if session_id is not None:
            if session_id in ('', 'null', None):
                thread.session = None
            else:
                try:
                    session = await sync_to_async(StudySession.objects.get)(id=session_id, user=request.user, is_deleted=False)
                except StudySession.DoesNotExist:
                    return Response({'error': '세션이 존재하지 않거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
                thread.session = session

        await sync_to_async(thread.save)()
        return Response({'id': thread.id, 'title': thread.title, 'session_id': str(thread.session.id) if thread.session else None}, status=status.HTTP_200_OK)

    async def delete(self, request, thread_id, *args, **kwargs) -> Response:
        """대화를 삭제 처리(soft delete)합니다."""
        thread = await sync_to_async(get_object_or_404)(Thread, id=thread_id, user=request.user)
        thread.is_deleted = True
        await sync_to_async(thread.save)()
        # 세션 내 모든 스레드가 삭제되었으면 세션도 자동 삭제 처리
        if thread.session_id:
            remaining = await sync_to_async(Thread.objects.filter(user=request.user, session_id=thread.session_id, is_deleted=False).exists)()
            if not remaining:
                try:
                    session = await sync_to_async(StudySession.objects.get)(id=thread.session_id, user=request.user)
                    session.is_deleted = True
                    await sync_to_async(session.save)()
                except StudySession.DoesNotExist:
                    pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatStateView(APIView):
    """LangGraph AgentState 요약을 반환합니다."""
    permission_classes = [IsAuthenticated]

    async def get(self, request, thread_id, *args, **kwargs) -> Response:
        try:
            config = {"configurable": {"thread_id": str(thread_id)}}
            snapshot = getattr(simon_agent, 'get_state', None)
            if snapshot is None:
                return Response({'error': '상태 조회를 지원하지 않습니다.'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            state_snapshot = await sync_to_async(simon_agent.get_state)(config)
            state = getattr(state_snapshot, 'values', None) or state_snapshot or {}

            curriculum = state.get('full_curriculum')
            subject = None
            learning_paths = []
            completed = False

            # BaseModel
            if curriculum is not None and hasattr(curriculum, 'model_dump'):
                curriculum_dict = curriculum.model_dump() or {}
                subject = curriculum_dict.get('subject')
                learning_paths = [
                    { 'title': lp.get('title'), 'completed': bool(lp.get('completed')) }
                    for lp in (curriculum_dict.get('learning_paths') or [])
                ]
                completed = bool(curriculum_dict.get('completed'))
            # dict
            elif isinstance(curriculum, dict):
                subject = curriculum.get('subject')
                learning_paths = [
                    { 'title': (lp or {}).get('title'), 'completed': bool((lp or {}).get('completed')) }
                    for lp in (curriculum.get('learning_paths') or [])
                ]
                completed = bool(curriculum.get('completed'))
            # JSON string
            elif isinstance(curriculum, str):
                try:
                    curriculum_dict = json.loads(curriculum)
                    subject = curriculum_dict.get('subject')
                    learning_paths = [
                        { 'title': (lp or {}).get('title'), 'completed': bool((lp or {}).get('completed')) }
                        for lp in (curriculum_dict.get('learning_paths') or [])
                    ]
                    completed = bool(curriculum_dict.get('completed'))
                except Exception:
                    pass

            summary = {
                'subject': subject,
                'learning_paths': learning_paths,
                'current_path_index': state.get('current_path_index'),
                'current_task': state.get('current_task'),
                'session_finished': bool(state.get('session_finished')),
            }
            return Response(summary, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'서버 내부 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


