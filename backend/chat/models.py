from django.db import models

class ChatMessage(models.Model):
    # 대화 고유 id
    thread_id = models.CharField(max_length=100, db_index=True)

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

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H-%M')}] {self.sender}: {self.message[:30]}"
    
    class Meta:
        ordering = ['-timestamp']