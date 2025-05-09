#!/usr/bin/env python3
"""
Script pour supprimer les animes problématiques du fichier anime.json
et permettre leur recréation correcte lors du prochain démarrage.
"""

import os
import json
import sys

def load_anime_data(json_path):
    """Charge les données depuis le fichier anime.json"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure we're getting a dictionary with an anime key
            if isinstance(data, dict) and 'anime' in data:
                print(f"Données chargées: {len(data['anime'])} animes trouvés")
                return data['anime']
            elif isinstance(data, list):
                # If it's just a list (no wrapper), return it directly
                print(f"Données chargées (format liste): {len(data)} animes trouvés")
                return data
            else:
                # Create a default structure
                print("Anime data file has unexpected format. Creating default structure.")
                return []
    except FileNotFoundError:
        print(f"Anime data file not found: {json_path}")
        return []
    except json.JSONDecodeError:
        print("Error decoding anime data file. Returning empty list.")
        return []

def save_anime_data(data, json_path):
    """Sauvegarde les données dans le fichier anime.json"""
    try:
        # Déterminer le format à sauvegarder (liste ou dictionnaire avec clé 'anime')
        # On préfère conserver le format original
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                try:
                    original_data = json.load(f)
                    is_dict_format = isinstance(original_data, dict) and 'anime' in original_data
                except:
                    # En cas d'erreur, utiliser le format dictionnaire par défaut
                    is_dict_format = True
        except FileNotFoundError:
            is_dict_format = True
        
        # Sauvegarder dans le format approprié
        with open(json_path, 'w', encoding='utf-8') as f:
            if is_dict_format:
                json.dump({'anime': data}, f, indent=4, ensure_ascii=False)
            else:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
        print(f"Données sauvegardées avec succès: {len(data)} animes")
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des données anime: {e}")
        return False

def remove_problematic_animes(json_path):
    """Supprime les animes qui ont des problèmes de saisons"""
    anime_data = load_anime_data(json_path)
    
    # Liste des animes à supprimer
    problematic_titles = ["Death Note", "Demon Slayer", "My Hero Academia", "Mashle"]
    
    # Filtrer pour garder uniquement les animes non problématiques
    filtered_animes = []
    for anime in anime_data:
        if anime.get('title') in problematic_titles:
            print(f"Suppression de l'anime problématique: {anime.get('title')}")
        else:
            filtered_animes.append(anime)
    
    # Sauvegarder la liste filtrée
    if len(filtered_animes) < len(anime_data):
        save_anime_data(filtered_animes, json_path)
        print(f"Animes problématiques supprimés. Nouveaux animes: {len(filtered_animes)}")
    else:
        print("Aucun anime problématique trouvé")

def main():
    # Trouver le chemin du fichier anime.json
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "realweb", "final_website", "static", "data", "anime.json")
    
    print(f"Recherche du fichier anime.json dans: {json_path}")
    
    if not os.path.exists(json_path):
        print(f"Fichier anime.json non trouvé à l'emplacement: {json_path}")
        sys.exit(1)
    
    print(f"Fichier anime.json trouvé. Suppression des animes problématiques...")
    remove_problematic_animes(json_path)
    print("Terminé. Vous pouvez maintenant démarrer l'application.")

if __name__ == "__main__":
    main()