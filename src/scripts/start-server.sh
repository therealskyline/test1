#!/bin/bash
# Script de démarrage simplifié pour le serveur de streaming d'anime

# Définit les variables d'environnement nécessaires
export FLASK_APP=app.py
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

# Démarrage du serveur avec le script simplifié
echo "Démarrage du serveur de streaming d'anime..."
python run-server.py