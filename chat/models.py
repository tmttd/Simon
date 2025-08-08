from django.db import models

class ChatMessage(models.Model):
    # 메세지가 속한 대화의 고유 ID
    thread_id = models.CharField(max_length=100, db_index=True)

    # 메세지를 보낸 주체
    SENDER_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI'),
    ]
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)

    # 실제 메세지 내용
    message = models.TextField()

    # 메세지가 생성된 시간 (자동으로 현재 시간이 기록됨)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # 관리자 페이지 등에서 객체를 쉽게 식별하기 위한 이름
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.sender}: {self.message[:30]}"
    
    class Meta:
        # 데이터베이스에 저장될 때, 최신 메세지가 먼저 오도록 정렬 순서 기본값을 최신순으로 지정
        ordering = ['-timestamp']
