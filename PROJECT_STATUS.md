# AI Task Manager — Project Status

## Current status

The application is a working Django-based AI task manager. The dashboard,
task creation, task updates, task deletion, search, AI assistant, history,
and production deployment configuration are implemented.

The local Git merge conflict in `.gitignore` has been resolved. Useful ignore
rules from both local and remote versions are preserved. Generated Python
bytecode, the local SQLite database, and static build output are excluded from
version control. The resolved merge was pushed to `origin/main` in commit
`32017af`.

## Status-document maintenance

Update this file after every project change that affects application behavior,
the UI, data models, AI integration, deployment configuration, tests, or
documentation. Each update should record the current implementation state,
important decisions, validation results, and any remaining limitations. Keep
this document aligned with the codebase and avoid documenting obsolete
workflows.

Latest local validation:

- Django system checks: passed.
- Production `check --deploy`: passed with production environment variables.
- Application test suite: **13 tests passed**.
- Migration plan: all migrations applied in the local development database.
- Static files: collected successfully with WhiteNoise.
- WSGI application: imports successfully.
- Gunicorn smoke test: returned HTTP 200.
- GitHub `origin/main`: contains the complete project structure and deployment
  files.

## Technology stack

- Python
- Django
- SQLite for local development
- PostgreSQL through `DATABASE_URL` for production
- LangChain `0.2.5`
- `langchain-groq` `0.1.6`
- Groq API
- Pydantic 2.x
- WhiteNoise
- Gunicorn
- HTML, CSS, JavaScript, and Django templates

## Application features

### Dashboard

- Summary cards for total tasks, green tasks, tasks needing attention,
  overdue tasks, total budget, and spent budget.
- Responsive task cards.
- Search by task name or description.
- Status and deadline filters.
- Budget progress bars.
- Animated status indicators:
  - Green: static green dot.
  - Amber: pulsing amber dot.
  - Red: blinking red dot.
- AI Focus panel for tasks with amber or red status.

### Automatic budget status

Status is calculated from budget usage only:

- **Green:** spent budget is below 80% of the original budget.
- **Amber:** spent budget is at least 80% of the original budget.
- **Red:** spent budget is greater than the original budget.

The calculation is applied when:

- A task is created.
- A task is updated.
- The dashboard is loaded and stale values are detected.
- The AI assistant changes a task budget.

Deadlines are retained for task information and filtering, but they do not
override the budget-based RAG status.

### Task management

- Add tasks with name, description, original budget, spent budget, dates, and
  an optional recommendation.
- Automatic task-number assignment.
- Update the selected task's spent budget and recommendation.
- The dashboard Update link passes the selected task number to the update form.
- The update form pre-fills the selected task's current values.
- Delete tasks with a visible Delete button and browser confirmation.
- Deletion uses a CSRF-protected POST endpoint.
- Additions and updates are stored in `TaskHistory`.

### AI recommendations

Groq is configured in `GenAI_app/helpers.py`:

- Model: `openai/gpt-oss-20b`
- Temperature: `0.2`
- Timeout: 30 seconds
- Maximum attempts: 3
- Environment variable: `GROQ_API_KEY`

AI recommendations use validated JSON containing:

```json
{
  "recommendation": "string",
  "risks": ["string"],
  "recommended_actions": ["string"]
}
```

Successful responses are cached by task inputs. All AI requests are recorded
in `AIRequest`, including status, attempts, response data, and errors.

### AI task assistant

The dashboard includes a natural-language assistant that can:

- Answer questions about the current tasks.
- Create a task when required values are provided.
- Update task name, description, spent budget, or recommendation.
- Recalculate the status after an AI update.
- Delete a task only after an explicit confirmation.

Example requests:

```text
How many red tasks do I have?
Which task has the highest budget?
Update task 3 spent budget to 8500.
Rename task 2 to Launch campaign.
```

The assistant endpoint is:

```text
POST /ai-assistant/
```

## Data model

The primary task persistence path is Django ORM with SQLite or PostgreSQL:

- `Task`: task details, budget values, status, recommendations, risks, and
  recommended actions.
- `TaskHistory`: task creation and update audit records.
- `AIRequest`: AI request history and cache records.

The original `GenAI_app/tasks.csv` file is retained only as source data for the
initial migration. New task changes are stored in the database; no runtime
feature reads or writes the CSV file.

## Production configuration

Production settings are environment-driven:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `DATABASE_URL`
- `GROQ_API_KEY`
- `DB_CONN_MAX_AGE`
- `LOG_LEVEL`

Local development uses SQLite when `DATABASE_URL` is not set. Production
should use PostgreSQL for multi-process deployments.

WhiteNoise serves compressed static files after `collectstatic`. Gunicorn uses
the corrected WSGI module:

```text
system_config.wsgi:application
```

## Run locally

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set at least:

```env
GROQ_API_KEY=your-groq-api-key
```

Apply migrations and start Django:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py migrate
PYTHONPATH=. .venv/bin/python RAG_app/manage.py runserver 127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000/
```

The main dashboard does not require sign-in. Django admin remains available
at `/admin/`.

## Test and deployment commands

Run tests:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py test GenAI_app
```

Run standard checks:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py check
```

Prepare a production deployment:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py migrate
PYTHONPATH=. .venv/bin/python RAG_app/manage.py collectstatic --noinput
PYTHONPATH=. .venv/bin/python RAG_app/manage.py check --deploy
```

Render commands:

```bash
pip install -r requirements.txt && PYTHONPATH=. python RAG_app/manage.py collectstatic --noinput && PYTHONPATH=. python RAG_app/manage.py migrate
PYTHONPATH=. gunicorn --chdir RAG_app system_config.wsgi:application --bind 0.0.0.0:$PORT
```

Run Gunicorn:

```bash
PYTHONPATH=. gunicorn --chdir RAG_app system_config.wsgi:application -c gunicorn.conf.py
```

For hosting platforms that provide `PORT`:

```bash
PYTHONPATH=. gunicorn --chdir RAG_app system_config.wsgi:application --bind 0.0.0.0:$PORT
```

## Important security notes

- Never commit `.env`.
- Never document or print the real Groq API key.
- Use a long, unique production `DJANGO_SECRET_KEY`.
- Set `DJANGO_DEBUG=False` in production.
- Restrict `DJANGO_ALLOWED_HOSTS` to the real domain.
- Configure full HTTPS values in `CSRF_TRUSTED_ORIGINS`.
- Rotate credentials if they have been exposed.

## Main implementation files

- [GenAI_app/models.py](GenAI_app/models.py): database models.
- [GenAI_app/forms.py](GenAI_app/forms.py): task validation.
- [GenAI_app/helpers.py](GenAI_app/helpers.py): budget status and Groq logic.
- [GenAI_app/views.py](GenAI_app/views.py): dashboard and task workflows.
- [GenAI_app/templates/index.html](GenAI_app/templates/index.html): dashboard UI.
- [GenAI_app/static/GenAI_app/styles.css](GenAI_app/static/GenAI_app/styles.css): theme and responsive styles.
- [RAG_app/system_config/settings.py](RAG_app/system_config/settings.py): environment and deployment settings.
- [RAG_app/system_config/wsgi.py](RAG_app/system_config/wsgi.py): Gunicorn entry point.
- [README.md](README.md): setup, usage, screenshots, and deployment guide.

## Cleanup record

Removed the obsolete Pandas-based CSV write helper and its dependency. The
database-backed Django models are now the only runtime persistence path. The
legacy CSV is retained because the historical data migration depends on it.
Removed unused deadline parameters from the budget-status helper and corrected
the update-form guidance to match the current fields.
