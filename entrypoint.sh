#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Run migrations
python manage.py migrate
# Collect static files
python manage.py collectstatic --no-input --clear

exec "$@"
