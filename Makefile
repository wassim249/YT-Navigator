makemigrations:
	python manage.py makemigrations $(app_name)

migrate:
	python manage.py migrate

prod:
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

help:
	@echo "Available commands:"
	@echo "  makemigrations   - Create new migrations based on changes"
	@echo "  migrate          - Apply migrations"
	@echo "  prod             - Run the application in production mode"
	@echo "  dev              - Run the application in development mode"
	@echo "  new-app         - Create a new Django app"
	@echo "  lint             - Run linting tools"
	@echo "  lint-fix         - Fix linting issues"
	@echo "  format           - Format code with black"
	@echo "  check-all        - Run linting and check formatting"
	@echo "  install-hooks    - Install pre-commit hooks"
	@echo "  run-hooks        - Run pre-commit hooks on all files"
	@echo "  clean            - Remove temporary files"
