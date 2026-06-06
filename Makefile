.PHONY: run worker beat shell migrate test lint

run:
	.venv/bin/python manage.py runserver

worker:
	.venv/bin/celery -A config.celery worker --loglevel=info

beat:
	.venv/bin/celery -A config.celery beat --loglevel=info

flower:
	.venv/bin/celery -A config.celery flower

shell:
	.venv/bin/python manage.py shell_plus

migrate:
	.venv/bin/python manage.py makemigrations && .venv/bin/python manage.py migrate

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check . && .venv/bin/black --check .

fmt:
	.venv/bin/black . && .venv/bin/ruff --fix .
