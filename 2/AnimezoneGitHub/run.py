#!/usr/bin/env python3
"""
Point d'entrée principal pour le site de streaming d'anime
Utilisé par Replit pour démarrer l'application
"""

import os
import sys
import subprocess
import signal
import time

def kill_existing_servers():
    """
    Arrête tous les processus Python existants pour éviter les conflits de ports
    Compatible avec Windows et Linux
    """
    try:
        import platform
        # Vérifier le système d'exploitation
        if platform.system() == "Windows":
            # Méthode pour Windows en utilisant taskkill
            try:
                subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq app.py"], 
                               shell=True, check=False)
                print("Serveurs existants arrêtés (Windows)")
            except Exception:
                print("Note: Impossible d'arrêter les serveurs existants sur Windows")
        else:
            # Méthode pour Linux/Unix en utilisant pkill
            subprocess.run(["pkill", "-f", "python.*app.py"], check=False)
            print("Serveurs existants arrêtés (Linux/Unix)")
        
        # Petit délai pour être sûr que le port est libéré
        time.sleep(1)
    except Exception as e:
        print(f"Note: {e}")

def main():
    """
    Script principal pour démarrer l'application web AnimeZone
    Ce script s'assure que l'application démarre avec les bonnes options
    pour être accessible à l'extérieur dans l'environnement Replit
    """
    # Arrêter d'abord les serveurs existants
    kill_existing_servers()
    
    # Obtenir le port depuis l'environnement (Replit définit cette variable)
    port = os.environ.get("PORT", "8080")
    
    # Imprimer des informations utiles
    print(f"Démarrage de l'application AnimeZone sur le port {port}")
    print(f"Répertoire courant: {os.getcwd()}")
    
    # Chemin vers l'application Flask
    app_path = "app.py"
    
    # Vérifier si le fichier de l'application existe
    if not os.path.exists(app_path):
        print(f"ERREUR: Le fichier {app_path} n'existe pas")
        sys.exit(1)
    else:
        print(f"Le fichier {app_path} existe!")
        
    # Vérifier que le dossier templates existe
    if not os.path.isdir("templates"):
        print(f"ERREUR: Le dossier templates n'existe pas")
        sys.exit(1)
    else:
        print(f"Le dossier templates existe!")
    
    # Démarrer l'application Flask
    try:
        # Configurer le gestionnaire de signal pour SIGINT (Ctrl+C)
        def signal_handler(sig, frame):
            print("\nArrêt du serveur...")
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        
        # Définir le port dans l'environnement pour que l'application Flask puisse l'utiliser
        os.environ["PORT"] = port
        
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