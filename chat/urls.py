from django.urls import path
from . import views

urlpatterns = [
    path('ask/', views.chat_with_agent, name='chat_with_agent')
]