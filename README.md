# AI Task Manager

AI Task Manager is a Django application for tracking project tasks, monitoring
budget health, and receiving AI-powered recommendations through Groq.

The application uses a simple RAG status model:

- **Green**: less than 80% of the original budget is spent.
- **Amber**: 80% or more of the original budget is spent.
- **Red**: the spent budget is greater than the original budget.

Status is recalculated automatically whenever a task is created, updated, or
the dashboard is loaded. Deadlines remain available for task context and
filtering, but budget usage controls the RAG status.

## Features

- Dashboard with summary cards for task count, status, deadlines, and budgets.
- Search by task name or description.
- Filters for status and deadline.
- Add, update, and delete tasks.
- Automatic budget-based status with animated status indicators.
- AI recommendations, risks, and recommended actions.
- Natural-language AI assistant that can:
  - Answer questions about your tasks.
  - Create tasks.
  - Update task details and budgets.
  - Delete tasks only after confirmation.
- Task update history.
- SQLite for local development.
- PostgreSQL support through `DATABASE_URL`.
- Production security settings and WhiteNoise static files.
- Gunicorn deployment configuration.

## Screenshots

### Dashboard overview

![AI Task Manager dashboard](img/Pasted%2024-10-2026%20at%2017.39.36.png)

### AI assistant and task workspace

![AI assistant and task cards](img/Pasted%2024-10-2026%20at%2017.51.28.png)

### Task cards and budget statuses

![Task cards with budget status](img/Pasted%2024-10-2026%20at%2017.52.12.png)

### Update task form

![Update task form](img/Pasted%2024-10-2026%20at%2017.52.29.png)

### Update task form with status guidance

![Task update status guidance](img/Pasted%2024-10-2026%20at%2017.52.30.png)

### Dashboard task list

![Dashboard task list](img/Pasted%2024-10-2026%20at%2017.40.01.png)

## Technology stack

- Python
- Django
- SQLite for local development
- PostgreSQL for production
- LangChain
- Groq API
- `langchain-groq`
- Pydantic
- WhiteNoise
- Gunicorn

## Project structure

```text
.
├── GenAI_app/
│   ├── migrations/
│   ├── static/GenAI_app/styles.css
│   ├── templates/
│   ├── forms.py
│   ├── helpers.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── RAG_app/
│   ├── manage.py
│   └── system_config/
│       ├── settings.py
│       ├── urls.py
│       └── wsgi.py
├── .env.example
├── Procfile
├── gunicorn.conf.py
└── requirements.txt
```

## Local setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

At minimum, set the Groq key:

```env
GROQ_API_KEY=your-groq-api-key
```

Never commit `.env` or expose API keys in source code.

### 4. Apply migrations

Because `manage.py` is inside `RAG_app`, run Django commands from the
repository root with `PYTHONPATH=.`:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py migrate
```

### 5. Start the development server

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

The main task dashboard does not require sign-in. The Django admin remains
available at `/admin/` for administrative access.

## Using the AI assistant

Use the AI Assistant panel on the dashboard to ask questions or request
changes in natural language.

Examples:

```text
How many red tasks do I have?
Which task has the highest budget?
What is the status of task 3?
Update task 3 spent budget to 8500.
Rename task 2 to Launch campaign.
```

To create a task, provide the required values:

```text
Add a task called Website redesign with a budget of 10000,
starting 2027-01-01 and deadline 2027-02-01.
```

Delete requests require an explicit confirmation. The assistant will ask for
confirmation before removing a task.

## Testing and checks

Run the application test suite:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py test GenAI_app
```

Run Django checks:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py check
```

## Production deployment

Copy `.env.example` to `.env` and configure production values:

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
GROQ_API_KEY=your-groq-api-key
DATABASE_URL=postgresql://user:password@host:5432/taskmanager
```

When `DATABASE_URL` is not set, local SQLite is used. Do not use SQLite for a
multi-process production deployment.

For Render, use these commands from the repository root:

```bash
# Build command
pip install -r requirements.txt && PYTHONPATH=. python RAG_app/manage.py collectstatic --noinput && PYTHONPATH=. python RAG_app/manage.py migrate

# Start command
PYTHONPATH=. gunicorn --chdir RAG_app system_config.wsgi:application --bind 0.0.0.0:$PORT
```

Prepare the production database and static files:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py migrate
PYTHONPATH=. .venv/bin/python RAG_app/manage.py collectstatic --noinput
PYTHONPATH=. .venv/bin/python RAG_app/manage.py check --deploy
```

Run with Gunicorn:

```bash
PYTHONPATH=. gunicorn --chdir RAG_app system_config.wsgi:application -c gunicorn.conf.py
```

For hosting platforms that provide a `PORT` environment variable:

```bash
PYTHONPATH=. gunicorn --chdir RAG_app system_config.wsgi:application --bind 0.0.0.0:$PORT
```

Create an administrator for Django admin:

```bash
PYTHONPATH=. .venv/bin/python RAG_app/manage.py createsuperuser
```

## Security notes

- Keep `.env` outside version control.
- Use a long, unique production `DJANGO_SECRET_KEY`.
- Set `DJANGO_DEBUG=False` in production.
- Restrict `DJANGO_ALLOWED_HOSTS` to the real hostnames.
- Configure `CSRF_TRUSTED_ORIGINS` with full HTTPS origins.
- Rotate the Groq key if it has ever been exposed.
