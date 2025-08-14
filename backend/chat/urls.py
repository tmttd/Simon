from django.urls import path
from . import views

urlpatterns = [
    path('ask/', views.chat_with_agent, name='chat_with_agent'),
    path('history/<str:thread_id>/', views.get_chat_history, name='get_chat_history'),
]