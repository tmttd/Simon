from django.urls import path
from .views import (
    ChatAgentView, ChatHistoryView, ThreadListView, ThreadDetailView,
    Simon_InitialClassiferView, StudyGroupDetailView, StudyGroupListView, StudyGroupCreateView,
)

urlpatterns = [
    path('ask/', ChatAgentView.as_view(), name='chat_with_agent'),
    path('history/<uuid:thread_id>/', ChatHistoryView.as_view(), name='get_chat_history'),
    path('threads/', ThreadListView.as_view(), name='thread_list'),
    path('thread/<uuid:thread_id>/', ThreadDetailView.as_view(), name='thread_detail'),
    path('classify/', Simon_InitialClassiferView.as_view(), name='classify_bootstrap'),
    path('groups/', StudyGroupListView.as_view(), name='study_group_list'),
    path('groups/create/', StudyGroupCreateView.as_view(), name='study_group_create'),
    path('group/<uuid:group_id>/', StudyGroupDetailView.as_view(), name='study_group_detail'),
]