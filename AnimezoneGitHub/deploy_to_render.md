# Guide de Déploiement sur Render

## Préparation pour GitHub

1. **Créer un nouveau repository** sur GitHub
2. **Initialiser Git** dans le dossier AnimeZone:
   ```bash
   cd AnimeZone
   git init
   git add .
   git commit -m "Version initiale d'AnimeZone"
   git branch -M main
   git remote add origin https://github.com/VOTRE-UTILISATEUR/AnimeZone.git
   git push -u origin main
   ```

## Déploiement sur Render

1. **Créer un nouveau Web Service** sur [Render](https://dashboard.render.com/)
2. **Connecter à GitHub** et sélectionner votre repository AnimeZone
3. **Configurer le service**:
   - **Nom**: AnimeZone
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free

### Variables d'Environnement à Configurer

| Nom | Valeur |
|-----|--------|
| `PYTHON_VERSION` | `3.11.0` |
| `SESSION_SECRET` | `votre-clé-secrète` (générer une clé sécurisée) |

## Vérification

1. Une fois le déploiement terminé, Render fournira une URL de type `https://animezone.onrender.com`
2. Accédez à cette URL pour vérifier que votre application fonctionne correctement

## Solutions aux Problèmes Courants

### Base de Données SQLite

Si vous utilisez SQLite, assurez-vous que le chemin de la base de données est configuré pour fonctionner sur Render:

```python
# Dans app.py
db_path = os.environ.get('DATABASE_URL', 'sqlite:///anime.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_path
```

### Timeout de Déploiement

Si le déploiement échoue à cause d'un timeout, augmentez le délai dans `start.sh` en ajoutant:

```bash
# Augmenter le délai avant timeout
export GUNICORN_CMD_ARGS="--timeout 120"
```

### Logs

Pour consulter les logs de l'application sur Render:
1. Allez dans la section "Logs" de votre service sur le dashboard Render
2. Sélectionnez "Live" pour voir les logs en temps réel