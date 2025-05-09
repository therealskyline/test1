# Structure du Projet AnimeZone

Cette documentation décrit la nouvelle organisation du projet pour une meilleure maintenabilité.

## Structure des Dossiers

```
.
├── src/                   # Code source principal
│   ├── api/               # API Anime-Sama et intégrations externes
│   ├── core/              # Noyau de l'application
│   │   ├── app.py         # Application principale Flask
│   │   └── web_scraper.py # Utilitaire de scraping
│   ├── config/            # Fichiers de configuration
│   ├── docs/              # Documentation
│   └── scripts/           # Scripts utilitaires
│       ├── run_server.py  # Lancement du serveur
│       └── update_imports.py # Mise à jour des imports
├── static/                # Fichiers statiques (CSS, JS, images)
├── templates/             # Templates HTML
├── archives/              # Fichiers anciens, sauvegardes, fichiers supprimables
│   ├── backup/            # Sauvegardes
│   └── temp/              # Fichiers temporaires
└── workflows/             # Configuration des workflows Replit
```

## Principe d'Organisation

1. **Modulaire** : Chaque dossier a une responsabilité unique
2. **Cohérent** : Les fichiers sont regroupés par fonction
3. **Évolutif** : Facilite l'ajout de nouvelles fonctionnalités

## Migration

Pour adapter le code à cette nouvelle structure, utilisez le script `src/scripts/update_imports.py`.

## Démarrage

- Pour Replit : Utilisez `src/main.py` comme point d'entrée
- Pour le développement local : `python src/scripts/run_server.py`

## Archives

Les fichiers non essentiels sont stockés dans le dossier `archives` pour 
garder l'espace de travail propre tout en conservant les fichiers historiques.