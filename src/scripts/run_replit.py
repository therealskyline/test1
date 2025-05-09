#!/usr/bin/env python3
"""
Point d'entrée principal pour le site de streaming d'anime sur Replit
Script optimisé pour l'environnement Replit
"""

import os
import sys
import subprocess
import signal
import time

def kill_existing_servers():
    """
    Arrête tous les processus Python existants pour éviter les conflits de ports
    """
    try:
        # Méthode pour Replit (Linux)
        subprocess.run(["pkill", "-f", "python.*app.py"], check=False)
        print("Serveurs existants arrêtés")
        
        # Petit délai pour être sûr que le port est libéré
        time.sleep(1)
    except Exception as e:
        print(f"Note: {e}")

def main():
    """
    Script principal pour démarrer l'application web AnimeZone
    Ce script s'assure que l'application démarre avec les bonnes options
    pour être accessible sur Replit
    """
    # Arrêter d'abord les serveurs existants
    kill_existing_servers()
    
    # Obtenir le port depuis l'environnement (Replit définit normalement PORT=443)
    port = os.environ.get("PORT", "5000")
    
    # Imprimer des informations utiles
    print(f"Démarrage d'AnimeZone sur le port {port}")
    print(f"Répertoire courant: {os.getcwd()}")
    
    # Vérifier si app.py existe dans le répertoire courant
    app_path = "app.py"
    if os.path.exists(app_path):
        print(f"Le fichier {app_path} existe dans le répertoire courant")
    else:
        print(f"AVERTISSEMENT: Le fichier {app_path} n'existe pas dans le répertoire courant")
    
    # Vérifier si les templates existent
    if os.path.isdir("templates"):
        print(f"Le dossier templates existe dans le répertoire courant")
        print(f"Contenu du dossier templates: {os.listdir('templates')}")
    else:
        print(f"AVERTISSEMENT: Le dossier templates n'existe pas dans le répertoire courant")
    
    # Vérifier si static/data/anime.json existe
    anime_json_path = "static/data/anime.json"
    if os.path.exists(anime_json_path):
        print(f"Le fichier {anime_json_path} existe")
    else:
        print(f"AVERTISSEMENT: Le fichier {anime_json_path} n'existe pas")
    
    # Démarrer l'application Flask
    try:
        # Configurer le gestionnaire de signal pour SIGINT (Ctrl+C)
        def signal_handler(sig, frame):
            print("\nArrêt du serveur...")
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        
        # Définir le port dans l'environnement pour que l'application Flask puisse l'utiliser
        os.environ["PORT"] = port
        
        # Définir FLASK_APP pour que Flask sache quel fichier exécuter
        os.environ["FLASK_APP"] = app_path
        
        # Désactiver le mode debug pour éviter les redémarrages automatiques qui causent des problèmes
        os.environ["FLASK_DEBUG"] = "0"
        
        # Imprimer la commande exécutée
        cmd = [sys.executable, app_path, "--host", "0.0.0.0", "--port", port]
        print("Exécution de:", " ".join(cmd))
        
        # Exécuter l'application
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("Arrêt du serveur...")
    except Exception as e:
        print(f"ERREUR lors du démarrage: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()