#!/bin/bash

# Wait for the database to be ready
echo "Waiting for database to be ready..."
while ! nc -z database 5432; do
  sleep 0.1
done
echo "Database is ready!"

# Run DB Migrations
flask db upgrade

# Start the application
gunicorn app:app -w 2 --threads 2 -b 0.0.0.0:5000 --reload

