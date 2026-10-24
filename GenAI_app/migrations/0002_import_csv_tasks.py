import csv
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import migrations


def import_csv_tasks(apps, schema_editor):
    Task = apps.get_model('GenAI_app', 'Task')
    csv_path = Path(settings.BASE_DIR).parent / 'GenAI_app' / 'tasks.csv'
    if not csv_path.exists():
        return

    with csv_path.open(newline='', encoding='utf-8') as file:
        for row in csv.DictReader(file, delimiter=';'):
            Task.objects.update_or_create(
                task_number=int(row['Task']),
                defaults={
                    'original_budget': row['Original budget'],
                    'spent_budget': row['Spent budget'],
                    'starting_date': datetime.strptime(row['Starting date'].strip(), '%Y-%m-%d').date(),
                    'deadline_date': datetime.strptime(row[' Deadline date'].strip(), '%Y-%m-%d').date(),
                    'status': row['Status'].strip().lower(),
                    'recommendation': row.get('Recommendation', '').strip().strip('"'),
                },
            )


class Migration(migrations.Migration):
    dependencies = [('GenAI_app', '0001_initial')]
    operations = [migrations.RunPython(import_csv_tasks, migrations.RunPython.noop)]
