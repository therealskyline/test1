"""
Point d'entrée principal pour Replit
Ce fichier assure la compatibilité avec Replit
"""

from app import app as application

# Exposer app pour Replit
app = application

if __name__ == "__main__":
    # Ce bloc ne sera pas exécuté normalement sur Replit,
    # mais permet de tester localement
    app.run(host="0.0.0.0", port=8080, debug=False)