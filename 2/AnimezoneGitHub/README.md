# AnimeZone

AnimeZone est une plateforme de streaming d'anime moderne et fonctionnelle développée avec Flask. Elle permet aux utilisateurs de regarder et télécharger des épisodes d'anime facilement et gratuitement.

## Fonctionnalités

- 🎬 **Streaming d'anime** en français (VF) et en version originale sous-titrée (VOSTFR)
- 📱 **Interface responsive** pour une expérience optimale sur tous les appareils
- 🔍 **Recherche avancée** par titre, genre, et popularité
- 👤 **Profils utilisateurs** avec suivi de progression et favoris
- 💾 **Téléchargement des épisodes** pour un visionnage hors-ligne
- 🌐 **Support multilingue** pour les contenus disponibles en plusieurs langues

## Installation

1. Cloner le repository:
   ```bash
   git clone https://github.com/votre-username/AnimeZone.git
   cd AnimeZone
   ```

2. Installer les dépendances:
   ```bash
   pip install -r requirements.txt
   ```

3. Lancer l'application:
   ```bash
   python run.py
   ```

## Déploiement

Ce projet est configuré pour être facilement déployé sur Render. Consultez le fichier [deploy_to_render.md](deploy_to_render.md) pour les instructions détaillées.

## Structure du Projet

```
AnimeZone/
├── API/               # API pour l'accès aux données d'anime
├── static/           # Fichiers statiques (CSS, JS, images)
├── templates/        # Templates HTML
├── app.py            # Application Flask principale
├── main.py           # Point d'entrée pour Replit
├── run.py            # Script de lancement du serveur
└── requirements.txt  # Dépendances du projet
```

## Capture d'écran

![Aperçu d'AnimeZone](https://i.imgur.com/example.png)

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Crédits

Développé par [Votre Nom]

---

*AnimeZone - Regardez vos animes préférés, où que vous soyez.*