import os
import re
import json
import logging
from dataclasses import dataclass

from groq import APIConnectionError, APITimeoutError, RateLimitError
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIRecommendation:
    recommendation: str
    risks: list[str]
    recommended_actions: list[str]
    attempts: int = 1


@dataclass(frozen=True)
class AIAssistantCommand:
    action: str
    reply: str
    task_number: int | None = None
    fields: dict = None
    requires_confirmation: bool = False


def parse_ai_response(content):
    """Parse and validate the model's structured JSON response."""
    text = content.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError('Groq returned invalid JSON.') from error
    recommendation = data.get('recommendation')
    risks = data.get('risks')
    actions = data.get('recommended_actions')
    if not isinstance(recommendation, str) or not recommendation.strip():
        raise ValueError('Groq response is missing a recommendation.')
    if not isinstance(risks, list) or not all(isinstance(item, str) for item in risks):
        raise ValueError('Groq response contains invalid risks.')
    if not isinstance(actions, list) or not all(isinstance(item, str) for item in actions):
        raise ValueError('Groq response contains invalid recommended actions.')
    return AIRecommendation(recommendation.strip(), risks, actions)


def status_from_budget(original_budget, spent_budget):
    """Return an automatic RAG status based only on budget usage."""
    original = float(original_budget)
    spent = float(spent_budget)
    if original <= 0 or spent > original:
        return 'red'
    if spent >= original * 0.8:
        return 'amber'
    return 'green'


def load_groq_llm(model="openai/gpt-oss-20b", temperature=0.2):
    '''
    Initialize and load the Groq language model for processing requests.

    Parameters:
        model: The Groq model.
        temperature (float): controls the randomness of the model's output. min-max is 0.0-1.0.

    Returns:
        An instance of the Groq language model ready for use.
    '''
    llm = ChatGroq(
        model=model,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,
        timeout=30,
    )
    return llm

def ask_ai(task_number, original_budget, spent_budget, starting_date, deadline_date, date):
    '''
    Processes project management data and prompts a Groq language model for task RAG status and expert recommendations.

    Parameters:
        task_number (int): The identifier of the task. In the csv sample, task_number is 1:5.
        original_budget (float): The original budget allocated for the task.
        spent_budget (float): The amount of budget spent on the task.
        starting_date (str): The starting date of the task.
        deadline_date (str): The deadline date for completing the task.
        date (str): Today's date.

    Returns:
        A tuple containing task number, status RAG color, and the AI expert recommendation response.
    '''
    prompt = f'''Return only valid JSON with exactly these keys:
{{"recommendation": "string", "risks": ["string"], "recommended_actions": ["string"]}}
You are a project management expert. Analyze task {task_number}.
Original budget: {original_budget}; spent budget: {spent_budget};
starting date: {starting_date}; deadline: {deadline_date}; today: {date}.
Give a concise recommendation, the main risks, and practical recommended actions.'''
    last_error = None
    for attempt in range(1, 4):
        try:
            llm = load_groq_llm()
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            parsed = parse_ai_response(content)
            return AIRecommendation(parsed.recommendation, parsed.risks, parsed.recommended_actions, attempt)
        except (ValueError, TimeoutError, ConnectionError, APIConnectionError, APITimeoutError, RateLimitError) as error:
            last_error = error
            logger.warning('Groq attempt %s failed: %s', attempt, error)
    raise RuntimeError(f'Groq request failed after 3 attempts: {last_error}') from last_error


def ask_assistant(message, tasks):
    """Translate a natural-language task request into a validated command."""
    task_context = [
        {
            'task_number': task.task_number,
            'name': task.name,
            'description': task.description,
            'original_budget': str(task.original_budget),
            'spent_budget': str(task.spent_budget),
            'starting_date': str(task.starting_date),
            'deadline_date': str(task.deadline_date),
            'status': task.status,
        }
        for task in tasks
    ]
    prompt = f"""You are the task manager assistant. Return only valid JSON with exactly these keys:
{{"action":"answer|create|update|delete","reply":"string","task_number":null,"fields":{{}},"requires_confirmation":false}}
User request: {message}
Tasks: {json.dumps(task_context)}
Rules:
- Use answer for questions or when the request is unclear.
- Use create for a new task and put provided values in fields.
- Use update for changing an existing task; identify task_number and put only changed values in fields.
- Use delete only when the user clearly asks to delete a task; set requires_confirmation true.
- Never invent missing dates, budgets, or task numbers. Ask for missing required create information in reply.
- For task questions, answer using the supplied task data."""
    last_error = None
    for attempt in range(1, 4):
        try:
            llm = load_groq_llm()
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            text = content.strip()
            if text.startswith('```'):
                text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.IGNORECASE)
            data = json.loads(text)
            action = data.get('action')
            if action not in {'answer', 'create', 'update', 'delete'}:
                raise ValueError('Assistant returned an invalid action.')
            fields = data.get('fields') or {}
            if not isinstance(fields, dict) or not isinstance(data.get('reply'), str):
                raise ValueError('Assistant returned an invalid command.')
            task_number = data.get('task_number')
            return AIAssistantCommand(
                action=action,
                reply=data['reply'].strip(),
                task_number=int(task_number) if task_number is not None else None,
                fields=fields,
                requires_confirmation=bool(data.get('requires_confirmation')),
            )
        except (ValueError, TypeError, json.JSONDecodeError, TimeoutError, ConnectionError,
                APIConnectionError, APITimeoutError, RateLimitError) as error:
            last_error = error
            logger.warning('Assistant attempt %s failed: %s', attempt, error)
    raise RuntimeError(f'AI assistant failed after 3 attempts: {last_error}') from last_error
