from django.contrib import admin

from GenAI_app.models import AIRequest, Task, TaskHistory


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_number', 'original_budget', 'spent_budget', 'status', 'deadline_date', 'updated_at')
    list_filter = ('status',)
    search_fields = ('task_number', 'recommendation')


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'action', 'created_at')
    list_filter = ('action',)


@admin.register(AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    list_display = ('task', 'status', 'attempts', 'created_at')
    list_filter = ('status',)
    search_fields = ('request_hash', 'error')
