"""
Script simplifié pour démarrer le serveur de streaming d'anime
Ce script lance directement le serveur Flask avec les configurations optimales pour Replit
"""

import os
import sys
import logging
from app import app  # Importe l'application Flask depuis app.py

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Point d'entrée principal
if __name__ == "__main__":
    logger.info("Démarrage du serveur de streaming d'anime...")
    
    # Vérification de l'environnement
    logger.info(f"Répertoire courant: {os.getcwd()}")
    
    # Informations sur les fichiers essentiels
    if os.path.exists("app.py"):
        logger.info("Le fichier app.py existe dans le répertoire courant")
    else:
        logger.error("ERREUR: Le fichier app.py est introuvable!")
        sys.exit(1)
    
    if os.path.exists("static/data/anime.json"):
        logger.info("Le fichier static/data/anime.json existe")
    else:
        logger.warning("ATTENTION: Le fichier anime.json est introuvable!")
    
    # Démarrage du serveur sur 0.0.0.0 pour être accessible sur Replit
    logger.info("Démarrage du serveur sur 0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)