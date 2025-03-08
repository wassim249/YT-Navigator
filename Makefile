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
	ruff format .
	black .
	isort .

lint-fix:
	ruff check . --fix
	ruff format .
	black .
	isort .

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


clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".DS_Store" -delete
	find . -name ".pytest_cache" -delete
	find . -name ".ruff_cache" -delete
	find . -name ".mypy_cache" -delete
	find . -name "migrations" -delete
