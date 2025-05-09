"""
Script pour récupérer du contenu textuel à partir d'une page web
Utilise Trafilatura pour extraire le contenu principal
"""

import trafilatura


def get_website_text_content(url: str) -> str:
    """
    Cette fonction prend une URL et retourne le contenu textuel principal du site web.
    Le contenu est extrait avec trafilatura et est plus facile à comprendre.
    
    Quelques sites web courants pour récupérer des informations :
    Scores MLB : https://www.mlb.com/scores/YYYY-MM-DD
    """
    # Envoyer une requête au site web
    downloaded = trafilatura.fetch_url(url)
    
    # Extraire le texte principal
    text = trafilatura.extract(downloaded)
    
    return text


if __name__ == "__main__":
    test_url = "https://www.mlb.com/scores/2024-05-07"
    content = get_website_text_content(test_url)
    print("Contenu extrait :")
    print("-" * 50)
    print(content[:1000] + "..." if len(content) > 1000 else content)
    print("-" * 50)