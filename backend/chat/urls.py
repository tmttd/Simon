from django.urls import path
from .views import (
    ChatAgentView, ChatHistoryView, ThreadListView, ThreadDetailView,
    Simon_InitialClassiferView, StudySessionDetailView, StudySessionListView, StudySessionCreateView, ChatStateView,
)

urlpatterns = [
    path('ask/', ChatAgentView.as_view(), name='chat_with_agent'),
    path('history/<uuid:thread_id>/', ChatHistoryView.as_view(), name='get_chat_history'),
    path('threads/', ThreadListView.as_view(), name='thread_list'),
    path('thread/<uuid:thread_id>/', ThreadDetailView.as_view(), name='thread_detail'),
    path('classify/', Simon_InitialClassiferView.as_view(), name='classify_bootstrap'),
    path('sessions/', StudySessionListView.as_view(), name='study_session_list'),
    path('sessions/create/', StudySessionCreateView.as_view(), name='study_session_create'),
    path('session/<uuid:session_id>/', StudySessionDetailView.as_view(), name='study_session_detail'),
    path('state/<uuid:thread_id>/', ChatStateView.as_view(), name='chat_state'),
]