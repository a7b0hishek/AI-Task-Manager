from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_number', models.PositiveIntegerField(unique=True)),
                ('original_budget', models.DecimalField(decimal_places=2, max_digits=12)),
                ('spent_budget', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('starting_date', models.DateField()),
                ('deadline_date', models.DateField()),
                ('status', models.CharField(choices=[('green', 'Green'), ('amber', 'Amber'), ('red', 'Red')], default='green', max_length=5)),
                ('recommendation', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ('task_number',)},
        ),
    ]
