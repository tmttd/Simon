from django.db import migrations, models
import uuid
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_chatmessage_duration'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudyGroup',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='study_groups', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='thread',
            name='group',
            field=models.ForeignKey(related_name='threads', to='chat.studygroup', null=True, blank=True, on_delete=models.deletion.CASCADE),
        ),
    ]


