#!/bin/bash
# Script pour démarrer le serveur en arrière-plan
echo "Démarrage du serveur en arrière-plan..."
nohup python run-server.py > server.log 2>&1 &
echo "Serveur démarré avec PID $!"
echo "Pour voir les logs, utilisez 'cat server.log'"