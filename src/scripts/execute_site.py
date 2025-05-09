#!/usr/bin/env python3
"""
Script de démarrage simplifié pour AnimeZone
Ce script démarre l'application Flask directement sans passer par run.py
"""

import os
import sys
from app import app

if __name__ == "__main__":
    # Définir le port (utiliser 5000 pour être compatible avec Replit)
    port = int(os.environ.get("PORT", 5000))
    
    print(f"Démarrage d'AnimeZone sur le port {port}...")
    print(f"Dossier des templates: {app.template_folder}")
    print(f"Templates disponibles: {os.listdir(app.template_folder)}")
    
    # Exécuter l'application
    app.run(host="0.0.0.0", port=port, debug=True)