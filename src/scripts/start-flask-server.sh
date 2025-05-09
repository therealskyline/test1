#!/bin/bash
# Script pour démarrer le serveur Flask en arrière-plan
echo "Démarrage du serveur Flask d'AnimeZone..."

# Définir les variables d'environnement
export FLASK_APP=app.py
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

# Créer un répertoire pour les logs si nécessaire
mkdir -p logs

# Arrêter les serveurs existants (optionnel)
pkill -f "python run-server.py" || true

# Lancer le serveur avec redirection des logs
nohup python run-server.py > logs/server.log 2>&1 &
SERVER_PID=$!
echo "Serveur démarré avec PID: $SERVER_PID"
echo "Pour voir les logs, utilisez: tail -f logs/server.log"

# Vérifier que le serveur a bien démarré
sleep 3
if ps -p $SERVER_PID > /dev/null; then
  echo "Le serveur est actif et fonctionne en arrière-plan."
  echo "Accédez au site à l'adresse: http://localhost:8080"
else
  echo "ERREUR: Le serveur n'a pas pu démarrer correctement!"
  echo "Consultez les logs pour plus d'informations."
  cat logs/server.log
fi