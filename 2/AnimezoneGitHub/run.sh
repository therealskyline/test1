#!/bin/bash
# Script de lancement pour AnimeZone
echo "Démarrage de l'application AnimeZone..."

# Vérifier si Python est disponible
if ! command -v python3 &> /dev/null; then
    echo "Python 3 n'est pas installé. Utilisation de 'python' à la place."
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Définir les variables d'environnement
export HOST="0.0.0.0"
export PORT="8080"
export DEBUG="False"

# Lancer l'application
cd "$(dirname "$0")"
$PYTHON_CMD main.py

# En cas d'erreur
if [ $? -ne 0 ]; then
    echo "Erreur lors du démarrage de l'application."
    echo "Vérifiez que toutes les dépendances sont installées avec:"
    echo "pip install -r backend/config/requirements.txt"
    exit 1
fi