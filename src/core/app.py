import os
import re
import json
import sys
import logging
import datetime
import shutil
import asyncio
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ajouter le chemin de l'API pour pouvoir l'importer
API_DIR = os.path.join(os.path.dirname(__file__), 'API')
if os.path.exists(API_DIR):
    sys.path.append(API_DIR)
else:
    # Essayer l'ancien chemin pour compatibilité
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API'))

try:
    from anime_sama_api.top_level import AnimeSama
    API_IMPORT_SUCCESS = True
    logger.info("Import de l'API Anime-Sama réussi!")
except ImportError as e:
    API_IMPORT_SUCCESS = False
    logger.error(f"Erreur d'import de l'API Anime-Sama: {e}")

# URL de base pour l'API Anime-Sama
ANIME_SAMA_BASE_URL = "https://anime-sama.fr/"

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Initialize database
# Utiliser SQLite en attendant de résoudre les problèmes avec PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///anime.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Liste des animes populaires à précharger au démarrage du serveur
POPULAR_ANIMES = [
    {"title": "One Piece", "id": 183},
    {"title": "Bleach", "id": 168},
    {"title": "Attack on Titan", "id": 169},
    {"title": "Death Note", "id": 170},
    {"title": "Demon Slayer", "id": 171},
    {"title": "My Hero Academia", "id": 172}, 
    {"title": "Jujutsu Kaisen", "id": 173},
    {"title": "Hunter x Hunter", "id": 174},
    {"title": "Dragon Ball", "id": 166},
    {"title": "Naruto", "id": 175}
]

# Dictionnaire global pour stocker les IDs des animes populaires
POPULAR_ANIME_IDS = {}

# Liste des animes populaires à précharger
POPULAR_ANIMES = [
    {"title": "One Piece", "id": 1},
    {"title": "Naruto", "id": 8},
    {"title": "Dragon Ball", "id": 3},
    {"title": "Death Note", "id": 5},
    {"title": "My Hero Academia", "id": 6},
    {"title": "Hunter x Hunter", "id": 7},
    {"title": "Demon Slayer", "id": 4},
    {"title": "Mashle", "id": 2},
    {"title": "Fairy Tail", "id": 9},
    {"title": "Sword Art Online", "id": 10},
    {"title": "Jujutsu Kaisen", "id": 11}
]

# Créer les tables et initialiser la base de données
with app.app_context():
    db.create_all()
    logger.info("Création des tables terminée")

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    # Nouvelles colonnes pour stocker les préférences utilisateur
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Modèle pour suivre la progression des utilisateurs sur les animes
class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    anime_id = db.Column(db.Integer, nullable=False)
    season_number = db.Column(db.Integer, nullable=False)
    episode_number = db.Column(db.Integer, nullable=False)
    time_position = db.Column(db.Float, default=0)  # Position en secondes dans l'épisode
    completed = db.Column(db.Boolean, default=False)
    last_watched = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('progress', lazy='dynamic'))

    # Contrainte d'unicité pour éviter les doublons
    __table_args__ = (
        db.UniqueConstraint('user_id', 'anime_id', 'season_number', 'episode_number'),
    )

# Modèle pour les favoris des utilisateurs
class UserFavorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    anime_id = db.Column(db.Integer, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('favorites', lazy='dynamic'))

    # Contrainte d'unicité pour éviter les doublons
    __table_args__ = (
        db.UniqueConstraint('user_id', 'anime_id'),
    )

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# S'assurer que tous les animes dans la liste possèdent un champ anime_id
def ensure_anime_id_in_data(data):
    """
    S'assure que tous les animes dans la liste possèdent un champ anime_id.
    Si ce champ est manquant, il est ajouté avec la même valeur que l'id.
    Aussi valide si has_episodes est présent et l'ajoute par défaut à True si absent.
    
    :param data: Liste d'animes à vérifier
    :return: Liste d'animes mise à jour
    """
    updated_data = []
    for anime in data:
        # Vérifier si l'anime a un ID
        if 'id' in anime:
            # Vérifier si anime_id est présent, sinon l'ajouter
            if 'anime_id' not in anime:
                anime['anime_id'] = anime['id']
            
            # Vérifier si has_episodes est présent, sinon l'ajouter (par défaut True)
            if 'has_episodes' not in anime:
                anime['has_episodes'] = True
        
        updated_data.append(anime)
    
    return updated_data

# Fonction pour sauvegarder les données anime dans le fichier JSON
def save_anime_data(data):
    try:
        # Définir le chemin absolu vers le fichier JSON
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'static', 'data', 'anime.json')
        
        # Vérifier si le répertoire existe, sinon le créer
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        # Déterminer le format à sauvegarder (liste ou dictionnaire avec clé 'anime')
        # On préfère conserver le format original
        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                original_data = json.load(f)
                is_dict_format = isinstance(original_data, dict) and 'anime' in original_data
            except:
                # En cas d'erreur, utiliser le format dictionnaire par défaut
                is_dict_format = True
        
        # Sauvegarder dans le format approprié
        with open(json_path, 'w', encoding='utf-8') as f:
            if is_dict_format:
                json.dump({'anime': data}, f, indent=4, ensure_ascii=False)
            else:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Données anime sauvegardées: {len(data)} animes")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des données anime: {e}")
        return False

