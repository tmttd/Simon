from django.db import models
from django.conf import settings
import uuid

class Thread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_threads'
    )
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} by {self.user.username}"

    class Meta:
        ordering = ['-created_at']

class ChatMessage(models.Model):
    # 이 메시지가 속한 사용자
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='chat_messages'
    )

    # 대화 고유 id
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    SENDER_CHOICES = [
        ( 'ai', 'AI' ),
        ( 'user', '사용자' ),
    ]

    # 대화 주체
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)

    # 메세지 본문
    message = models.TextField()

    # 메세지가 생성된 시각(자동으로 현재 시간으로 업데이트 됨.)
    timestamp = models.DateTimeField(auto_now_add=True)

    # 삭제 여부 (Soft Delete)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H-%M')}] {self.sender}: {self.message[:30]}"
    
    class Meta:
        ordering = ['timestamp']