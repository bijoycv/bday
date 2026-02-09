#!/bin/sh

# Wait for the web container to be ready
sleep 10

echo "Starting cron scheduler for birthday wishes..."

# Run the scheduled wishes command every 15 minutes
while true; do
    echo "[$(date)] Running send_scheduled_wishes..."
    python manage.py send_scheduled_wishes
    echo "[$(date)] Sleeping for 15 minutes..."
    sleep 900
done
