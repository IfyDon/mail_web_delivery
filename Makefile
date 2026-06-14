.PHONY: run worker beat flower shell migrate test lint fmt

PYTHON = .venv/Scripts/python
CELERY = $(PYTHON) -m celery -A config.celery

run:
	$(PYTHON) manage.py runserver

worker:
	$(CELERY) worker --loglevel=info --pool=solo

beat:
	$(CELERY) beat --loglevel=info

flower:
	$(CELERY) flower --port=5555

shell:
	$(PYTHON) manage.py shell_plus

migrate:
	$(PYTHON) manage.py makemigrations && $(PYTHON) manage.py migrate

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check . && $(PYTHON) -m black --check .

fmt:
	$(PYTHON) -m black . && $(PYTHON) -m ruff --fix .
