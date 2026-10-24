import datetime
import hashlib
import json
import os

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from dotenv import load_dotenv

from GenAI_app.forms import TaskForm, TaskUpdateForm
from GenAI_app.helpers import ask_ai, ask_assistant, status_from_budget
from GenAI_app.models import AIRequest, Task, TaskHistory

load_dotenv()
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')


def index(request):
    for task in Task.objects.all():
        current_status = status_from_budget(task.original_budget, task.spent_budget)
        if task.status != current_status:
            task.status = current_status
            task.save(update_fields=('status', 'updated_at'))
    tasks = Task.objects.all()
    query = request.GET.get('q', '').strip()
    selected_status = request.GET.get('status', '').strip().lower()
    selected_deadline = request.GET.get('deadline', '').strip()
    if query:
        tasks = tasks.filter(name__icontains=query) | tasks.filter(description__icontains=query)
    if selected_status in {'green', 'amber', 'red'}:
        tasks = tasks.filter(status=selected_status)
    today = datetime.date.today()
    if selected_deadline == 'overdue':
        tasks = tasks.filter(deadline_date__lt=today)
    elif selected_deadline == 'upcoming':
        tasks = tasks.filter(deadline_date__gte=today, deadline_date__lte=today + datetime.timedelta(days=7))
    all_tasks = Task.objects.all()
    for task in all_tasks:
        task.budget_percent = min(
            100,
            round(float(task.spent_budget / task.original_budget * 100), 1)
            if task.original_budget
            else 0,
        )
    attention_tasks = [task for task in all_tasks if task.status in {'amber', 'red'}]
    summary = {
        'total': all_tasks.count(),
        'green': all_tasks.filter(status='green').count(),
        'amber': all_tasks.filter(status='amber').count(),
        'red': all_tasks.filter(status='red').count(),
        'budget': sum(task.original_budget for task in all_tasks),
        'spent': sum(task.spent_budget for task in all_tasks),
        'attention': len(attention_tasks),
        'overdue': all_tasks.filter(deadline_date__lt=today).count(),
    }
    return render(request, 'index.html', {
        'tasks': tasks.distinct(), 'summary': summary, 'query': query,
        'selected_status': selected_status, 'selected_deadline': selected_deadline,
        'attention_tasks': attention_tasks[:3],
    })


