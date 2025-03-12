#!/bin/bash
set -e

# Create log directory and file (no ownership changes needed since we set this up in Dockerfile)
echo "Setting up log directory and file..."
LOG_FILE="/app/logs/$(date +%Y-%m-%d).jsonl"
touch $LOG_FILE

# Ensure Hugging Face cache directory has correct permissions
if [ ! -w "/app/.cache/huggingface" ]; then
    echo "Warning: Hugging Face cache directory is not writable..."
    exit 1
fi

# Wait for the database to be ready
echo "Waiting for database to be ready..."
while ! python -c "import psycopg; psycopg.connect('postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}')" 2>/dev/null; do
    echo "Database not ready yet, retrying in 1 second..."
    sleep 1
done
echo "Database is ready!"

# Create PGVector tables if they don't exist
echo "Creating PGVector tables if they don't exist..."
python -c "
import psycopg
conn = psycopg.connect('postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}')
cursor = conn.cursor()
cursor.execute('''
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS langchain_pg_collection
(
    uuid      uuid    not null
        primary key,
    name      varchar not null
        unique,
    cmetadata json
);
CREATE TABLE IF NOT EXISTS langchain_pg_embedding
(
    id            varchar not null
        primary key,
    collection_id uuid
        references langchain_pg_collection
            on delete cascade,
    embedding     vector,
    document      varchar,
    cmetadata     jsonb
);
''')
conn.commit()
cursor.close()
conn.close()
print('Tables created successfully!')
"

# Apply database migrations
echo "Applying database migrations..."
python manage.py makemigrations admin app auth contenttypes sessions
python manage.py migrate
# Remove Migrations folder
rm -rf /app/app/migrations

# Start the application
echo "Starting application..."
exec "$@"
