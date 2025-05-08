#!/bin/bash
# Script d'installation et de préparation pour AnimeZone

echo "🌟 Préparation de l'environnement AnimeZone 🌟"
echo "=============================================="

# Vérifier si nous sommes dans le bon dossier
if [ ! -f "main.py" ]; then
    echo "❌ Erreur: Ce script doit être exécuté depuis le dossier AnimeZone"
    echo "   Veuillez vous placer dans le dossier AnimeZone et réessayer"
    exit 1
fi

# Vérifier si Python est disponible
if ! command -v python3 &> /dev/null; then
    echo "⚠️ Python 3 n'est pas installé. Utilisation de 'python' à la place."
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Vérifier si pip est disponible
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "❌ pip n'est pas installé. Veuillez l'installer avant de continuer."
    exit 1
fi

echo "📦 Installation des dépendances..."
$PYTHON_CMD -m pip install -r backend/config/requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de l'installation des dépendances."
    exit 1
fi

echo "🧹 Nettoyage des fichiers temporaires..."
# Supprimer les fichiers __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

echo "🔧 Configuration des permissions..."
# Rendre les scripts exécutables
chmod +x run.sh

echo "✅ Installation terminée avec succès! Vous pouvez maintenant lancer l'application avec:"
echo "   ./run.sh"