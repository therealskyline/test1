#!/bin/bash
# Script de démarrage pour Render

# Exécuter gunicorn
exec gunicorn --bind 0.0.0.0:$PORT app:app
