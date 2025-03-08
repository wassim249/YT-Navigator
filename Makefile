makemigrations:
	python manage.py makemigrations $(app_name)

migrate:
	python manage.py migrate

start:
	python -m gunicorn -b 0.0.0.0:8000 core.wsgi

dev:
	python manage.py runserver

new-app:
	python manage.py startapp $(app_name) # make new-app app_name=core

lint:
	ruff check .

lint-fix:
	ruff check . --fix

format:
	black .

check-all: lint format
	ruff check .
	black --check .

install-hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg
	pre-commit install --hook-type pre-push

run-hooks:
	pre-commit run --all-files
