makemigrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate

start:
	python -m gunicorn -b 0.0.0.0:8000 core.wsgi

dev:
	python manage.py runserver

new-app:
	python manage.py startapp $(app_name) # make new-app app_name=core

