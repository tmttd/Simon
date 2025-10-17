from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_add_studygroup_and_thread_group'),
    ]

    operations = [
        # 1) 모델 이름 변경
        migrations.RenameModel(
            old_name='StudyGroup',
            new_name='StudySession',
        ),
        # 2) Thread의 외래키 필드명 변경
        migrations.RenameField(
            model_name='thread',
            old_name='group',
            new_name='session',
        ),
        # 3) FK 대상 테이블, related_name 등 최신 스키마로 정합
        migrations.AlterField(
            model_name='thread',
            name='session',
            field=models.ForeignKey(
                related_name='threads',
                to='chat.studysession',
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
            ),
        ),
        # 4) (선택) 모델 옵션 보정 - 필요 시에만
        # migrations.AlterModelOptions(
        #     name='studysession',
        #     options={'ordering': ['-created_at']},
        # ),
    ]