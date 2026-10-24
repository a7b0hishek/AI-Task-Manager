from django.db import migrations


def name_existing_tasks(apps, schema_editor):
    Task = apps.get_model('GenAI_app', 'Task')
    for task in Task.objects.filter(name='Untitled task'):
        task.name = f'Task {task.task_number}'
        task.save(update_fields=('name',))


class Migration(migrations.Migration):
    dependencies = [('GenAI_app', '0003_phase2_fields_history')]
    operations = [migrations.RunPython(name_existing_tasks, migrations.RunPython.noop)]
