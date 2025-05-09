"""
Point d'entrée principal restructuré pour Replit
Ce fichier assure la compatibilité avec Replit en utilisant la nouvelle structure de dossiers
"""

import sys
import os

# Ajout du répertoire parent au path pour pouvoir importer depuis src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import de l'application Flask depuis le package core
from src.core.app import app as application

# Exposer app pour Replit
app = application

if __name__ == "__main__":
    # Ce bloc ne sera pas exécuté normalement sur Replit,
    # mais permet de tester localement
    app.run(host="0.0.0.0", port=8080, debug=False)