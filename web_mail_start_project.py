#!/usr/bin/env python3
"""
web_mail_start_project.py

A script to bootstrap the web_mail Django project (email delivery service).
Creates folder structure, virtual environment, installs dependencies,
initialises Django, and configures PostgreSQL as the database.

Usage:
    python web_mail_start_project.py

After running, you will need to:
    1. Activate the virtual environment (see output instructions).
    2. Create a PostgreSQL database (e.g., 'web_mail_db').
    3. Update the .env file with your database credentials.
    4. Run migrations: python manage.py migrate
    5. Create a superuser: python manage.py createsuperuser
"""


import subprocess
import sys
from pathlib import Path

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
PROJECT_NAME = "web_mail"
VENV_DIR = ".venv"
REQUIREMENTS = [
    "django>=4.2",
    "djangorestframework>=3.14",
    "django-cors-headers",
    "django-environ",
    "psycopg2-binary",          # PostgreSQL adapter
    "celery>=5.3",
    "redis>=5.0",
    "boto3",                    # AWS SES
    "dnspython",                # DNS lookups
    "django-allauth",
    "django-otp",
    "django-otp-totp",
    "drf-spectacular",          # OpenAPI docs
    "sentry-sdk",               # error tracking
    "django-celery-results",
    "django-redis",
    "gunicorn",
    "whitenoise",               # static files
]

