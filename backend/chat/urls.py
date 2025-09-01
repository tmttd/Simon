from django.urls import path
from .views import ChatAgentView, ChatHistoryView, ThreadListView

urlpatterns = [
    path('ask/', ChatAgentView.as_view(), name='chat_with_agent'),
    path('history/<str:thread_id>/', ChatHistoryView.as_view(), name='get_chat_history'),
    path('threads/', ThreadListView.as_view(), name='thread_list'),
]