# Load anime data from JSON file
def load_anime_data():
    try:
        # Définir le chemin absolu vers le fichier JSON
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'static', 'data', 'anime.json')
        logger.info(f"Chargement du fichier anime.json depuis: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure we're getting a dictionary with an anime key
            if isinstance(data, dict) and 'anime' in data:
                logger.info(f"Données chargées: {len(data['anime'])} animes trouvés")
                # S'assurer que tous les animes ont un anime_id
                animes = ensure_anime_id_in_data(data['anime'])
                return animes
            elif isinstance(data, list):
                # If it's just a list (no wrapper), return it directly
                logger.info(f"Données chargées (format liste): {len(data)} animes trouvés")
                # S'assurer que tous les animes ont un anime_id
                animes = ensure_anime_id_in_data(data)
                return animes
            else:
                # Create a default structure
                logger.warning("Anime data file has unexpected format. Creating default structure.")
                return []
    except FileNotFoundError:
        logger.error(f"Anime data file not found. Creating empty data file.")
        # Create empty data file with proper structure
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'static', 'data')
        json_path = os.path.join(data_dir, 'anime.json')

        os.makedirs(data_dir, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({'anime': []}, f, indent=4)
        logger.info(f"Fichier vide créé: {json_path}")
        return []
    except json.JSONDecodeError:
        logger.error("Error decoding anime data file. Returning empty list.")
        return []

# Fonction pour précharger One Piece et vérifier qu'il est accessible
def preload_one_piece():
    """
    Fonction spéciale pour précharger et vérifier One Piece, qui est l'anime le plus critique
    pour les utilisateurs du site. Cette fonction s'assure que One Piece est correctement
    présent dans la base de données avec le bon ID et les bonnes saisons.
    """
    global POPULAR_ANIME_IDS
    try:
        logger.info("Préchargement spécial pour One Piece...")
        anime_data = load_anime_data()
        
        # Rechercher One Piece par titre
        one_piece = next((a for a in anime_data if a.get('title', '').lower() == "one piece"), None)
        
        if one_piece:
            # Vérifier que l'anime_id est présent et cohérent
            actual_id = one_piece.get('id')
            anime_id = one_piece.get('anime_id', actual_id)
            
            if 'anime_id' not in one_piece:
                one_piece['anime_id'] = actual_id
                logger.info(f"Ajout du champ anime_id={actual_id} à One Piece")
            
            # S'assurer que les saisons sont organisées correctement si elles existent
            if 'seasons' in one_piece and one_piece['seasons']:
                # On trie les saisons comme dans anime_detail
                regular_seasons = []
                kai_seasons = []
                film_seasons = []
                
                for season in one_piece.get('seasons', []):
                    season_name = season.get('name', '')
                    if season.get('season_number') == 99:
                        film_seasons.append(season)
                    elif 'Kai' in season_name:
                        kai_seasons.append(season)
                    else:
                        regular_seasons.append(season)
                
                # Tri interne des saisons par numéro
                regular_seasons.sort(key=lambda s: s.get('season_number', 0))
                kai_seasons.sort(key=lambda s: s.get('season_number', 0))
                
                # Reconstituer la liste complète des saisons
                one_piece['seasons'] = regular_seasons + film_seasons + kai_seasons
                logger.info(f"One Piece: {len(regular_seasons)} saisons normales, {len(film_seasons)} films, {len(kai_seasons)} saisons Kai")
            
            # Enregistrer One Piece dans les animes populaires
            POPULAR_ANIME_IDS["one piece"] = {
                'id': actual_id,
                'anime_id': anime_id
            }
            
            # Marquer One Piece comme ayant des épisodes
            one_piece['has_episodes'] = True
            
            # Mettre à jour la base de données
            updated = False
            for i, anime in enumerate(anime_data):
                if anime.get('title', '').lower() == "one piece":
                    anime_data[i] = one_piece
                    updated = True
                    break
            
            if updated:
                save_anime_data(anime_data)
                logger.info(f"One Piece a été mis à jour dans la base de données (ID: {actual_id}, anime_id: {anime_id})")
            
            return True
        else:
            logger.warning("One Piece n'a pas été trouvé dans la base de données!")
            return False
    except Exception as e:
        logger.error(f"Erreur lors du préchargement de One Piece: {e}")
        return False

# Fonction pour créer des données par défaut pour la section découverte
def create_default_discover_data(all_anime_data):
    """
    Crée des données par défaut pour la section 'Découvrir de Nouvelles Séries'
    en utilisant les animes populaires.
    
    :param all_anime_data: Données de tous les animes disponibles
    :return: Liste d'animes pour la section découverte
    """
    logger.info("Création de données par défaut pour la section découverte")
    default_data = []
    
    # Utiliser les données des animes populaires comme base
    for popular in POPULAR_ANIMES:
        # Chercher l'anime dans notre base de données
        found = False
        for anime in all_anime_data:
            if anime.get('title', '').lower() == popular["title"].lower():
                # Ajouter l'anime trouvé aux données par défaut
                anime_copy = anime.copy()
                # S'assurer que les IDs sont cohérents
                anime_copy['id'] = popular["id"]
                anime_copy['anime_id'] = popular["id"]
                # Marquer comme ayant des épisodes
                anime_copy['has_episodes'] = True
                default_data.append(anime_copy)
                found = True
                break
        
        # Si non trouvé, ajouter une version simplifiée
        if not found:
            default_data.append({
                'id': popular["id"],
                'anime_id': popular["id"],
                'title': popular["title"],
                'description': f"Découvrez {popular['title']}, un anime populaire sélectionné pour vous.",
                'image': f"https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/{popular['title'].lower().replace(' ', '-')}.jpg",
                'genres': ['Action', 'Aventure'],
                'has_episodes': True,
            })
    
    logger.info(f"Données par défaut créées avec {len(default_data)} animes populaires")
    return default_data

# Fonction pour précharger les animes populaires au démarrage du serveur
def preload_popular_animes():
    """
    Charge les animes populaires définis dans POPULAR_ANIMES au démarrage du serveur.
    S'assure que ces animes sont présents et que leurs IDs sont correctement enregistrés.
    Renseigne le dictionnaire global POPULAR_ANIME_IDS.
    """
    global POPULAR_ANIME_IDS
    try:
        logger.info("Préchargement des animes populaires...")
        # Charger les données complètes
        anime_data = load_anime_data()
        
        # Précharger One Piece en premier (cas spécial)
        preload_one_piece()
        
        # Vérifier chaque anime populaire
        for popular_anime in POPULAR_ANIMES:
            title = popular_anime["title"]
            expected_id = popular_anime["id"]
            
            # Ignorer One Piece qui a déjà été traité
            if title.lower() == "one piece":
                continue
                
            # Rechercher l'anime par titre (cas insensible)
            anime = next((a for a in anime_data if a.get('title', '').lower() == title.lower()), None)
            
            if anime:
                # Enregistrer l'ID trouvé
                actual_id = anime.get('id')
                anime_id = anime.get('anime_id', actual_id)
                
                # Mettre à jour l'ID pour correspondre à celui attendu
                if actual_id != expected_id:
                    logger.info(f"Mise à jour de l'ID de {title}: {actual_id} -> {expected_id}")
                    anime['id'] = expected_id
                    anime['anime_id'] = expected_id
                    
                    # Mettre à jour la base de données
                    for i, a in enumerate(anime_data):
                        if a.get('id') == actual_id or a.get('title', '').lower() == title.lower():
                            anime_data[i] = anime
                            save_anime_data(anime_data)
                            logger.info(f"Mise à jour de l'ID pour {title}: {actual_id} -> {expected_id}")
                            break
                
                # Ajouter anime_id s'il n'existe pas
                if 'anime_id' not in anime:
                    anime['anime_id'] = expected_id
                    # Mettre à jour la base de données
                    for i, a in enumerate(anime_data):
                        if a.get('id') == expected_id:
                            anime_data[i] = anime
                            save_anime_data(anime_data)
                            logger.info(f"Ajout du champ anime_id={expected_id} à {title}")
                            break
                
                POPULAR_ANIME_IDS[title.lower()] = {
                    'id': expected_id,
                    'anime_id': expected_id
                }
                logger.info(f"Anime populaire préchargé: {title} (ID: {expected_id})")
            else:
                # L'anime n'existe pas, le créer avec l'ID attendu
                logger.info(f"Création de l'anime populaire: {title} (ID: {expected_id})")
                
                # Essayer de récupérer les vrais données depuis l'API Anime-Sama
                try:
                    # Rechercher l'anime dans l'API
                    found_animes = search_anime(title, limit=5, fetch_seasons=True)
                    logger.info(f"Recherche de {title} via API: {len(found_animes)} résultats trouvés")
                    
                    # Filtrer pour trouver le bon anime (par titre exact)
                    exact_match = None
                    for found in found_animes:
                        if found.get('title', '').lower() == title.lower():
                            exact_match = found
                            break
                    
                    # Si pas de correspondance exacte, prendre le premier résultat
                    if not exact_match and found_animes:
                        exact_match = found_animes[0]
                        logger.info(f"Pas de correspondance exacte pour {title}, utilisation de {exact_match.get('title')}")
                    
                    if exact_match:
                        # Utiliser les données réelles de l'API avec l'ID attendu
                        exact_match['id'] = expected_id
                        exact_match['anime_id'] = expected_id
                        exact_match['has_episodes'] = True
                        
                        # S'assurer que toutes les saisons ont un nom correct
                        if 'seasons' in exact_match:
                            for season in exact_match['seasons']:
                                if season.get('season_number') == 99:
                                    season['name'] = "Films"
                        
                        new_anime = exact_match
                        logger.info(f"Données réelles récupérées pour {title}")
                    else:
                        raise Exception("Aucun résultat trouvé dans l'API")
                except Exception as e:
                    logger.warning(f"Échec de récupération des données via API pour {title}: {e}")
                    logger.warning("Création d'une structure par défaut")
                    
                    # Structure par défaut (une seule saison, pas de films)
                    seasons = [
                        {
                            "season_number": 1,
                            "name": "Saison 1",
                            "episodes": [
                                {
                                    "episode_number": 1,
                                    "title": "Épisode 1",
                                    "description": "Premier épisode",
                                    "duration": 24,
                                    "languages": ["VOSTFR", "VF"],
                                    "urls": {}
                                }
                            ]
                        }
                    ]
                    
                    # Déterminer l'image en fonction du titre
                    image_url = f"https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/{title.lower().replace(' ', '-')}.jpg"
                    
                    # Créer l'anime avec l'ID attendu (structure simplifiée sans saison "Films")
                    new_anime = {
                        "id": expected_id,
                        "anime_id": expected_id,
                        "title": title,
                        "description": f"Découvrez {title}, un anime populaire.",
                        "image": image_url,
                        "genres": ["Action", "Aventure"],
                        "rating": 8.5,
                        "featured": True,
                        "has_episodes": True,
                        "seasons": seasons,
                        "seasons_fetched": True
                    }
                
                # Ajouter à la liste des animes
                anime_data.append(new_anime)
                save_anime_data(anime_data)
                
                # Ajouter aux animes populaires
                POPULAR_ANIME_IDS[title.lower()] = {
                    'id': expected_id,
                    'anime_id': expected_id
                }
                logger.info(f"Anime populaire créé: {title} (ID: {expected_id})")
        
        logger.info(f"Préchargement terminé. {len(POPULAR_ANIME_IDS)} animes populaires trouvés.")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du préchargement des animes populaires: {e}")
        return False

# Load discover anime data from JSON file
def load_discover_anime_data():
    try:
        # S'assurer que les animes populaires sont préchargés
        if not POPULAR_ANIME_IDS:
            preload_popular_animes()
            logger.info("Préchargement forcé des animes populaires depuis load_discover_anime_data")
            
        # Définir le chemin absolu vers le fichier JSON de découverte
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'data_discover.json')
        logger.info(f"Chargement du fichier data_discover.json depuis: {json_path}")

        # Charger d'abord les données complètes pour vérifier les id existants
        all_anime_data = load_anime_data()
        anime_id_mapping = {}
        
        # Utiliser les animes préchargés en priorité (IDs fiables)
        for title_lower, ids in POPULAR_ANIME_IDS.items():
            anime_id_mapping[title_lower] = ids
        
        # Compléter avec d'autres animes si nécessaire
        for anime in all_anime_data:
            if anime.get('title'):
                title_lower = anime['title'].lower()
                if title_lower not in anime_id_mapping:
                    anime_id_mapping[title_lower] = {
                        'id': anime.get('id', 0),
                        'anime_id': anime.get('anime_id', anime.get('id', 0))
                    }

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if isinstance(data, list):
                logger.info(f"Données chargées (format liste): {len(data)} animes trouvés")
                
                # Créer une liste pour stocker les animes valides
                valid_animes = []
                
                # Mettre à jour les IDs des animes de découverte en fonction des animes existants
                for anime in data:
                    title_lower = anime.get('title', '').lower()
                    
                    # S'assurer que l'anime a le champ has_episodes (par défaut True)
                    if 'has_episodes' not in anime:
                        anime['has_episodes'] = True
                    
                    # Vérifier s'il existe déjà dans notre base
                    if title_lower in anime_id_mapping:
                        # Utiliser l'ID réel de l'anime existant
                        anime['id'] = anime_id_mapping[title_lower]['id']
                        anime['anime_id'] = anime_id_mapping[title_lower]['anime_id']
                        logger.info(f"ID d'anime mis à jour: {anime['title']} -> id:{anime['id']}, anime_id:{anime['anime_id']}")
                        valid_animes.append(anime)
                    else:
                        # Chercher dans POPULAR_ANIMES
                        for popular in POPULAR_ANIMES:
                            if popular["title"].lower() == title_lower:
                                # Utiliser l'ID attendu pour cet anime populaire
                                anime['id'] = popular["id"]
                                anime['anime_id'] = popular["id"]
                                valid_animes.append(anime)
                                logger.info(f"Anime populaire ajouté à la découverte: {anime['title']} (ID: {anime['id']})")
                                break
                
                # Ne garder que les animes qui ont des épisodes
                valid_animes = [a for a in valid_animes if a.get('has_episodes', True)]
                
                # S'assurer que tous les animes ont bien un anime_id
                valid_animes = ensure_anime_id_in_data(valid_animes)
                
                return valid_animes
                
            elif isinstance(data, dict) and 'anime' in data:
                logger.info(f"Données chargées (format dict): {len(data['anime'])} animes trouvés")
                
                # Créer une liste pour stocker les animes valides
                valid_animes = []
                
                # Mettre à jour les IDs des animes de découverte
                for anime in data['anime']:
                    title_lower = anime.get('title', '').lower()
                    
                    # S'assurer que l'anime a le champ has_episodes (par défaut True)
                    if 'has_episodes' not in anime:
                        anime['has_episodes'] = True
                    
                    # Vérifier s'il existe déjà dans notre base
                    if title_lower in anime_id_mapping:
                        # Utiliser l'ID réel de l'anime existant
                        anime['id'] = anime_id_mapping[title_lower]['id']
                        anime['anime_id'] = anime_id_mapping[title_lower]['anime_id']
                        valid_animes.append(anime)
                    else:
                        # Chercher dans POPULAR_ANIMES
                        for popular in POPULAR_ANIMES:
                            if popular["title"].lower() == title_lower:
                                # Utiliser l'ID attendu pour cet anime populaire
                                anime['id'] = popular["id"]
                                anime['anime_id'] = popular["id"]
                                valid_animes.append(anime)
                                logger.info(f"Anime populaire ajouté à la découverte: {anime['title']} (ID: {anime['id']})")
                                break
                
                # Ne garder que les animes qui ont des épisodes
                valid_animes = [a for a in valid_animes if a.get('has_episodes', True)]
                
                # S'assurer que tous les animes ont un anime_id
                valid_animes = ensure_anime_id_in_data(valid_animes)
                
                return valid_animes
                
            else:
                # Create a default structure
                logger.warning("Format de fichier de découverte inattendu. Utilisation des animes populaires.")
                return create_default_discover_data(all_anime_data)
    except FileNotFoundError:
        logger.error(f"Fichier de découverte non trouvé, création de données par défaut")
        # Utiliser les animes populaires comme données par défaut
        default_data = create_default_discover_data(all_anime_data)
        
        # Créer le fichier de découverte avec les données par défaut
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'data_discover.json')
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Fichier de découverte créé avec {len(default_data)} animes populaires")
        return default_data
    except json.JSONDecodeError:
        logger.error("Error decoding anime data file. Returning empty list.")
        return []