def ai_assistant(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Use POST for assistant requests.'}, status=405)
    try:
        payload = json.loads(request.body or '{}')
        message = str(payload.get('message', '')).strip()
        if not message or len(message) > 1000:
            return JsonResponse({'error': 'Enter a question or task request up to 1000 characters.'}, status=400)
        pending_delete = request.session.get('pending_delete')
        if pending_delete and payload.get('confirm') and message.lower() in {'yes', 'confirm', 'delete'}:
            task = get_object_or_404(Task, task_number=pending_delete)
            task_name = task.name
            task.delete()
            request.session.pop('pending_delete', None)
            return JsonResponse({'reply': f'Task #{pending_delete} “{task_name}” was deleted.', 'action': 'deleted'})
        command = ask_assistant(message, Task.objects.all())
        if command.action == 'answer':
            return JsonResponse({'reply': command.reply, 'action': command.action})
        if command.task_number is None:
            return JsonResponse({'reply': command.reply, 'action': 'answer'})
        if command.action == 'delete':
            task = get_object_or_404(Task, task_number=command.task_number)
            if not payload.get('confirm'):
                request.session['pending_delete'] = task.task_number
                return JsonResponse({
                    'reply': f'{command.reply} Please confirm that you want to delete “{task.name}”.',
                    'action': 'confirm_delete',
                    'task_number': task.task_number,
                })
            if request.session.get('pending_delete') != task.task_number:
                return JsonResponse({'reply': 'Delete confirmation expired. Ask me to delete the task again.', 'action': 'answer'})
            task.delete()
            request.session.pop('pending_delete', None)
            return JsonResponse({'reply': f'Task #{command.task_number} was deleted.', 'action': 'deleted'})
        if command.action == 'create':
            fields = command.fields
            required = ('name', 'original_budget', 'starting_date', 'deadline_date')
            if any(not fields.get(field) for field in required):
                return JsonResponse({'reply': command.reply, 'action': 'answer'})
            task = Task(
                task_number=(Task.objects.order_by('-task_number').values_list('task_number', flat=True).first() or 0) + 1,
                name=str(fields['name'])[:200],
                description=str(fields.get('description', '')),
                original_budget=fields['original_budget'],
                spent_budget=fields.get('spent_budget', 0),
                starting_date=fields['starting_date'],
                deadline_date=fields['deadline_date'],
                recommendation=str(fields.get('recommendation', '')),
            )
            task.status = status_from_budget(task.original_budget, task.spent_budget)
            task.save()
            TaskHistory.objects.create(task=task, action='created', changes={'source': 'ai_assistant'})
            return JsonResponse({'reply': f'Task #{task.task_number} “{task.name}” was created with {task.status} status.', 'action': 'created'})
        task = get_object_or_404(Task, task_number=command.task_number)
        fields = command.fields
        changed = []
        for field in ('name', 'description', 'spent_budget', 'recommendation'):
            if field in fields:
                setattr(task, field, fields[field])
                changed.append(field)
        if not changed:
            return JsonResponse({'reply': command.reply, 'action': 'answer'})
        task.status = status_from_budget(task.original_budget, task.spent_budget)
        task.save()
        TaskHistory.objects.create(task=task, action='updated', changes={'source': 'ai_assistant', 'fields': changed})
        return JsonResponse({'reply': f'Task #{task.task_number} was updated. Its budget status is now {task.status}.', 'action': 'updated'})
    except (json.JSONDecodeError, TypeError, ValueError, RuntimeError) as error:
        return JsonResponse({'error': str(error)}, status=502)


def add_page(request):
    return render(request, 'add.html', {'form': TaskForm()})


def add_task(request):
    if request.method != 'POST':
        return redirect('index')

    form = TaskForm(request.POST)
    if not form.is_valid():
        return render(request, 'add.html', {'form': form}, status=400)

    task = form.save(commit=False)
    task.task_number = (Task.objects.order_by('-task_number').values_list('task_number', flat=True).first() or 0) + 1
    task.status = status_from_budget(task.original_budget, task.spent_budget)
    task.save()
    TaskHistory.objects.create(task=task, action='created', changes={'name': task.name})
    messages.success(request, f'Task {task.task_number} added successfully.')
    return redirect('index')


def task_history(request, task_number):
    task = get_object_or_404(Task, task_number=task_number)
    return render(request, 'history.html', {'task': task, 'history': task.history.all()})


def delete_task(request, task_number):
    if request.method != 'POST':
        return redirect('index')
    task = get_object_or_404(Task, task_number=task_number)
    task_name = task.name
    task.delete()
    messages.success(request, f'Task {task_number} "{task_name}" was deleted.')
    return redirect('index')


def update_page(request):
    initial = {}
    task_number = request.GET.get('task_number', '').strip()
    if task_number.isdigit():
        initial['task_number'] = int(task_number)
        task = Task.objects.filter(task_number=task_number).first()
        if task:
            initial['spent_budget'] = task.spent_budget
            initial['recommendation'] = task.recommendation
    return render(request, 'update.html', {'form': TaskUpdateForm(initial=initial)})


def update_status(request):
    if request.method != 'POST':
        return redirect('index')

    task_number = request.POST.get('task_number')
    task = get_object_or_404(Task, task_number=task_number) if task_number else None
    form = TaskUpdateForm(request.POST, instance=task)
    if not form.is_valid():
        messages.error(request, ' '.join(form.errors.get_json_data().get(field, [{}])[0].get('message', '') for field in form.errors))
        return redirect('update_page')

    spent_budget = form.cleaned_data.get('spent_budget')
    recommendation = form.cleaned_data.get('recommendation')
    if spent_budget is None and not recommendation and not form.cleaned_data.get('generate_recommendation'):
        messages.error(request, 'Change at least one task field before saving.')
        return redirect('update_page')

    previous = {'spent_budget': str(task.spent_budget), 'recommendation': task.recommendation, 'status': task.status}
    if spent_budget is not None:
        task.spent_budget = spent_budget
    if recommendation:
        task.recommendation = recommendation

    if form.cleaned_data.get('generate_recommendation'):
        if not GROQ_API_KEY:
            messages.error(request, 'Groq API key is not configured. Add GROQ_API_KEY or enter a manual recommendation.')
            return redirect('update_page')
        request_data = {
            'task': task.task_number,
            'original_budget': str(task.original_budget),
            'spent_budget': str(task.spent_budget),
            'starting_date': str(task.starting_date),
            'deadline_date': str(task.deadline_date),
            'date': str(datetime.date.today()),
        }
        request_hash = hashlib.sha256(json.dumps(request_data, sort_keys=True).encode()).hexdigest()
        cached = AIRequest.objects.filter(task=task, request_hash=request_hash, status=AIRequest.STATUS_SUCCESS).first()
        if cached:
            ai_data = cached.response
        else:
            try:
                ai_result = ask_ai(**{
                    'task_number': task.task_number,
                    'original_budget': task.original_budget,
                    'spent_budget': task.spent_budget,
                    'starting_date': task.starting_date,
                    'deadline_date': task.deadline_date,
                    'date': datetime.date.today(),
                })
                ai_data = {
                    'recommendation': ai_result.recommendation,
                    'risks': ai_result.risks,
                    'recommended_actions': ai_result.recommended_actions,
                }
                AIRequest.objects.create(task=task, request_hash=request_hash, status=AIRequest.STATUS_SUCCESS, response=ai_data, attempts=ai_result.attempts)
            except (RuntimeError, ValueError) as error:
                AIRequest.objects.create(task=task, request_hash=request_hash, status=AIRequest.STATUS_FAILED, error=str(error), attempts=3)
                messages.error(request, f'AI recommendation failed: {error}')
                return redirect('update_page')
        task.recommendation = ai_data['recommendation']
        task.risks = ai_data['risks']
        task.recommended_actions = ai_data['recommended_actions']

    task.status = status_from_budget(task.original_budget, task.spent_budget)
    task.save()
    TaskHistory.objects.create(task=task, action='updated', changes={
        'before': previous,
        'after': {'spent_budget': str(task.spent_budget), 'recommendation': task.recommendation, 'status': task.status},
    })
    messages.success(request, f'Task {task.task_number} updated successfully.')
    return redirect('index')
