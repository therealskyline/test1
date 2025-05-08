# AnimeZone - Version GitHub 1.2

Cette version d'AnimeZone apporte des améliorations importantes pour résoudre les problèmes de la version 1.1, notamment les bugs de navigation et le remplacement de Hunter x Hunter.

## Nouvelles fonctionnalités et corrections

### 1. Correction des problèmes de navigation
- **Problème résolu** : La barre de recherche ne fonctionnait pas correctement dans la version 1.1
- **Solution** : Utilisation de chemins relatifs (`./search?query=`) au lieu de chemins absolus (`/search?query=`)
- **Fichiers modifiés** : `static/js/main.js`

### 2. Remplacement de Hunter x Hunter par Bleach
- **Problème résolu** : Hunter x Hunter causait des problèmes de chargement
- **Solution** : Remplacement par Bleach dans toutes les références (IDs, descriptions, etc.)
- **Fichiers modifiés** : `app.py`

### 3. Conservation des fonctionnalités de la version 1.1
- Animes aléatoires dans la section "Découvrir de Nouvelles Séries"
- Interface simplifiée sans étoiles de notation
- Organisation horizontale des saisons

## Comment utiliser cette version

1. Décompressez l'archive sur votre serveur ou sur votre PC
2. Exécutez le script de démarrage :
   ```bash
   chmod +x start_v1.2.sh
   ./start_v1.2.sh
   ```
   
3. Accédez à l'application via votre navigateur à l'adresse : `http://localhost:8080`

## Compatibilité

Cette version est optimisée pour fonctionner dans les environnements suivants :
- GitHub Pages
- PC local (Windows/Linux)
- Render.com

## Notes de développement

- Correction de bugs de navigation dus aux chemins absolus
- Remplacement complet de Hunter x Hunter par Bleach pour éviter les problèmes de chargement
- Optimisation des performances pour un démarrage plus rapide
- Conservation des fonctionnalités d'animes aléatoires de la version 1.1