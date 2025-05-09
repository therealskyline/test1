# AnimeZone

Site de streaming d'anime avec une interface moderne et une grande collection d'anime.

## Caractéristiques

- Navigation facile dans les séries d'anime
- Lecteur vidéo intégré avec plusieurs sources
- Téléchargement d'épisodes (si disponible)
- Système de compte utilisateur
- Progression de visionnage sauvegardée automatiquement
- Liste de favoris personnelle
- Recherche et filtrage par genres

## Démarrage rapide

Pour démarrer le serveur localement :

```bash
./start-server.sh
```

Le site sera accessible à l'adresse : http://localhost:8080

## Structure du projet

- `app.py` : Application principale Flask
- `run-server.py` : Script de démarrage simplifié
- `static/` : Ressources statiques (CSS, JS, images)
- `static/data/anime.json` : Base de données locale des animes
- `templates/` : Templates HTML
- `API/` : API Anime-Sama pour récupérer les données

## Commandes utiles

- Démarrer le serveur : `./start-server.sh`
- Rechercher un anime : Utilisez la barre de recherche sur le site
- Télécharger un épisode : Bouton de téléchargement sur la page de lecture