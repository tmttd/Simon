from django.urls import path
from .views import ChatAgentView, ChatHistoryView, ThreadListView, ThreadDetailView

urlpatterns = [
    path('ask/', ChatAgentView.as_view(), name='chat_with_agent'),
    path('history/<uuid:thread_id>/', ChatHistoryView.as_view(), name='get_chat_history'),
    path('threads/', ThreadListView.as_view(), name='thread_list'),
    path('thread/<uuid:thread_id>/', ThreadDetailView.as_view(), name='thread_detail'),
]