# ----------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------
def run_command(cmd, cwd=None):
    """Run a shell command and exit on failure."""
    print(f"\n--> Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"ERROR: Command failed with code {result.returncode}")
        sys.exit(1)
    return result

def create_dirs(base_path, dirs):
    """Create directories relative to base_path."""
    for d in dirs:
        full_path = base_path / d
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {full_path}")

def touch_file(path, content=""):
    """Create an empty file (or with given content)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  Created: {path}")

# ----------------------------------------------------------------------
# MAIN SCRIPT
# ----------------------------------------------------------------------
def main():
    # Determine project root (current directory)
    project_root = Path.cwd() / PROJECT_NAME
    if project_root.exists():
        print(f"Error: {project_root} already exists. Please remove or choose another location.")
        sys.exit(1)

    print(f"Creating project at {project_root}\n")
    project_root.mkdir(parents=True)

    # ------------------------------------------------------------------
    # 1. Create virtual environment
    # ------------------------------------------------------------------
    print("1. Creating virtual environment...")
    venv_path = project_root / VENV_DIR
    run_command(f"python -m venv {venv_path}")
    print(f"   Virtual environment created at {venv_path}")

    # Determine pip path inside venv
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip"
        python_path = venv_path / "Scripts" / "python"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"

    # ------------------------------------------------------------------
    # 2. Install dependencies
    # ------------------------------------------------------------------
    print("\n2. Installing Python dependencies inside venv...")
    for pkg in REQUIREMENTS:
        run_command(f"{pip_path} install {pkg}")

    # ------------------------------------------------------------------
    # 3. Create Django project (config folder)
    # ------------------------------------------------------------------
    print("\n3. Creating Django project 'config'...")
    run_command(f"{python_path} -m django startproject config .", cwd=project_root)

    # ------------------------------------------------------------------
    # 4. Create directory structure (as per detailed diagram)
    # ------------------------------------------------------------------
    print("\n4. Creating directory structure...")

    # Top-level folders
    top_dirs = [
        "requirements",
        "core/models",
        "core/utils",
        "core/permissions",
        "core/pagination",
        "core/exceptions",
        "core/middleware",
        "apps/authentication",
        "apps/accounts",
        "apps/domains",
        "apps/streams",
        "apps/templates",
        "apps/email_messages",
        "apps/events",
        "apps/analytics",
        "apps/webhooks",
        "apps/suppressions",
        "api/v1/views",
        "api/v1/serializers",
        "web/views",
        "web/forms",
        "templates/landing",
        "templates/registration",
        "templates/dashboard",
        "templates/legal",
        "static/css",
        "static/js",
        "static/img",
        "services",
        "workers/tasks",
        "integrations/ses",
        "integrations/smtp",
        "integrations/storage",
        "tracking",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
        "frontend/public",
        "frontend/src/api",
        "frontend/src/components/common",
        "frontend/src/components/auth",
        "frontend/src/components/domains",
        "frontend/src/components/templates",
        "frontend/src/components/webhooks",
        "frontend/src/pages",
        "frontend/src/hooks",
        "frontend/src/utils",
        "frontend/src/styles",
    ]
    create_dirs(project_root, top_dirs)

    # ------------------------------------------------------------------
    # 5. Create empty files with placeholders
    # ------------------------------------------------------------------
    print("\n5. Creating empty/placeholder files...")

    # Root files
    touch_file(project_root / ".env.example", "# Environment variables\n")
    touch_file(project_root / ".gitignore", "*.pyc\n.venv/\n__pycache__/\n.env\n")
    touch_file(project_root / "docker-compose.yml", "# Docker compose will be added later\n")
    touch_file(project_root / "Dockerfile", "# Dockerfile for Django\n")
    touch_file(project_root / "Dockerfile.frontend", "# Dockerfile for React\n")
    touch_file(project_root / "README.md", f"# {PROJECT_NAME}\n\nEmail delivery service.\n")

    # requirements/*.txt
    touch_file(project_root / "requirements/base.txt", "# Core dependencies\n")
    touch_file(project_root / "requirements/dev.txt", "-r base.txt\n# Dev tools\n")
    touch_file(project_root / "requirements/prod.txt", "-r base.txt\n# Production only\n")

    # Core __init__.py files
    for init_dir in ["core", "core/models", "core/utils", "core/permissions",
                     "core/pagination", "core/exceptions", "core/middleware"]:
        touch_file(project_root / init_dir / "__init__.py")

    # Apps __init__.py and basic models/views stubs
    for app in ["authentication", "accounts", "domains", "streams", "templates",
                "email_messages", "events", "analytics", "webhooks", "suppressions"]:
        app_path = project_root / "apps" / app
        touch_file(app_path / "__init__.py")
        touch_file(app_path / "admin.py", "# Register models\n")
        touch_file(app_path / "apps.py", f"from django.apps import AppConfig\n\nclass {app.capitalize()}Config(AppConfig):\n    name = 'apps.{app}'\n")
        touch_file(app_path / "models.py", "# TODO: Add models\n")
        touch_file(app_path / "serializers.py", "# TODO: Add serializers\n")
        touch_file(app_path / "urls.py", "# TODO: Add URL patterns\n")
        touch_file(app_path / "views.py", "# TODO: Add views\n")

    # API files
    touch_file(project_root / "api/__init__.py")
    touch_file(project_root / "api/urls.py", "from django.urls import include, path\n\nurlpatterns = [\n    path('v1/', include('api.v1.urls')),\n]\n")
    touch_file(project_root / "api/v1/__init__.py")
    touch_file(project_root / "api/v1/urls.py", "from django.urls import path\n\nurlpatterns = [\n    # Add v1 endpoints\n]\n")
    for view in ["send", "messages", "domains", "templates", "stats", "webhooks", "suppressions"]:
        touch_file(project_root / f"api/v1/views/{view}.py", "# TODO: Implement view\n")
    touch_file(project_root / "api/v1/serializers/__init__.py")

    # Web (marketing/dashboard) files
    touch_file(project_root / "web/__init__.py")
    touch_file(project_root / "web/urls.py", "from django.urls import path\n\nurlpatterns = [\n    # Marketing and dashboard URLs\n]\n")
    for wview in ["landing", "legal", "dashboard", "domains_ui", "templates_ui", "analytics_ui", "webhooks_ui", "account"]:
        touch_file(project_root / f"web/views/{wview}.py", "# TODO: Add view\n")
    touch_file(project_root / "web/forms/__init__.py")
    touch_file(project_root / "web/context_processors.py", "# Add context processors\n")

    # Templates base
    touch_file(project_root / "templates/base.html", "<!-- Base template -->\n")
    touch_file(project_root / "templates/landing/index.html", "<!-- Landing page -->\n")
    touch_file(project_root / "templates/registration/login.html", "<!-- Login form -->\n")

    # Static files placeholders
    touch_file(project_root / "static/css/output.css", "/* Tailwind output */\n")
    touch_file(project_root / "static/js/charts.js", "// Charting code\n")

    # Services
    for svc in ["email_service", "template_service", "tracking_service", "webhook_service", "analytics_service"]:
        touch_file(project_root / f"services/{svc}.py", "# Business logic\n")
    touch_file(project_root / "services/__init__.py")

    # Workers / Celery
    touch_file(project_root / "workers/__init__.py")
    for task in ["send_email", "process_events", "webhook_dispatch"]:
        touch_file(project_root / f"workers/tasks/{task}.py", "# Celery task\n")
    touch_file(project_root / "workers/tasks/__init__.py")

    # Integrations
    for sub in ["ses", "smtp", "storage"]:
        touch_file(project_root / f"integrations/{sub}/__init__.py")
        touch_file(project_root / f"integrations/{sub}/client.py", "# External API client\n")

    # Tracking
    touch_file(project_root / "tracking/__init__.py")
    touch_file(project_root / "tracking/urls.py", "from django.urls import path\n\nurlpatterns = [\n    path('open/<str:token>/', ...),\n    path('click/<str:token>/', ...),\n]\n")
    touch_file(project_root / "tracking/views.py", "# Open/click tracking views\n")

    # Tests
    for test_dir in ["unit", "integration", "e2e"]:
        touch_file(project_root / f"tests/{test_dir}/__init__.py")

    # React frontend basic files
    touch_file(project_root / "frontend/package.json", '{ "name": "web_mail_frontend", "version": "0.1.0" }\n')
    touch_file(project_root / "frontend/tailwind.config.js", "module.exports = { content: ['./src/**/*.{js,jsx}'] }\n")
    touch_file(project_root / "frontend/public/index.html", "<!DOCTYPE html><html><body><div id='root'></div></body></html>\n")
    touch_file(project_root / "frontend/src/index.js", "// React entry point\n")
    touch_file(project_root / "frontend/src/App.js", "function App() { return <div>Dashboard</div>; }\nexport default App;\n")
    touch_file(project_root / "frontend/src/api/client.js", "// Axios instance\n")
    # Additional frontend placeholders
    for comp_dir in ["components/common", "components/auth", "components/domains", "components/templates", "components/webhooks", "pages", "hooks", "utils", "styles"]:
        touch_file(project_root / f"frontend/src/{comp_dir}/.gitkeep")

    # ------------------------------------------------------------------
    # 6. Configure Django settings for PostgreSQL
    # ------------------------------------------------------------------
    print("\n6. Configuring settings.py for PostgreSQL...")
    settings_path = project_root / "config/settings.py"
    if settings_path.exists():
        with open(settings_path, "r") as f:
            settings_content = f.read()

        # Replace default DATABASES with PostgreSQL + environment variable support
        db_config = """
import environ

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-temporary-key')
DEBUG = env.bool('DEBUG', default=True)

# PostgreSQL database
DATABASES = {
    'default': env.db(default='postgres://postgres:postgres@localhost:5432/web_mail_db')
}
"""
        # Insert after BASE_DIR definition
        lines = settings_content.splitlines()
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if "BASE_DIR = Path(__file__).resolve().parent.parent" in line and not inserted:
                new_lines.append(db_config)
                inserted = True
        with open(settings_path, "w") as f:
            f.write("\n".join(new_lines))
        print("   settings.py updated for PostgreSQL + django-environ")

    # ------------------------------------------------------------------
    # 7. Create .env.example with database vars
    # ------------------------------------------------------------------
    env_content = """DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@localhost:5432/web_mail_db
REDIS_URL=redis://localhost:6379/0
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
SENTRY_DSN=
"""
    touch_file(project_root / ".env.example", env_content)

    # ------------------------------------------------------------------
    # 8. Final instructions
    # ------------------------------------------------------------------
    print("\n" + "="*70)
    print("✅ Project bootstrapping complete!")
    print("="*70)
    print(f"Project location: {project_root}")
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if sys.platform == "win32":
        print(f"   {venv_path}\\Scripts\\activate")
    else:
        print(f"   source {venv_path}/bin/activate")
    print("2. Copy .env.example to .env and edit database credentials:")
    print(f"   cp {project_root}/.env.example {project_root}/.env")
    print("3. Create the PostgreSQL database (e.g., 'web_mail_db').")
    print("4. Run migrations:")
    print(f"   cd {project_root}")
    print("   python manage.py migrate")
    print("5. Create a superuser:")
    print("   python manage.py createsuperuser")
    print("6. Run the development server:")
    print("   python manage.py runserver")
    print("\nYou can now start implementing the models, views, and services.")
    print("Happy coding!")

if __name__ == "__main__":
    main()