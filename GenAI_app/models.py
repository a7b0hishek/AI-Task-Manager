from django.db import models


class Task(models.Model):
    STATUS_GREEN = 'green'
    STATUS_AMBER = 'amber'
    STATUS_RED = 'red'
    STATUS_CHOICES = (
        (STATUS_GREEN, 'Green'),
        (STATUS_AMBER, 'Amber'),
        (STATUS_RED, 'Red'),
    )

    task_number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200, default='Untitled task')
    description = models.TextField(blank=True)
    original_budget = models.DecimalField(max_digits=12, decimal_places=2)
    spent_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    starting_date = models.DateField()
    deadline_date = models.DateField()
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default=STATUS_GREEN)
    recommendation = models.TextField(blank=True)
    risks = models.JSONField(default=list, blank=True)
    recommended_actions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('task_number',)

    def __str__(self):
        return f'{self.task_number}: {self.name}'


class TaskHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20)
    changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)


class AIRequest(models.Model):
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='ai_requests')
    request_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=10)
    response = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