# Fonction pour rechercher des animes avec l'API Anime-Sama
async def search_anime_api(query, limit=20, fetch_seasons=False):
    """
    Recherche des animes en utilisant l'API Anime-Sama de manière simplifiée
    :param query: Texte de recherche
    :param limit: Nombre maximum de résultats à retourner (défaut: 20)
    :param fetch_seasons: Si True, récupère également les saisons et épisodes pour chaque anime
    :return: Liste des animes trouvés (limitée à 'limit', avec peu de détails)
    """
    try:
        if not API_IMPORT_SUCCESS:
            logger.error("L'API Anime-Sama n'est pas disponible")
            return []

        # Cas particulier pour les animes populaires qui peuvent avoir des problèmes avec certaines saisons
        popular_anime_queries = {
            "naruto": "Naruto",
            "bleach": "Bleach",
            "one piece": "One Piece",
            "hunter x hunter": "Hunter x Hunter",
            "dragon ball": "Dragon Ball"
        }
        
        # Vérifier si la requête correspond à un anime populaire connu
        found_popular_anime = None
        for key, value in popular_anime_queries.items():
            if key in query.lower():
                found_popular_anime = value
                logger.info(f"Requête pour un anime populaire détectée: {found_popular_anime}")
                # Pour les animes populaires, toujours rechercher avec le nom exact
                query = value
                # Et augmenter la limite pour maximiser les chances de trouver toutes les saisons
                limit = max(limit, 50)
                logger.info(f"Limite augmentée à {limit} pour anime populaire: {found_popular_anime}")
                break

        logger.info(f"Recherche d'anime via l'API pour: {query} (limite: {limit})")
        api = AnimeSama(ANIME_SAMA_BASE_URL)
        results = await api.search(query)

        if not results:
            logger.info(f"Aucun résultat trouvé pour: {query}")
            return []

        # Filtrer les résultats pour ne garder que les animes (pas les scans/mangas)
        filtered_results = []
        for anime in results:
            # Vérification simplifiée
            is_anime = True
            try:
                if hasattr(anime, 'is_manga') and callable(anime.is_manga) and anime.is_manga():
                    is_anime = False
            except Exception:
                pass

            if is_anime:
                filtered_results.append(anime)
                # Limite très tôt le nombre de résultats traités
                if len(filtered_results) >= limit:
                    break

        logger.info(f"Nombre d'animes après filtrage: {len(filtered_results)}")

        # Convertir les résultats de l'API au format attendu par l'application, mais de façon minimaliste
        anime_list = []

        # Charger les données existantes pour la gestion des IDs
        current_data = load_anime_data()

        # Trouver le plus grand ID existant pour attribuer de nouveaux IDs uniques
        next_id = 1
        if current_data:
            next_id = max(int(a.get('id', 0)) for a in current_data) + 1

        for i, anime in enumerate(filtered_results):
            # Pour les animes populaires, toujours récupérer les saisons pour vérifier la qualité
            if found_popular_anime and anime.name.lower() == found_popular_anime.lower():
                fetch_seasons_for_this_anime = True
                logger.info(f"Force la récupération des saisons pour {anime.name} (anime populaire)")
            else:
                fetch_seasons_for_this_anime = fetch_seasons

            # Rechercher si l'anime existe déjà dans notre base locale
            existing_anime = next((a for a in current_data if a.get('title', '').lower() == anime.name.lower()), None)

            # Si l'anime existe déjà, on le réutilise directement
            if existing_anime:
                # Mais on vérifie si on doit récupérer les saisons
                if (fetch_seasons_for_this_anime and not existing_anime.get('seasons_fetched', False)):
                    logger.info(f"Récupération des saisons pour l'anime existant: {existing_anime['title']}")
                    try:
                        existing_anime = await fetch_anime_seasons(anime, existing_anime)
                    except Exception as e:
                        logger.error(f"Erreur lors de la récupération des saisons pour {existing_anime['title']}: {e}")
                anime_list.append(existing_anime)
                continue

            # Créer une entrée minimale pour cet anime 
            anime_id = next_id + i

            # Récupérer l'URL de l'image de base
            image_url = ''
            if hasattr(anime, 'image_url') and anime.image_url:
                image_url = anime.image_url

            # Formater l'image correctement
            if not image_url or not image_url.startswith(('http://', 'https://')):
                image = '/static/img/anime-placeholder.jpg'
            else:
                image = image_url

            # Version simplifiée des saisons - juste une saison par défaut pour commencer
            seasons_data = [{
                'season_number': 1,
                'name': "Saison 1",
                'episodes': []
            }]

            # Créer une entrée anime minimale
            anime_entry = {
                'id': anime_id,
                'anime_id': anime_id,  # Ajouter anime_id pour éviter les erreurs 404
                'title': anime.name,
                'original_title': anime.name,
                'description': 'Chargez la page de l\'anime pour voir sa description',
                'image': image,
                'image_url': image_url,
                'genres': anime.genres if hasattr(anime, 'genres') else [],
                'seasons': seasons_data,
                'featured': False,
                'year': '',
                'status': 'Disponible',
                'rating': 7.5,
                'languages': ['VOSTFR'],
                'seasons_fetched': False,
                'has_episodes': True  # Par défaut, considérer que l'anime a des épisodes
            }

            # Si demandé ou si c'est un anime populaire, récupérer les saisons et les épisodes
            if fetch_seasons_for_this_anime:
                try:
                    anime_entry = await fetch_anime_seasons(anime, anime_entry)
                    
                    # Pour les animes populaires, vérifier qu'on a suffisamment de saisons
                    if found_popular_anime and anime.name.lower() == found_popular_anime.lower():
                        if len(anime_entry.get('seasons', [])) < 2:
                            logger.warning(f"Nombre insuffisant de saisons pour {anime.name}: {len(anime_entry.get('seasons', []))}")
                            # Ne pas ajouter cet anime si c'est un anime populaire avec trop peu de saisons
                            continue
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération des saisons pour {anime.name}: {e}")

            anime_list.append(anime_entry)

        logger.info(f"Résultats retournés: {len(anime_list)} animes")
        return anime_list

    except Exception as e:
        logger.error(f"Erreur lors de la recherche d'anime: {e}")
        return []

async def fetch_anime_seasons(anime_obj, anime_entry):
    """
    Récupère les saisons, films et épisodes pour un anime.
    Les films sont inclus comme une saison spéciale nommée "Films".

    :param anime_obj: L'objet anime de l'API Anime-Sama
    :param anime_entry: L'entrée anime au format du site
    :return: L'entrée anime mise à jour avec les saisons et épisodes
    """
    try:
        logger.info(f"Récupération des saisons pour: {anime_entry['title']}")
        
        # Initialiser le flag pour indiquer si l'anime a des épisodes

        # Récupérer la description/synopsis
        try:
            synopsis = await anime_obj.synopsis()
            if synopsis:
                anime_entry['description'] = synopsis
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du synopsis: {e}")

        # Récupérer toutes les saisons
        seasons = await anime_obj.seasons()

        if not seasons:
            logger.info(f"Aucune saison trouvée pour: {anime_entry['title']}")
            anime_entry['seasons_fetched'] = True
            return anime_entry

        logger.info(f"Nombre de saisons trouvées: {len(seasons)}")

        # Structure pour organiser les saisons et films
        regular_seasons = []
        films = []

        # Pour chaque saison, récupérer les épisodes
        for i, season in enumerate(seasons):
            try:
                season_name = season.name
                logger.info(f"Traitement de la saison: {season_name}")

                # Déterminer si c'est un film ou une saison régulière
                is_film = False
                if "Film" in season_name or "Movie" in season_name:
                    is_film = True
                    logger.info(f"Film détecté: {season_name}")

                # Récupérer les épisodes de cette saison
                episodes = await season.episodes()

                if not episodes:
                    logger.info(f"Aucun épisode trouvé pour la saison: {season_name}")
                    continue

                logger.info(f"Nombre d'épisodes trouvés: {len(episodes)}")

                # Déterminer le numéro de saison
                season_number = i + 1
                try:
                    # Essayer d'extraire le numéro de saison du nom
                    season_match = re.search(r'Saison\s+(\d+)', season_name, re.IGNORECASE)
                    if season_match:
                        season_number = int(season_match.group(1))
                except Exception:
                    pass

                # Créer la structure de saison
                season_data = {
                    'season_number': 99 if is_film else season_number,  # Films auront le numéro 99
                    'name': "Films" if is_film else season_name,
                    'episodes': []
                }

                # Ajouter les épisodes
                for j, episode in enumerate(episodes):
                    # Langues disponibles (préférer VF si disponible)
                    available_langs = []
                    has_vf = False
                    for lang in episode.languages.availables:
                        if lang in ["VF", "VOSTFR"]:
                            if lang == "VF":
                                has_vf = True
                            available_langs.append(lang)
                            
                    # Si VF est disponible, c'est la seule qu'on affiche pour simplifier
                    if has_vf and "VOSTFR" in available_langs:
                        available_langs = ["VF"]

                    # Créer l'entrée d'épisode
                    episode_data = {
                        'episode_number': j + 1,
                        'title': episode.name,
                        'description': '',
                        'duration': 0,  # Durée inconnue pour l'instant
                        'languages': available_langs,
                        'urls': {}  # Sera rempli plus tard lors de la lecture
                    }

                    season_data['episodes'].append(episode_data)

                # Ajouter la saison à la bonne catégorie
                if is_film:
                    # Pour les films, ajouter chaque épisode comme un film dans la liste films
                    films.extend(season_data['episodes'])
                else:
                    regular_seasons.append(season_data)

            except Exception as e:
                logger.error(f"Erreur lors du traitement de la saison {season.name}: {e}")

        # Créer une entrée pour les films si nécessaire
        if films:
            film_season = {
                'season_number': 99,
                'name': "Films",
                'episodes': films
            }
            regular_seasons.append(film_season)

        # Préparation des saisons pour le tri
        regular_seasons_normal = []
        kai_seasons = []
        film_seasons = []
        
        # Identifier les types de saisons
        for season in regular_seasons:
            season_name = season.get('name', '')
            if season.get('season_number') == 99:
                film_seasons.append(season)
            elif 'Kai' in season_name:
                kai_seasons.append(season)
            else:
                regular_seasons_normal.append(season)
        
        # Tri interne des saisons par numéro
        regular_seasons_normal.sort(key=lambda s: s.get('season_number', 0))
        kai_seasons.sort(key=lambda s: s.get('season_number', 0))
        
        # Reconstituer la liste des saisons dans l'ordre souhaité
        sorted_seasons = regular_seasons_normal + film_seasons + kai_seasons
        
        # Mettre à jour l'entrée anime avec les saisons triées
        anime_entry['seasons'] = sorted_seasons
        anime_entry['seasons_fetched'] = True
        
        # Si nous avons des épisodes dans au moins une saison, marquer comme ayant des épisodes
        has_episodes = False
        for season in sorted_seasons:
            if season.get('episodes', []):
                has_episodes = True
                break
        
        # Définir explicitement si l'anime a des épisodes
        anime_entry['has_episodes'] = has_episodes
        
        return anime_entry

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des saisons pour {anime_entry['title']}: {e}")
        return anime_entry

