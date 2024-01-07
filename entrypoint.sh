#!/bin/bash


# Run DB Migrations
flask db upgrade

# Start the application
gunicorn app:app -w 2 --threads 2 -b 0.0.0.0:5000 --reload
