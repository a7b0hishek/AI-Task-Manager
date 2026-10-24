from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('GenAI_app', '0004_name_existing_tasks')]
    operations = [
        migrations.AddField(model_name='task', name='risks', field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name='task', name='recommended_actions', field=models.JSONField(blank=True, default=list)),
        migrations.CreateModel(
            name='AIRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_hash', models.CharField(db_index=True, max_length=64)),
                ('status', models.CharField(max_length=10)),
                ('response', models.JSONField(blank=True, default=dict)),
                ('error', models.TextField(blank=True)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_requests', to='GenAI_app.task')),
            ],
            options={'ordering': ('-created_at',)},
        ),
    ]
