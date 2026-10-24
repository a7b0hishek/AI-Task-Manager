from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from unittest.mock import patch

from GenAI_app.helpers import parse_ai_response, status_from_budget
from GenAI_app.models import AIRequest, Task


class TaskStatusTests(TestCase):
    def test_status_is_calculated_from_budget(self):
        self.assertEqual(status_from_budget(Decimal('100'), Decimal('79.99')), 'green')
        self.assertEqual(status_from_budget(Decimal('100'), Decimal('80')), 'amber')
        self.assertEqual(status_from_budget(Decimal('100'), Decimal('101')), 'red')

    def test_deadline_does_not_change_budget_status(self):
        self.assertEqual(
            status_from_budget(Decimal('100'), Decimal('10')),
            'green',
        )
        self.assertEqual(
            status_from_budget(Decimal('100'), Decimal('10')),
            'green',
        )

    def test_structured_ai_response_is_validated(self):
        result = parse_ai_response('{"recommendation":"Keep scope focused.","risks":["Delay"],"recommended_actions":["Review milestones"]}')
        self.assertEqual(result.risks, ['Delay'])
        with self.assertRaises(ValueError):
            parse_ai_response('not json')


class TaskWorkflowTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username='tester', password='test-password')
        self.client.force_login(user)

    def test_anonymous_users_can_open_dashboard(self):
        self.client.logout()
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_search_filters_task_name_and_description(self):
        Task.objects.create(
            task_number=101,
            name='Website redesign',
            description='Refresh the landing page.',
            original_budget=Decimal('1000'),
            spent_budget=Decimal('100'),
            starting_date=date(2027, 1, 1),
            deadline_date=date(2027, 2, 1),
            status='green',
        )
        Task.objects.create(
            task_number=102,
            name='Analytics report',
            description='Prepare the monthly metrics.',
            original_budget=Decimal('1000'),
            spent_budget=100,
            starting_date=date(2027, 1, 1),
            deadline_date=date(2027, 2, 1),
            status='green',
        )

        response = self.client.get(reverse('index'), {'q': 'landing'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Website redesign')
        self.assertNotContains(response, 'Analytics report')

    def test_delete_task_requires_post_and_removes_task(self):
        task = Task.objects.create(
            task_number=104,
            name='Task to remove',
            original_budget=Decimal('1000'),
            spent_budget=Decimal('100'),
            starting_date=date(2027, 1, 1),
            deadline_date=date(2027, 2, 1),
            status='green',
        )

        get_response = self.client.get(reverse('delete_task', args=[task.task_number]))
        self.assertRedirects(get_response, reverse('index'))
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

        post_response = self.client.post(reverse('delete_task', args=[task.task_number]))
        self.assertRedirects(post_response, reverse('index'))
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    @patch('GenAI_app.views.ask_assistant')
    def test_ai_assistant_updates_task(self, ask_assistant):
        from GenAI_app.helpers import AIAssistantCommand

        Task.objects.create(
            task_number=103,
            name='Prepare report',
            original_budget=Decimal('1000'),
            spent_budget=Decimal('100'),
            starting_date=date(2027, 1, 1),
            deadline_date=date(2027, 2, 1),
            status='green',
        )
        ask_assistant.return_value = AIAssistantCommand(
            action='update',
            reply='Updating the task.',
            task_number=103,
            fields={'spent_budget': '850'},
        )

        response = self.client.post(
            '/ai-assistant/',
            data='{"message":"set task 103 spent budget to 850"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        task = Task.objects.get(task_number=103)
        self.assertEqual(task.spent_budget, Decimal('850'))
        self.assertEqual(task.status, 'amber')

    def test_add_task_creates_validated_task(self):
        response = self.client.post('/add_task/', {
            'name': 'Launch campaign',
            'description': 'Prepare and launch the campaign.',
            'original_budget': '10000',
            'spent_budget': '9000',
            'starting_date': '2027-01-01',
            'deadline_date': '2027-02-01',
            'recommendation': 'Review remaining scope.',
        })

        self.assertRedirects(response, '/')
        task = Task.objects.order_by('-task_number').first()
        self.assertEqual(task.status, 'amber')
        self.assertEqual(task.recommendation, 'Review remaining scope.')

    def test_add_task_rejects_deadline_before_start(self):
        existing_count = Task.objects.count()
        response = self.client.post('/add_task/', {
            'original_budget': '10000',
            'spent_budget': '0',
            'starting_date': '2026-02-01',
            'deadline_date': '2026-01-01',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Task.objects.count(), existing_count)

    def test_update_task_changes_budget_and_recalculates_status(self):
        Task.objects.create(
            task_number=99,
            original_budget=Decimal('10000'),
            spent_budget=Decimal('1000'),
            starting_date=date(2026, 1, 1),
            deadline_date=date(2026, 2, 1),
            status='green',
        )

        response = self.client.post('/update_status/', {
            'task_number': '99',
            'spent_budget': '11000',
            'recommendation': 'Escalate the budget risk.',
        })

        self.assertRedirects(response, '/')
        task = Task.objects.get(task_number=99)
        self.assertEqual(task.status, 'red')
        self.assertEqual(task.spent_budget, Decimal('11000'))
        self.assertEqual(task.recommendation, 'Escalate the budget risk.')

    def test_update_button_opens_selected_task(self):
        Task.objects.create(
            task_number=105,
            name='Selected task',
            original_budget=Decimal('1000'),
            spent_budget=Decimal('100'),
            starting_date=date(2027, 1, 1),
            deadline_date=date(2027, 2, 1),
            status='green',
        )

        response = self.client.get('/update/?task_number=105')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="105"')
        self.assertContains(response, 'value="100.00"')

    def test_dashboard_refreshes_stale_status_and_renders_status_dot(self):
        Task.objects.create(
            task_number=100,
            original_budget=Decimal('10000'),
            spent_budget=Decimal('9000'),
            starting_date=date(2027, 1, 1),
            deadline_date=date(2027, 2, 1),
            status='green',
        )

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.get(task_number=100).status, 'amber')
        self.assertContains(response, 'status-dot-amber')

    @patch('GenAI_app.views.GROQ_API_KEY', 'test-key')
    @patch('GenAI_app.views.ask_ai')
    def test_ai_request_is_cached(self, ask_ai):
        from GenAI_app.helpers import AIRecommendation

        Task.objects.create(
            task_number=99,
            name='Cached task',
            original_budget=Decimal('10000'),
            spent_budget=Decimal('1000'),
            starting_date=date(2027, 1, 1),
            deadline_date=date(2027, 2, 1),
            status='green',
        )
        ask_ai.return_value = AIRecommendation('Keep monitoring.', ['Delay'], ['Review plan'])
        payload = {'task_number': '99', 'generate_recommendation': 'on'}
        self.client.post('/update_status/', payload)
        self.client.post('/update_status/', payload)
        self.assertEqual(ask_ai.call_count, 1)
        self.assertEqual(AIRequest.objects.filter(status='success').count(), 1)