# Wrapper synchrone pour la fonction de recherche asynchrone
def search_anime(query, limit=20, fetch_seasons=False):
    """
    Wrapper synchrone pour la fonction de recherche asynchrone
    :param query: Texte de recherche
    :param limit: Nombre maximum de résultats à retourner
    :param fetch_seasons: Si True, récupère aussi les saisons et épisodes
    :return: Liste des animes trouvés (limitée à 'limit')
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(search_anime_api(query, limit=limit, fetch_seasons=fetch_seasons))
        loop.close()
        return results
    except Exception as e:
        logger.error(f"Erreur dans le wrapper de recherche: {e}")
        return []

def ensure_anime_id_in_data(data):
    """
    S'assure que tous les animes dans la liste possèdent un champ anime_id.
    Si ce champ est manquant, il est ajouté avec la même valeur que l'id.
    Aussi valide si has_episodes est présent et l'ajoute par défaut à True si absent.
    
    :param data: Liste d'animes à vérifier
    :return: Liste d'animes mise à jour
    """
    for anime in data:
        # Ajouter anime_id s'il est manquant
        if 'anime_id' not in anime and 'id' in anime:
            anime['anime_id'] = anime['id']
            
        # S'assurer que has_episodes existe, par défaut à True si non spécifié
        if 'has_episodes' not in anime:
            seasons = anime.get('seasons', [])
            has_episodes = False
            
            # Vérifier si au moins une saison a des épisodes
            for season in seasons:
                if season.get('episodes', []):
                    has_episodes = True
                    break
                    
            anime['has_episodes'] = has_episodes
    
    return data

def save_anime_data(data):
    try:
        # S'assurer que tous les animes ont un anime_id
        if isinstance(data, list):
            data = ensure_anime_id_in_data(data)
            
        # Définir le chemin absolu pour le stockage
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'static', 'data')
        json_path = os.path.join(data_dir, 'anime.json')

        # Créer le dossier data s'il n'existe pas
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Sauvegarde des données anime vers: {json_path}")

        # Ensure we're saving with the expected structure
        if isinstance(data, list):
            save_data = {'anime': data}
        else:
            # If somehow data is not a list, create a default structure
            logger.warning("Unexpected data format when saving anime data")
            save_data = {'anime': []}

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=4)
        logger.info(f"Données sauvegardées avec succès: {len(save_data['anime'])} animes")
        return True
    except Exception as e:
        logger.error(f"Error saving anime data: {e}")
        return False

# Extract unique genres from anime data
def get_all_genres():
    anime_data = load_anime_data()
    genres = set()
    for anime in anime_data:
        for genre in anime.get('genres', []):
            genres.add(genre.lower())
    return sorted(list(genres))

# Helper function to extract Google Drive ID from URL
def extract_drive_id(url):
    # Looking for patterns like drive.google.com/file/d/ID/view
    drive_patterns = [
        r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
        r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'
    ]

    for pattern in drive_patterns:
        match = re.search(pattern, url)
        if match:
            logger.debug(f"Extracted Google Drive ID: {match.group(1)}")
            return match.group(1)

    # If it's just the ID itself
    if not url.startswith(('http://', 'https://')):
        logger.debug(f"Using provided ID: {url}")
        return url

    # If it contains the ID in the URL but doesn't match the patterns above
    parts = url.split('/')
    for part in parts:
        if len(part) > 20 and re.match(r'^[a-zA-Z0-9_-]+$', part):
            logger.debug(f"Extracted potential Google Drive ID from parts: {part}")
            return part

    logger.warning(f"Could not extract Google Drive ID from URL: {url}")
    return None

@app.route('/')
def index():
    try:
        # Rediriger vers la page de connexion si l'utilisateur n'est pas connecté
        if not current_user.is_authenticated:
            return redirect(url_for('login'))

        anime_data = load_anime_data()

        # S'assurer que les animes populaires sont préchargés
        if not POPULAR_ANIME_IDS:
            preload_popular_animes()
            logger.info("Préchargement forcé des animes populaires depuis route index")

        # Récupérer les animes en cours de visionnage (limité à 20 maximum)
        continue_watching = []
        if current_user.is_authenticated:
            try:
                # Récupérer les progressions non terminées les plus récentes par anime
                latest_progress_by_anime = UserProgress.query.filter_by(
                    user_id=current_user.id
                ).order_by(
                    UserProgress.last_watched.desc()
                ).all()

                # Pour chaque anime, trouver les données et ajouter à la liste (limité à 20)
                processed_animes = set()
                for progress in latest_progress_by_anime:
                    if progress.anime_id not in processed_animes and len(continue_watching) < 20:
                        anime = next((a for a in anime_data if int(a.get('id', 0)) == progress.anime_id), None)
                        if anime:
                            # Trouver la saison et l'épisode correspondants
                            season = next((s for s in anime.get('seasons', []) if s.get('season_number') == progress.season_number), None)
                            if season:
                                episode = next((e for e in season.get('episodes', []) if e.get('episode_number') == progress.episode_number), None)
                                if episode:
                                    continue_watching.append({
                                        'anime': anime,
                                        'progress': progress,
                                        'season': season,
                                        'episode': episode
                                    })
                                    processed_animes.add(progress.anime_id)
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des animes en cours de visionnage: {e}")
                continue_watching = []

        # Récupérer les favoris (limité à 15 maximum)
        favorite_anime = []
        if current_user.is_authenticated:
            try:
                favorites = UserFavorite.query.filter_by(user_id=current_user.id).all()
                for favorite in favorites:
                    if len(favorite_anime) >= 15:
                        break
                    anime = next((a for a in anime_data if a.get('id') == favorite.anime_id), None)
                    if anime:
                        favorite_anime.append(anime)
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des favoris: {e}")
                favorite_anime = []

        # Charger les animes fixes pour "Découvrir de Nouvelles Séries" depuis le fichier data_discover.json
        # Ces animes ne changent jamais et ne sont pas affectés par les recherches
        try:
            featured_anime = load_discover_anime_data()
            
            # S'assurer que Bleach est toujours dans les animes mis en avant
            bleach_in_featured = False
            for anime in featured_anime:
                if anime.get('title', '').lower() == 'bleach':
                    anime['featured'] = True
                    bleach_in_featured = True
                    logger.info("Bleach est bien présent dans les animes en vedette")
            
            # Vérifier si les animes ont les IDs corrects par rapport aux animes préchargés
            updated = False
            for anime in featured_anime:
                title_lower = anime.get('title', '').lower()
                if title_lower in POPULAR_ANIME_IDS:
                    # Mettre à jour les IDs avec ceux des animes préchargés
                    old_id = anime.get('id')
                    old_anime_id = anime.get('anime_id')
                    
                    new_id = POPULAR_ANIME_IDS[title_lower]['id']
                    new_anime_id = POPULAR_ANIME_IDS[title_lower]['anime_id']
                    
                    if old_id != new_id or old_anime_id != new_anime_id:
                        anime['id'] = new_id
                        anime['anime_id'] = new_anime_id
                        updated = True
                        logger.info(f"ID mis à jour pour l'anime {anime['title']}: id={new_id}, anime_id={new_anime_id}")
            
            logger.info(f"Animes de découverte chargés: {len(featured_anime)} trouvés" + 
                      (" (IDs mis à jour)" if updated else ""))
        except Exception as e:
            logger.error(f"Erreur lors du chargement des animes de découverte: {e}")
            # En cas d'erreur, utiliser la liste codée en dur avec les IDs corrects
            featured_anime = []
            
            # Utiliser les animes populaires préchargés
            for title, ids in POPULAR_ANIME_IDS.items():
                # Trouver l'anime correspondant dans la liste complète
                anime = next((a for a in anime_data if a.get('title', '').lower() == title), None)
                if anime:
                    anime_copy = anime.copy()
                    # S'assurer que les IDs sont corrects
                    anime_copy['id'] = ids['id']
                    anime_copy['anime_id'] = ids['anime_id']
                    anime_copy['featured'] = True
                    anime_copy['has_episodes'] = True
                    featured_anime.append(anime_copy)
            
            # Si aucun anime n'a été trouvé, utiliser une liste par défaut
            if not featured_anime:
                featured_anime = [
                {
                    'id': POPULAR_ANIME_IDS.get('one piece', {}).get('id', 1), 
                    'anime_id': POPULAR_ANIME_IDS.get('one piece', {}).get('anime_id', 1),
                    'title': 'One Piece', 
                    'description': 'Monkey D. Luffy se lance à la poursuite du trésor One Piece et de son rêve de devenir le Roi des Pirates.',
                    'image': 'https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/one-piece.jpg',
                    'genres': ['Action', 'Aventure', 'Pirates'],
                    'rating': 9.5,
                    'featured': True,
                    'has_episodes': True,
                },
            {
                'id': 2, 
                'anime_id': 2,
                'title': 'Death Note', 
                'description': 'Light Yagami trouve un carnet mystérieux qui lui permet de tuer n\'importe qui en écrivant leur nom.',
                'image': 'https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/death-note.jpg',
                'genres': ['Thriller', 'Psychologique', 'Surnaturel'],
                'rating': 9.4,
                'featured': True,
                'has_episodes': True,
            },
            {
                'id': 3, 
                'anime_id': 3,
                'title': 'Demon Slayer', 
                'description': 'Tanjiro Kamado devient un chasseur de démons après que sa famille est massacrée et sa sœur transformée en démon.',
                'image': 'https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/demon-slayer.jpg',
                'genres': ['Action', 'Démons', 'Historique'],
                'rating': 9.0,
                'featured': True,
                'has_episodes': True,
            },
            {
                'id': 4, 
                'anime_id': 4,
                'title': 'One Punch Man', 
                'description': 'Saitama, un super-héros capable de vaincre n\'importe quel ennemi d\'un seul coup de poing, s\'ennuie de sa toute-puissance.',
                'image': 'https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/one-punch-man.jpg',
                'genres': ['Action', 'Comédie', 'Super-héros'],
                'rating': 8.8,
                'featured': True,
                'has_episodes': True,
            },
            {
                'id': 5, 
                'anime_id': 5,
                'title': 'Mashle', 
                'description': 'Dans un monde où la magie fait loi, un jeune garçon nommé Mash Burnedead, dépourvu de toute aptitude pour la magie, vit paisiblement avec son grand-père adoptif.',
                'image': 'https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/mashle.jpg',
                'genres': ['Action', 'Comédie', 'Fantasy'],
                'rating': 8.2,
                'featured': True,
                'has_episodes': True,
            },
            {
                'id': 6, 
                'anime_id': 6,
                'title': 'My Hero Academia', 
                'description': 'Dans un monde où 80% de la population possède des super-pouvoirs, Izuku Midoriya rêve de devenir un héros malgré le fait qu\'il n\'a pas de pouvoir.',
                'image': 'https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/my-hero-academia.jpg',
                'genres': ['Action', 'Super-héros', 'Ecole'],
                'rating': 8.7,
                'featured': True,
                'has_episodes': True,
            },
            {
                'id': 7, 
                'anime_id': 7,
                'title': 'Hunter x Hunter', 
                'description': 'Gon Freecss part à la recherche de son père qui est un Hunter d\'élite.',
                'image': 'https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/hunter-x-hunter.jpg',
                'genres': ['Action', 'Aventure', 'Shônen'],
                'rating': 9.3,
                'featured': True,
                'has_episodes': True,
            },
            {
                'id': 8, 
                'anime_id': 8,
                'title': 'Naruto', 
                'description': 'Dans le village caché de Konoha vit Naruto, un jeune garçon qui rêve de devenir Hokage, le chef du village.',
                'image': 'https://cdn.statically.io/gh/Anime-Sama/IMG/img/contenu/naruto.jpg',
                'genres': ['Action', 'Aventure', 'Shônen'],
                'rating': 8.3,
                'featured': True,
                'has_episodes': True,
            }
        ]

        # Maximum 12 animes dans cette section
        # Filtrer pour ne garder que les animes qui ont des épisodes
        featured_anime_with_episodes = [anime for anime in featured_anime if anime.get('has_episodes', False)]
        featured_anime_with_episodes = featured_anime_with_episodes[:12]

        return render_template('index_new.html', 
                        anime_list=featured_anime_with_episodes,
                        continue_watching=continue_watching,
                        favorite_anime=favorite_anime)

    except Exception as e:
        logger.error(f"Erreur dans la page d'accueil: {e}")
        # En cas d'erreur, afficher une page d'accueil avec un minimum de contenu
        return render_template('index_new.html', 
                        anime_list=[],
                        continue_watching=[],
                        favorite_anime=[],
                        error_message="Une erreur s'est produite lors du chargement de la page d'accueil.")

@app.route('/search')
@login_required
def search():
    try:
        query = request.args.get('query', '').lower()
        genre = request.args.get('genre', '').lower()

        # Si la requête est vide ou trop courte, renvoyer directement les résultats locaux (20 derniers)
        if not query or len(query) < 3:
            logger.info("Requête vide ou trop courte, utilisation des données locales uniquement")
            # Charger les données et prendre les 20 derniers animes ajoutés qui ont des épisodes
            local_data = load_anime_data()
            # Filtrer pour ne garder que les animes avec des épisodes
            filtered_data = [anime for anime in local_data if anime.get('has_episodes', False)]
            recent_animes = filtered_data[-20:] if len(filtered_data) > 0 else []

            return render_template('search.html', 
                                anime_list=[], 
                                query=query, 
                                selected_genre=genre, 
                                genres=get_all_genres(),
                                api_error="Veuillez entrer au moins 3 caractères pour rechercher",
                                other_anime_list=recent_animes)

        # Définir une limite de temps pour la recherche API
        api_timeout = 8  # Réduit pour éviter les timeouts

        # Nombre maximum de résultats (sans limite)
        MAX_RESULTS = 100  # Augmenté comme demandé

        # Cas spécial pour les requêtes problématiques connues
        problematic_queries = ["1", "2", "3", "a", "e", "o", "100"]
        if query in problematic_queries:
            logger.warning(f"Requête problématique détectée: {query}")
            return render_template('search.html', 
                                anime_list=[], 
                                query=query, 
                                selected_genre=genre, 
                                genres=get_all_genres(),
                                api_error="Cette requête est trop générique et peut causer des problèmes. Veuillez préciser votre recherche.")

        # Obtenir d'abord les résultats de la base locale
        local_data = load_anime_data()
        filtered_local = []

        # Cas spécial : si la recherche contient "one piece", forcer l'utilisation de notre entrée One Piece
        if query and "one piece" in query.lower():
            # Rechercher One Piece dans notre base de données locale
            one_piece = next((a for a in local_data if "one piece" in a.get('title', '').lower()), None)
            if one_piece:
                logger.info(f"Utilisation de l'entrée One Piece locale: {one_piece.get('title')}")
                return render_template('search.html',
                                    anime_list=[one_piece],
                                    query=query,
                                    selected_genre=genre,
                                    genres=get_all_genres())

        # Filtrer les données locales
        for anime in local_data:
            title_match = query in anime.get('title', '').lower()
            genre_match = not genre or genre in [g.lower() for g in anime.get('genres', [])]
            has_episodes = anime.get('has_episodes', False)

            if (not query or title_match) and genre_match and has_episodes:
                filtered_local.append(anime)

        # Limiter le nombre de résultats locaux pour des raisons de performance
        filtered_local = filtered_local[:MAX_RESULTS]

        # Si nous avons assez de résultats locaux, ne pas utiliser l'API
        if len(filtered_local) >= MAX_RESULTS//2:  # Si on a au moins la moitié des résultats max
            logger.info(f"Utilisation des résultats locaux uniquement (suffisant): {len(filtered_local)}")
            return render_template('search.html',
                                anime_list=filtered_local,
                                query=query,
                                selected_genre=genre,
                                genres=get_all_genres())

        # Préparer la liste des résultats
        merged_results = []
        local_titles = [anime.get('title', '').lower() for anime in filtered_local]

        # D'abord ajouter les résultats locaux
        merged_results.extend(filtered_local)

        # Si une requête est spécifiée et que l'API est disponible, chercher via l'API
        # pour compléter jusqu'à MAX_RESULTS
        api_results = []
        api_error = None
        remaining_slots = min(20, MAX_RESULTS - len(merged_results))  # Limité à 20 résultats API maximum

        if query and API_IMPORT_SUCCESS and remaining_slots > 0:
            try:
                logger.info(f"Recherche via API pour: {query} (limite: {remaining_slots} résultats)")

                # Utiliser asyncio avec timeout pour éviter que l'API ne bloque trop longtemps
                async def search_with_timeout():
                    try:
                        return await asyncio.wait_for(search_anime_api(query, limit=remaining_slots), timeout=api_timeout)
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout lors de la recherche API pour: {query}")
                        return []

                # Exécuter la recherche avec timeout
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                api_results = loop.run_until_complete(search_with_timeout())
                loop.close()

                # Si des résultats sont trouvés, filtrer par genre si nécessaire
                if api_results and genre:
                    api_results = [anime for anime in api_results 
                                if any(g.lower() == genre for g in anime.get('genres', []))]

                # Limiter les résultats API
                api_results = api_results[:remaining_slots]

                # Puis ajouter les résultats de l'API qui ne sont pas déjà dans les résultats locaux
                for anime in api_results:
                    # Vérifier que l'image existe et est accessible
                    if not anime.get('image_url') or not anime['image_url'].startswith(('http://', 'https://')):
                        # Utiliser une image par défaut
                        anime['image'] = '/static/images/default_anime.jpg'
                    else:
                        # Utiliser l'URL de l'image de l'API
                        anime['image'] = anime['image_url']

                    # Vérifier si l'anime a des épisodes avant de l'ajouter
                    # On ne peut pas savoir sans les récupérer, donc on considère qu'un anime sans propriété 'seasons' n'a pas d'épisodes
                    has_episodes = anime.get('seasons') is not None and len(anime.get('seasons', [])) > 0
                    anime['has_episodes'] = has_episodes
                    
                    # Vérifier que l'anime a un anime_id
                    if 'anime_id' not in anime or not anime['anime_id']:
                        anime['anime_id'] = anime.get('id', 0)
                    
                    # Ne montrer que les animes avec des épisodes dans les résultats
                    if anime.get('title', '').lower() not in local_titles and has_episodes:
                        merged_results.append(anime)
                        local_titles.append(anime.get('title', '').lower())

                        # Sauvegarder les résultats de recherche dans le fichier local 
                        # Ajouter les nouveaux résultats et conserver jusqu'à 20 animes au total
                        existing_titles = [a.get('title', '').lower() for a in local_data]
                        if anime.get('title', '').lower() not in existing_titles:
                            # Ajouter le nouvel anime à la liste
                            local_data.append(anime)
                            # Si on dépasse 20 animes, supprimer les plus anciens
                            if len(local_data) > 20:  # Limiter à 20 animes maximum au lieu de 15
                                # Supprimer les plus anciens pour revenir à 20
                                local_data = local_data[-20:]
                            # Sauvegarder les changements dans le fichier local
                            save_anime_data(local_data)

                        # Arrêter si on atteint MAX_RESULTS
                        if len(merged_results) >= MAX_RESULTS:
                            break

            except Exception as e:
                logger.error(f"Erreur lors de la recherche API: {e}")
                api_error = "Erreur lors de la recherche. Veuillez réessayer avec des termes différents."

        logger.info(f"Résultats de recherche: {len(merged_results)} animes trouvés")

        # Si aucun résultat n'est trouvé, fournir les 20 derniers animes recherchés (qui ont des épisodes)
        other_anime_list = load_anime_data()
        # Filtrer pour ne garder que les animes avec des épisodes
        other_anime_list = [anime for anime in other_anime_list if anime.get('has_episodes', False)]
        # Limiter à 20 derniers animes
        other_anime_list = other_anime_list[-20:] if len(other_anime_list) > 0 else []
        # Si nous avons des résultats, nous n'affichons pas les dernières recherches
        if merged_results:
            other_anime_list = []

        return render_template('search.html', 
                            anime_list=merged_results, 
                            query=query, 
                            selected_genre=genre, 
                            genres=get_all_genres(),
                            api_error=api_error,
                            other_anime_list=other_anime_list)

    except Exception as e:
        # En cas d'erreur, retourner une page d'erreur claire
        logger.error(f"Erreur critique lors de la recherche: {e}")
        # Charger les 20 derniers animes recherchés même en cas d'erreur (qui ont des épisodes)
        other_anime_list = load_anime_data()
        # Filtrer pour ne garder que les animes avec des épisodes
        other_anime_list = [anime for anime in other_anime_list if anime.get('has_episodes', False)]
        other_anime_list = other_anime_list[-20:] if len(other_anime_list) > 0 else []

        return render_template('search.html', 
                              anime_list=[], 
                              query=query if 'query' in locals() else '', 
                              selected_genre=genre if 'genre' in locals() else '', 
                              genres=get_all_genres(),
                              api_error=f"Une erreur s'est produite. Veuillez réessayer plus tard.",
                              other_anime_list=other_anime_list)

@app.route('/anime/<int:anime_id>')
@login_required
def anime_detail(anime_id):
    try:
        # S'assurer que les animes populaires sont préchargés
        if not POPULAR_ANIME_IDS:
            preload_popular_animes()
            logger.info("Préchargement forcé des animes populaires depuis anime_detail")
            
        anime_data = load_anime_data()

        # Protection des IDs invalides
        if anime_id <= 0:
            logger.warning(f"Tentative d'accès à un anime avec ID invalide: {anime_id}")
            return render_template('404.html', message="ID d'anime invalide"), 404
            
        # Rechercher d'abord dans les animes populaires préchargés
        anime = None
        
        # Parcourir les animes populaires pour trouver celui avec l'ID correspondant
        for title, ids in POPULAR_ANIME_IDS.items():
            if ids.get('id') == anime_id or ids.get('anime_id') == anime_id:
                # Trouver l'anime dans la liste complète
                anime = next((a for a in anime_data if a.get('title', '').lower() == title), None)
                if anime:
                    logger.info(f"Anime trouvé dans les populaires: {title} (ID: {ids})")
                    break
        
        # Si non trouvé dans les populaires, rechercher dans tous les animes
        if not anime:
            # Find the anime by ID (anime_id est un int, assurons-nous de comparer avec des int)
            # Recherche par anime_id d'abord, puis par id s'il n'est pas trouvé
            anime = next((a for a in anime_data if int(a.get('anime_id', 0)) == anime_id), None)
            
            # Fallback sur le champ id si anime_id n'existe pas ou ne correspond pas
            if not anime:
                anime = next((a for a in anime_data if int(a.get('id', 0)) == anime_id), None)

        if not anime:
            logger.warning(f"Anime avec ID {anime_id} non trouvé")
            return render_template('404.html', message="Anime non trouvé"), 404
            
        # Si c'est One Piece ou un autre anime avec beaucoup de saisons, trions-les correctement
        if anime.get('seasons'):
            # Trier les saisons:
            # 1. Saisons normales (non-Kai) d'abord, par numéro
            # 2. Films (season_number = 99)
            # 3. Versions Kai, par numéro
            
            # On identifie d'abord les types de saisons
            regular_seasons = []
            kai_seasons = []
            film_seasons = []
            
            for season in anime.get('seasons', []):
                season_name = season.get('name', '')
                if season.get('season_number') == 99:
                    film_seasons.append(season)
                elif 'Kai' in season_name:
                    kai_seasons.append(season)
                else:
                    regular_seasons.append(season)
            
            # Tri interne des saisons par numéro
            regular_seasons.sort(key=lambda s: s.get('season_number', 0))
            kai_seasons.sort(key=lambda s: s.get('season_number', 0))
            
            # Reconstituer la liste complète des saisons dans l'ordre souhaité
            anime['seasons'] = regular_seasons + film_seasons + kai_seasons

        # Vérifier si les saisons et épisodes ont déjà été récupérés pour cet anime
        # Si non, essayer de les récupérer maintenant
        if not anime.get('seasons_fetched', False) and API_IMPORT_SUCCESS:
            try:
                logger.info(f"Récupération des saisons pour l'anime {anime['title']} lors de la consultation")
                # Rechercher l'anime pour avoir l'objet API
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                api = AnimeSama(ANIME_SAMA_BASE_URL)
                search_results = loop.run_until_complete(api.search(anime['title']))

                # Trouver l'anime correspondant dans les résultats
                api_anime = None
                for result in search_results:
                    if result.name.lower() == anime['title'].lower():
                        api_anime = result
                        break

                if api_anime:
                    # Récupérer les saisons et épisodes
                    updated_anime = loop.run_until_complete(fetch_anime_seasons(api_anime, anime))

                    # Mettre à jour l'anime dans la liste
                    for i, a in enumerate(anime_data):
                        if int(a.get('id', 0)) == anime_id:
                            anime_data[i] = updated_anime
                            anime = updated_anime
                            break

                    # Sauvegarder les modifications
                    save_anime_data(anime_data)
                    logger.info(f"Saisons et épisodes récupérés avec succès pour {anime['title']}")
                else:
                    logger.warning(f"Impossible de trouver l'anime {anime['title']} dans l'API")

                loop.close()
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des saisons pour {anime['title']}: {e}")

        # Vérifier si l'anime est dans les favoris de l'utilisateur
        is_favorite = False
        episode_progress = {}
        latest_progress = None

        if current_user.is_authenticated:
            try:
                # Vérifier le statut favori
                favorite = UserFavorite.query.filter_by(
                    user_id=current_user.id,
                    anime_id=anime_id
                ).first()
                is_favorite = favorite is not None

                # Récupérer la progression pour tous les épisodes de cet anime
                progress_data = UserProgress.query.filter_by(
                    user_id=current_user.id,
                    anime_id=anime_id
                ).all()

                # Créer un dictionnaire de progression pour un accès facile dans le template
                for progress in progress_data:
                    key = f"{progress.season_number}_{progress.episode_number}"
                    episode_progress[key] = {
                        'time_position': progress.time_position,
                        'completed': progress.completed,
                        'last_watched': progress.last_watched
                    }

                # Trouver le dernier épisode regardé pour cet anime
                latest_progress = UserProgress.query.filter_by(
                    user_id=current_user.id,
                    anime_id=anime_id,
                    completed=False
                ).order_by(
                    UserProgress.last_watched.desc()
                ).first()
            except Exception as e:
                # En cas d'erreur avec la progression, on continue quand même
                logger.error(f"Erreur lors de la récupération de la progression: {e}")
                episode_progress = {}
                latest_progress = None

        # Vérifiez que les saisons sont complètes
        if not anime.get('seasons'):
            anime['seasons'] = [{
                'season_number': 1,
                'name': "Saison 1",
                'episodes': []
            }]

        return render_template('anime_new.html', 
                              anime=anime, 
                              is_favorite=is_favorite,
                              episode_progress=episode_progress,
                              latest_progress=latest_progress)

    except Exception as e:
        logger.error(f"Erreur lors de l'affichage de l'anime {anime_id}: {e}")
        return render_template('404.html', message="Une erreur s'est produite lors du chargement de l'anime"), 500

@app.route('/player/<int:anime_id>/<int:season_num>/<int:episode_num>')
@login_required
def player(anime_id, season_num, episode_num):
    try:
        # Récupérer éventuellement une source spécifique depuis l'URL
        source_url = request.args.get('source', None)

        # Protection des paramètres invalides
        if anime_id <= 0 or season_num <= 0 or episode_num <= 0:
            logger.warning(f"Tentative d'accès au player avec des paramètres invalides: anime={anime_id}, saison={season_num}, episode={episode_num}")
            return render_template('404.html', message="Paramètres de lecteur invalides"), 404

        # S'assurer que les animes populaires sont préchargés
        if not POPULAR_ANIME_IDS:
            preload_popular_animes()
            logger.info("Préchargement forcé des animes populaires depuis player")
            
        anime_data = load_anime_data()

        # Rechercher d'abord dans les animes populaires préchargés
        anime = None
        
        # Parcourir les animes populaires pour trouver celui avec l'ID correspondant
        for title, ids in POPULAR_ANIME_IDS.items():
            if ids.get('id') == anime_id or ids.get('anime_id') == anime_id:
                # Trouver l'anime dans la liste complète
                anime = next((a for a in anime_data if a.get('title', '').lower() == title), None)
                if anime:
                    logger.info(f"Anime trouvé dans les populaires pour le player: {title} (ID: {ids})")
                    break
        
        # Si non trouvé dans les populaires, rechercher dans tous les animes
        if not anime:
            # Find the anime by ID (même logique de conversion que anime_detail)
            # Recherche par anime_id d'abord, puis par id s'il n'est pas trouvé
            anime = next((a for a in anime_data if int(a.get('anime_id', 0)) == anime_id), None)
            
            # Fallback sur le champ id si anime_id n'existe pas ou ne correspond pas
            if not anime:
                anime = next((a for a in anime_data if int(a.get('id', 0)) == anime_id), None)

        if not anime:
            logger.error(f"Anime with ID {anime_id} not found")
            return render_template('404.html', message="Anime non trouvé"), 404

        # Find the season
        season = next((s for s in anime.get('seasons', []) if s.get('season_number') == season_num), None)

        if not season:
            logger.error(f"Season {season_num} not found for anime {anime_id}")
            return render_template('404.html', message=f"Saison {season_num} non trouvée"), 404

        # Find the episode
        episode = next((e for e in season.get('episodes', []) if e.get('episode_number') == episode_num), None)

        if not episode:
            logger.error(f"Episode {episode_num} not found for anime {anime_id}, season {season_num}")
            return render_template('404.html', message=f"Épisode {episode_num} non trouvé"), 404

        # Generate download URL for Google Drive (avec vérification)
        # Forcer la récupération des URLs de vidéo à chaque fois pour avoir les sources les plus récentes
        video_urls = episode.get('urls', {})
        # Forcer un rafraîchissement périodique des sources
        force_refresh = False
        if video_urls:
            # Forcer rafraîchissement toutes les 24h pour garder les sources à jour
            import time  # Ajout de l'import ici pour s'assurer qu'il est disponible
            last_refresh = episode.get('last_refreshed', 0)
            current_time = int(time.time())
            if current_time - last_refresh > 86400:  # 24 heures
                force_refresh = True
                logger.info(f"Rafraîchissement des sources pour {anime['title']} S{season_num}E{episode_num} (dernière mise à jour il y a plus de 24h)")

        # Si on n'a pas d'URLs ou on a besoin de rafraîchir les sources
        if (not video_urls or force_refresh) and API_IMPORT_SUCCESS:
            try:
                logger.info(f"Récupération des URLs vidéo pour l'anime {anime['title']}, saison {season_num}, épisode {episode_num}")

                # Rechercher l'anime pour avoir l'objet API
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                api = AnimeSama(ANIME_SAMA_BASE_URL)
                
                # Amélioré: Essayer plusieurs variantes du titre pour les animes sensibles
                title_variations = [
                    anime['title'],
                    anime.get('original_title', anime['title']),
                    # Cas spécifiques connus
                    "solo leveling" if anime['title'].lower() == "solo leveling" else None
                ]
                
                # Filtrer les variantes None
                title_variations = [t for t in title_variations if t]
                
                # Journaliser les tentatives
                logger.info(f"Tentatives de recherche pour l'anime: {title_variations}")
                
                api_anime = None
                for title in title_variations:
                    search_results = loop.run_until_complete(api.search(title))
                    logger.info(f"Recherche de '{title}' via API: {len(search_results)} résultats trouvés")
                    
                    # Recherche exacte
                    for result in search_results:
                        if result.name.lower() == title.lower():
                            api_anime = result
                            logger.info(f"Correspondance exacte trouvée pour '{title}': {result.name}")
                            break
                    
                    # Si toujours pas trouvé, essayer une correspondance partielle
                    if not api_anime and search_results:
                        # Prendre le premier résultat comme approximation
                        api_anime = search_results[0]
                        logger.info(f"Correspondance partielle utilisée pour '{title}': {api_anime.name}")
                    
                    if api_anime:
                        break

                if api_anime:
                    # Récupérer les saisons
                    seasons = loop.run_until_complete(api_anime.seasons())

                    # Trouver la saison correspondante (en gérant le cas spécial des films avec numéro 99)
                    target_season = None
                    if season_num == 99:  # Cas spécial pour les films
                        for s in seasons:
                            if "Film" in s.name or "Movie" in s.name:
                                target_season = s
                                break
                    else:
                        # Trouver la saison normale par numéro
                        for s in seasons:
                            try:
                                season_match = re.search(r'Saison\s+(\d+)', s.name, re.IGNORECASE)
                                if season_match and int(season_match.group(1)) == season_num:
                                    target_season = s
                                    break
                            except Exception:
                                continue

                    if target_season:
                        # Récupérer les épisodes de cette saison
                        eps = loop.run_until_complete(target_season.episodes())

                        # Trouver l'épisode correspondant
                        if 0 <= episode_num - 1 < len(eps):
                            ep = eps[episode_num - 1]

                            # Récupérer TOUTES les URLs des players disponibles
                            video_urls = {}
                            # List des langues dans l'ordre de priorité
                            langs = ["VF", "VOSTFR"]

                            # Pour chaque langue, récupérer tous les lecteurs disponibles
                            for lang in langs:
                                try:
                                    lang_urls = []

                                    # Récupérer tous les lecteurs pour cette langue
                                    if lang in ep.languages.availables():
                                        players = ep.languages[lang]
                                        if players:
                                            # Trier les players par ordre de préférence
                                            # 1. SendVid
                                            # 2. OneUpload
                                            # 3. MixDrop 
                                            # 4. DoodStream
                                            # 5. Autres non-Vidmoly
                                            # 6. Vidmoly en dernier recours

                                            # Classifier les players
                                            vidmoly_urls = [url for url in players if "vidmoly.to" in url]
                                            sendvid_urls = [url for url in players if "sendvid.com" in url]
                                            oneupload_urls = [url for url in players if "oneupload.to" in url]
                                            mixdrop_urls = [url for url in players if "mixdrop.co" in url]
                                            dood_urls = [url for url in players if "dood" in url]
                                            other_urls = [url for url in players if "vidmoly.to" not in url and 
                                                         "sendvid.com" not in url and 
                                                         "oneupload.to" not in url and 
                                                         "mixdrop.co" not in url and 
                                                         "dood" not in url]

                                            # Ajouter les URLs dans l'ordre de préférence (Vidmoly en premier)
                                            if vidmoly_urls:
                                                lang_urls.extend(vidmoly_urls)
                                            if sendvid_urls:
                                                lang_urls.extend(sendvid_urls)
                                            if oneupload_urls:
                                                lang_urls.extend(oneupload_urls)
                                            if mixdrop_urls:
                                                lang_urls.extend(mixdrop_urls)
                                            if dood_urls:
                                                lang_urls.extend(dood_urls)
                                            if other_urls:
                                                lang_urls.extend(other_urls)

                                    # S'il y a des URLs pour cette langue, stocker la meilleure
                                    if lang_urls:
                                        video_urls[lang] = lang_urls[0]  # Prendre la meilleure URL (première de la liste triée)
                                        # Enregistrer toutes les URLs alternatives aussi
                                        if not 'all_sources' in episode:
                                            episode['all_sources'] = {}
                                        episode['all_sources'][lang] = lang_urls
                                except Exception as e:
                                    logger.error(f"Erreur lors de la récupération des sources pour {lang}: {e}")

                            # Si aucune URL trouvée, utiliser la méthode simple (fallback)
                            if not video_urls:
                                for lang in langs:
                                    player_url = ep.best([lang])
                                    if player_url:
                                        video_urls[lang] = player_url

                            # Mettre à jour l'épisode avec les URLs
                            if video_urls:
                                episode['urls'] = video_urls

                                # Mettre à jour l'anime dans la liste et sauvegarder
                                for i, a in enumerate(anime_data):
                                    if int(a.get('id', 0)) == anime_id:
                                        anime_data[i] = anime
                                        break

                                save_anime_data(anime_data)
                                logger.info(f"URLs vidéo récupérées avec succès pour {anime['title']}")
                        else:
                            logger.warning(f"Épisode {episode_num} non trouvé dans la saison {target_season.name}")
                    else:
                        logger.warning(f"Saison {season_num} non trouvée pour l'anime {anime['title']}")
                else:
                    logger.warning(f"Anime {anime['title']} non trouvé dans l'API")

                loop.close()
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des URLs vidéo: {e}")

        # Préparer les URLs pour le template
        # Priorité aux lecteurs autres que Vidmoly
        # Puis choisir entre VF et VOSTFR
        video_url = ""
        vidmoly_url = ""  # Pour stocker l'URL Vidmoly comme fallback
        episode_lang = "?"  # Variable pour stocker la langue sélectionnée

        if video_urls and isinstance(video_urls, dict):
            # Récupérer toutes les URLs disponibles et les trier par langue et qualité
            vf_urls = []
            vostfr_urls = []

            # Récupérer toutes les sources alternatives si disponibles
            if episode.get('all_sources'):
                if 'VF' in episode['all_sources']:
                    vf_urls.extend(episode['all_sources']['VF'])
                if 'VOSTFR' in episode['all_sources']:
                    vostfr_urls.extend(episode['all_sources']['VOSTFR'])

            # Ajouter aussi les URLs principales
            if 'VF' in video_urls:
                if video_urls['VF'] not in vf_urls:
                    vf_urls.append(video_urls['VF'])
            if 'VOSTFR' in video_urls:
                if video_urls['VOSTFR'] not in vostfr_urls:
                    vostfr_urls.append(video_urls['VOSTFR'])

            # Filtrer les URLs par source (Vidmoly en premier maintenant)
            vf_vidmoly = [url for url in vf_urls if "vidmoly.to" in url]
            vf_non_vidmoly = [url for url in vf_urls if "vidmoly.to" not in url]
            vostfr_vidmoly = [url for url in vostfr_urls if "vidmoly.to" in url]
            vostfr_non_vidmoly = [url for url in vostfr_urls if "vidmoly.to" not in url]

            # Sélectionner la meilleure URL disponible (priorité Vidmoly et VF)
            video_url = ""
            if vf_vidmoly:
                video_url = vf_vidmoly[0]
                episode_lang = "VF"
            elif vf_non_vidmoly:
                video_url = vf_non_vidmoly[0]
                episode_lang = "VF"
            elif vostfr_vidmoly:
                video_url = vostfr_vidmoly[0]
                episode_lang = "VOSTFR"
            elif vostfr_non_vidmoly:
                video_url = vostfr_non_vidmoly[0]
                episode_lang = "VOSTFR"


        # Si une langue spécifique a été demandée via le paramètre d'URL
        preferred_lang = request.args.get('lang')
        if preferred_lang in ['VF', 'VOSTFR']:
            # Vérifier si cette langue est disponible
            if episode.get('all_sources') and preferred_lang in episode.get('all_sources'):
                # Utiliser la première source disponible pour cette langue
                if episode['all_sources'][preferred_lang]:
                    video_url = episode['all_sources'][preferred_lang][0]
                    episode_lang = preferred_lang
                    logger.info(f"Utilisation de la langue demandée: {preferred_lang}")
        
        # Si une source spécifique a été demandée via le paramètre d'URL
        if source_url:
            video_url = source_url
            # Détecter la langue utilisée
            if episode.get('all_sources'):
                for lang, urls in episode.get('all_sources', {}).items():
                    if source_url in urls:
                        episode_lang = lang
                        break
            logger.info(f"Utilisation d'une source spécifique: {video_url} (langue: {episode_lang})")

        # Si pas d'URL trouvée via API, essayer l'ancienne méthode
        if not video_url:
            video_url = episode.get('video_url', '')
            logger.info(f"Utilisation de l'URL de secours pour l'épisode: {video_url}")

        # Si toujours rien, on renvoie une erreur
        if not video_url:
            logger.warning(f"URL de vidéo non trouvée pour anime {anime_id}, saison {season_num}, épisode {episode_num}")
            return render_template('404.html', message="Source vidéo non disponible - Nous ajouterons bientôt ce contenu."), 404

        # Mettre à jour les langues disponibles dans l'épisode
        if episode_lang != "?" and episode_lang not in episode.get('languages', []):
            if not episode.get('languages'):
                episode['languages'] = []
            episode['languages'].append(episode_lang)

            # Mettre à jour dans la base de données
            for i, a in enumerate(anime_data):
                if int(a.get('id', 0)) == anime_id:
                    anime_data[i] = anime
                    break
            save_anime_data(anime_data)

        # Préparer l'URL de téléchargement/lecture selon la source
        download_url = "#"

        # Liste des lecteurs par ordre de préférence (Vidmoly prioritaire)
        # 1. Vidmoly
        # 2. SendVid
        # 3. OneUpload
        # 4. MixDrop
        # 5. DoodStream
        # 6. Google Drive
        # 7. Autres

        if "sendvid.com" in video_url:
            # Pour SendVid, on utilise le format embed
            if "/embed/" not in video_url:
                video_id = video_url.split("/")[-1].split(".")[0]
                download_url = f"https://sendvid.com/embed/{video_id}"
            else:
                download_url = video_url

        elif "oneupload.to" in video_url:
            # Pour OneUpload, on s'assure d'avoir le format embed
            if "/embed-" not in video_url:
                video_id = video_url.split("/")[-1].split(".")[0]
                download_url = f"https://oneupload.to/embed-{video_id}.html"
            else:
                download_url = video_url

        elif "mixdrop.co" in video_url:
            # Pour MixDrop, on s'assure d'avoir le format embed
            if "/e/" not in video_url:
                video_id = video_url.split("/")[-1]
                download_url = f"https://mixdrop.co/e/{video_id}"
            else:
                download_url = video_url

        elif "dood" in video_url:  # doodstream, dood.to, etc.
            # Pour DoodStream, on s'assure d'avoir le format embed
            if "/e/" not in video_url:
                parts = video_url.split("/")
                video_id = parts[-1]
                domain = ".".join(parts[2].split(".")[-2:])
                download_url = f"https://dood.{domain}/e/{video_id}"
            else:
                download_url = video_url

        elif "drive.google.com" in video_url:
            # Pour Google Drive, on extrait l'ID et on construit l'URL embed
            file_id = extract_drive_id(video_url)
            if file_id:
                download_url = f"https://drive.google.com/file/d/{file_id}/preview"

        elif "vidmoly.to" in video_url:
            # Pour Vidmoly, on utilise l'URL directe sans modification
            logger.warning(f"Vidmoly détecté, utilisation directe: {video_url}")
            download_url = video_url

        else:
            # Pour les autres sources, on utilise l'URL directement
            download_url = video_url

        # Si l'URL est toujours invalide, on renvoie une erreur
        if not download_url or download_url == "#":
            logger.warning(f"URL de vidéo invalide pour anime {anime_id}, saison {season_num}, épisode {episode_num}: {video_url}")
            return render_template('404.html', message="Source vidéo non disponible - Nous ajouterons bientôt ce contenu."), 404

        logger.debug(f"Generated download URL: {download_url}")

        # Si l'utilisateur est connecté, récupérer sa progression et statut favori
        time_position = 0
        is_favorite = False

        if current_user.is_authenticated:
            try:
                # Récupérer la progression
                progress = UserProgress.query.filter_by(
                    user_id=current_user.id,
                    anime_id=anime_id,
                    season_number=season_num,
                    episode_number=episode_num
                ).first()

                if progress:
                    time_position = progress.time_position

                # Vérifier si l'anime est dans les favoris
                favorite = UserFavorite.query.filter_by(
                    user_id=current_user.id,
                    anime_id=anime_id
                ).first()

                is_favorite = favorite is not None
            except Exception as e:
                # En cas d'erreur avec la progression, continuer quand même
                logger.error(f"Erreur lors de la récupération de la progression: {e}")
                time_position = 0
                is_favorite = False

        return render_template('player.html', 
                            anime=anime, 
                            season=season, 
                            episode=episode, 
                            download_url=download_url,
                            time_position=time_position,
                            is_favorite=is_favorite,
                            episode_lang=episode_lang)

    except Exception as e:
        logger.error(f"Erreur lors du chargement du lecteur pour anime {anime_id}, saison {season_num}, épisode {episode_num}: {e}")
        return render_template('404.html', message="Une erreur s'est produite lors du chargement du lecteur"), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.args.get('password', '')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin1234')  # Fallback to default for development

        if password == admin_password:
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error="Invalid password")

    return render_template('admin_login.html')

@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    return render_template('admin.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin/add_anime', methods=['POST'])
def add_anime():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    # Get form data
    title = request.form.get('title')
    description = request.form.get('description')
    image = request.form.get('image')
    genres = [g.strip().lower() for g in request.form.get('genres', '').split(',')]
    rating = float(request.form.get('rating', 0))
    featured = request.form.get('featured') == 'yes'
    episode_count = int(request.form.get('episode_count', 1))

    # Load existing anime data
    anime_data = load_anime_data()

    # Generate a new ID (max + 1)
    new_id = 1
    if anime_data:
        new_id = max(a.get('id', 0) for a in anime_data) + 1

    # Create episodes list
    episodes = []
    for i in range(1, episode_count + 1):
        episodes.append({
            'episode_number': i,
            'title': request.form.get(f'episode_title_{i}'),
            'description': request.form.get(f'episode_description_{i}'),
            'video_url': request.form.get(f'episode_video_{i}')
        })

    # Create the new anime object
    new_anime = {
        'id': new_id,
        'title': title,
        'description': description,
        'image': image,
        'genres': genres,
        'rating': rating,
        'featured': featured,
        'seasons': [
            {
                'season_number': 1,
                'episodes': episodes
            }
        ]
    }

    # Add to the anime data and save
    anime_data.append(new_anime)
    success = save_anime_data(anime_data)

    if success:
        return render_template('admin.html', message="Anime added successfully!", success=True)
    else:
        return render_template('admin.html', message="Error adding anime. Please try again.", success=False)

@app.route('/categories')
@login_required
def categories():
    anime_data = load_anime_data()
    genres = get_all_genres()

    # Create dictionary of genres and their anime
    genres_dict = {genre: [] for genre in genres}

    for anime in anime_data:
        for genre in anime.get('genres', []):
            if genre.lower() in genres_dict:
                genres_dict[genre.lower()].append(anime)

    return render_template('categories.html', all_anime=anime_data, genres=genres, genres_dict=genres_dict)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si l'utilisateur est déjà connecté, rediriger vers l'accueil
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # Traitement du formulaire de connexion
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Vérification des identifiants
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Mettre à jour la date de dernière connexion
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()

            # Connecter l'utilisateur
            login_user(user)
            logger.debug(f"User {username} logged in successfully")

            # Redirection vers la page demandée ou l'accueil
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('index'))
        else:
            logger.debug(f"Failed login attempt for user {username}")
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')

    return render_template('login_new.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Si l'utilisateur est déjà connecté, rediriger vers l'accueil
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # Traitement du formulaire d'inscription
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Vérifier si les mots de passe correspondent
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('register_new.html')

        # Vérifier si le nom d'utilisateur existe déjà
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
        else:
            # Créer un nouvel utilisateur
            new_user = User(username=username)
            new_user.set_password(password)

            # Enregistrer en base de données
            db.session.add(new_user)
            db.session.commit()

            logger.debug(f"New user registered: {username}")
            flash('Votre compte a été créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))

    return render_template('register_new.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        current_password = request.form.get('current_password')
        new_username = request.form.get('new_username')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Vérifier le mot de passe actuel
        if not current_user.check_password(current_password):
            flash('Mot de passe actuel incorrect', 'danger')
            return redirect(url_for('settings'))

        # Mettre à jour le nom d'utilisateur si fourni
        if new_username and new_username != current_user.username:
            # Vérifier si le nom d'utilisateur existe déjà
            if User.query.filter_by(username=new_username).first():
                flash('Ce nom d\'utilisateur est déjà pris', 'danger')
                return redirect(url_for('settings'))
            current_user.username = new_username

        # Mettre à jour le mot de passe si fourni
        if new_password:
            if new_password != confirm_password:
                flash('Les nouveaux mots de passe ne correspondent pas', 'danger')
                return redirect(url_for('settings'))
            current_user.set_password(new_password)

        # Sauvegarder les modifications
        db.session.commit()
        flash('Paramètres mis à jour avec succès', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html')

@app.route('/profile')
@login_required
def profile():
    # Récupérer les animes en cours de visionnage
    progress_data = UserProgress.query.filter_by(user_id=current_user.id).order_by(UserProgress.last_watched.desc()).all()

    # Récupérer les détails des animes
    anime_data = load_anime_data()
    watching_anime = []

    for progress in progress_data:
        anime = next((a for a in anime_data if int(a.get('id', 0)) == progress.anime_id), None)
        if anime:
            # Trouver la saison et l'épisode
            season = next((s for s in anime.get('seasons', []) if s.get('season_number') == progress.season_number), None)
            episode = None
            if season:
                episode = next((e for e in season.get('episodes', []) if e.get('episode_number') == progress.episode_number), None)

            watching_anime.append({
                'progress': progress,
                'anime': anime,
                'season': season,
                'episode': episode
            })

    # Récupérer les favoris
    favorites = UserFavorite.query.filter_by(user_id=current_user.id).all()
    favorite_anime = []

    for favorite in favorites:
        anime = next((a for a in anime_data if int(a.get('id', 0)) == favorite.anime_id), None)
        if anime:
            favorite_anime.append(anime)

    return render_template('profile_new.html', 
                          watching_anime=watching_anime, 
                          favorite_anime=favorite_anime)

@app.route('/remove-from-watching', methods=['POST'])
@login_required
def remove_from_watching():
    try:
        if request.method == 'POST':
            anime_id = request.form.get('anime_id', type=int)
            if anime_id:
                # Supprimer toutes les entrées de progression pour cet anime
                UserProgress.query.filter_by(
                    user_id=current_user.id,
                    anime_id=anime_id
                ).delete()

                db.session.commit()
                return jsonify({'success': True})

        return jsonify({'success': False, 'error': 'ID anime manquant'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/save-progress', methods=['POST'])
@login_required
def save_progress():
    if request.method == 'POST':
        anime_id = request.form.get('anime_id', type=int)
        season_number = request.form.get('season_number', type=int)
        episode_number = request.form.get('episode_number', type=int)
        time_position = request.form.get('time_position', type=float)
        completed = request.form.get('completed') == 'true'

        # Chercher une entrée existante
        progress = UserProgress.query.filter_by(
            user_id=current_user.id,
            anime_id=anime_id,
            season_number=season_number,
            episode_number=episode_number
        ).first()

        if progress:
            # Mettre à jour l'entrée existante
            progress.time_position = time_position
            progress.completed = completed
            progress.last_watched = datetime.datetime.utcnow()
        else:
            # Créer une nouvelle entrée
            progress = UserProgress(
                user_id=current_user.id,
                anime_id=anime_id,
                season_number=season_number,
                episode_number=episode_number,
                time_position=time_position,
                completed=completed,
                last_watched=datetime.datetime.utcnow()
            )
            db.session.add(progress)

        if progress:
            # Mettre à jour l'entrée existante, mais conserver le statut "terminé" si déjà marqué
            if not progress.completed:  # Si l'épisode n'était pas déjà terminé
                progress.time_position = time_position
                progress.completed = completed
            else:
                # Si l'épisode était déjà marqué comme terminé, ne le remettre "en cours" que si explicitement demandé
                if not completed:
                    # On ne remet pas à "non terminé" un épisode déjà marqué terminé
                    # sauf si le temps est revenu en arrière (par ex. début de l'épisode)
                    if time_position < progress.time_position * 0.5:  # Si position actuelle < 50% de la position sauvegardée
                        progress.completed = False
                        progress.time_position = time_position

            # Toujours mettre à jour la date de dernière visualisation
            progress.last_watched = datetime.datetime.utcnow()
        else:
            # Créer une nouvelle entrée
            progress = UserProgress(
                user_id=current_user.id,
                anime_id=anime_id,
                season_number=season_number,
                episode_number=episode_number,
                time_position=time_position,
                completed=completed
            )
            db.session.add(progress)

        db.session.commit()
        return {'success': True}, 200

    return {'success': False, 'error': 'Invalid request'}, 400

@app.route('/toggle-favorite', methods=['POST'])
@login_required
def toggle_favorite():
    if request.method == 'POST':
        anime_id = request.form.get('anime_id', type=int)

        # Vérifier si l'anime est déjà dans les favoris
        favorite = UserFavorite.query.filter_by(
            user_id=current_user.id, 
            anime_id=anime_id
        ).first()

        if favorite:
            # Supprimer des favoris
            db.session.delete(favorite)
            db.session.commit()
            return {'success': True, 'action': 'removed'}, 200
        else:
            # Ajouter aux favoris
            favorite = UserFavorite(
                user_id=current_user.id,
                anime_id=anime_id
            )
            db.session.add(favorite)
            db.session.commit()
            return {'success': True, 'action': 'added'}, 200

    return {'success': False, 'error': 'Invalid request'}, 400
@app.route('/documentation')
@login_required
def documentation():
    return render_template('documentation.html')

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    # Choisir le template en fonction de l'authentification
    if current_user.is_authenticated:
        return render_template('404.html'), 404
    else:
        return render_template('404_public.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    # Choisir le template en fonction de l'authentification
    if current_user.is_authenticated:
        return render_template('404.html'), 500
    else:
        return render_template('404_public.html'), 500

# Créer les tables au démarrage
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully!")
        
        # Précharger les animes populaires au démarrage
        preload_popular_animes()
        logger.info("Animes populaires préchargés avec succès")
    except Exception as e:
        logger.error(f"Error creating database tables or preloading animes: {e}")

@app.route('/download-episode/<int:anime_id>/<int:season_num>/<int:episode_num>')
@login_required
def download_episode(anime_id, season_num, episode_num):
    """
    Télécharge un épisode d'anime via l'ancienne méthode
    
    Cette fonction est maintenue pour la rétrocompatibilité mais redirige
    désormais vers la nouvelle méthode de téléchargement direct
    """
    # Rediriger vers la page du lecteur avec un message
    flash("Utilisez le bouton de téléchargement sur la page du lecteur pour une meilleure expérience.", "info")
    return redirect(url_for('player', anime_id=anime_id, season_num=season_num, episode_num=episode_num))

@app.route('/api/download-direct', methods=['POST'])
@login_required
def download_direct():
    """
    Télécharge directement depuis l'URL fournie
    
    Cette API reçoit l'URL du lecteur actuel et utilise yt-dlp pour
    télécharger directement la vidéo.
    """
    try:
        # Récupérer les données JSON
        data = request.json
        if not data:
            return jsonify({'error': 'Aucune donnée reçue'}), 400
            
        video_url = data.get('url')
        anime_id = data.get('anime_id')
        season_num = data.get('season_num')
        episode_num = data.get('episode_num')
        
        if not video_url or not anime_id or not season_num or not episode_num:
            return jsonify({'error': 'Paramètres manquants'}), 400
            
        logger.info(f"Téléchargement direct depuis {video_url} pour anime {anime_id}, saison {season_num}, épisode {episode_num}")
        
        # Récupérer les informations de l'anime
        anime_data = load_anime_data()
        anime = next((a for a in anime_data if int(a.get('id', 0)) == anime_id), None)
        
        if not anime:
            return jsonify({'error': 'Anime non trouvé'}), 404
            
        # Créer un nom de fichier sécurisé
        anime_title_safe = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in anime['title'])
        download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads', anime_title_safe, f"Saison {season_num}")
        os.makedirs(download_dir, exist_ok=True)
        
        output_file = os.path.join(download_dir, f'Episode {episode_num}.mp4')
        
        # Import yt-dlp ici pour éviter les problèmes d'importation
        from yt_dlp import YoutubeDL
        
        # Configuration de yt-dlp optimisée pour le téléchargement direct
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Préférer MP4 pour la compatibilité
            'outtmpl': output_file,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'restrictfilenames': True,
            'no_check_certificate': True,
            'ignoreerrors': True
        }
        
        try:
            # Utiliser yt-dlp pour télécharger la vidéo
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                
                # Si le téléchargement a réussi, générer une URL pour le fichier
                if os.path.exists(output_file):
                    # Générer un nom de fichier pour le téléchargement
                    download_name = f"{anime_title_safe} - S{season_num}E{episode_num}.mp4"
                    
                    # Créer une URL de téléchargement temporaire
                    download_url = url_for('download_file', 
                                        anime_id=anime_id, 
                                        season_num=season_num, 
                                        episode_num=episode_num,
                                        _external=True)
                    
                    return jsonify({
                        'success': True,
                        'download_url': download_url,
                        'filename': download_name
                    })
                else:
                    logger.error(f"Le fichier {output_file} n'a pas été créé après téléchargement")
                    return jsonify({'error': 'Échec du téléchargement - fichier non créé'}), 500
                    
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement direct: {str(e)}")
            return jsonify({'error': f'Erreur de téléchargement: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Erreur générale lors du téléchargement direct: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@app.route('/download-file/<int:anime_id>/<int:season_num>/<int:episode_num>')
@login_required
def download_file(anime_id, season_num, episode_num):
    """
    Télécharge un fichier déjà téléchargé sur le serveur
    """
    try:
        # Récupérer l'anime
        anime_data = load_anime_data()
        anime = next((a for a in anime_data if int(a.get('id', 0)) == anime_id), None)
        
        if not anime:
            return jsonify({'error': 'Anime non trouvé'}), 404
            
        # Construire le chemin du fichier
        anime_title_safe = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in anime['title'])
        download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads', anime_title_safe, f"Saison {season_num}")
        
        # Vérifier si le fichier existe
        output_file = os.path.join(download_dir, f'Episode {episode_num}.mp4')
        
        if os.path.exists(output_file):
            return send_file(
                output_file,
                as_attachment=True,
                download_name=f"{anime_title_safe} - S{season_num}E{episode_num}.mp4"
            )
        else:
            logger.error(f"Fichier non trouvé: {output_file}")
            return jsonify({'error': 'Fichier non trouvé'}), 404
            
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement du fichier: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

if __name__ == '__main__':
    import argparse
    
    # Précharger les animes populaires avant le démarrage du serveur
    with app.app_context():
        try:
            preload_popular_animes()
            logger.info("Préchargement des animes populaires effectué avant le démarrage du serveur")
        except Exception as e:
            logger.error(f"Erreur lors du préchargement des animes populaires: {e}")
    
    # Créer un parser pour les arguments en ligne de commande
    parser = argparse.ArgumentParser(description='Serveur AnimeZone')
    
    # Utiliser le port défini par l'environnement Replit si disponible, sinon 8080
    default_port = int(os.environ.get('PORT', 8080))
    parser.add_argument('--port', type=int, default=default_port, help=f'Port sur lequel démarrer le serveur (défaut: {default_port})')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Hôte sur lequel démarrer le serveur (défaut: 0.0.0.0)')
    
    # Analyser les arguments
    args = parser.parse_args()
    
    # Démarrer le serveur avec les arguments spécifiés
    print(f"Démarrage du serveur sur {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)
