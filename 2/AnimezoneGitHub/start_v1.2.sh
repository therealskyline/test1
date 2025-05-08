#!/bin/bash
# Script de démarrage pour AnimeZone v1.2 (version GitHub avec correctifs)

echo "=== AnimeZone - Version GitHub 1.2 ==="
echo "- Interface améliorée avec chemins relatifs pour la barre de recherche"
echo "- Remplacement de Hunter x Hunter par Bleach"
echo "- Animes aléatoires dans 'Découvrir de Nouvelles Séries'"
echo "- Interface simplifiée sans étoiles de notation"

# S'assurer que le script est exécutable
chmod +x app.py
chmod +x run.py

# Démarrer le serveur
python run.py