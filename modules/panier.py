import json
from pathlib import Path

FICHIER_PANIERS = Path("paniers.json")

def charger_panier(nom="defaut"):
    """Charge un panier nommé depuis le fichier JSON."""
    if FICHIER_PANIERS.exists():
        with open(FICHIER_PANIERS, 'r', encoding='utf-8') as f:
            paniers = json.load(f)
            panier = paniers.get(nom, {})
            # Convertir tous les prix en float et normaliser les noms de magasins
            panier_normalise = {}
            for article, magasins in panier.items():
                if isinstance(magasins, dict):
                    # Normaliser les noms de magasins (fusionner les doublons de casse)
                    magasins_normalises = {}
                    dates_normalisees = {}
                    dates_orig = magasins.get("_dates", {})
                    
                    for mag, prix in magasins.items():
                        if mag.startswith("_"):
                            continue
                        if prix is not None:
                            try:
                                prix_float = float(prix)
                            except (ValueError, TypeError):
                                prix_float = 0.0
                            
                            # Clé normalisée (minuscules) pour détecter les doublons
                            mag_lower = mag.lower()
                            if mag_lower in magasins_normalises:
                                # Garder le prix le plus bas si doublon
                                if prix_float < magasins_normalises[mag_lower]:
                                    magasins_normalises[mag_lower] = prix_float
                                    # Mettre à jour la date aussi
                                    if mag in dates_orig:
                                        dates_normalisees[mag_lower] = dates_orig[mag]
                            else:
                                magasins_normalises[mag_lower] = prix_float
                                if mag in dates_orig:
                                    dates_normalisees[mag_lower] = dates_orig[mag]
                    
                    # Mettre à jour le panier avec les magasins normalisés
                    # Utiliser la première lettre en majuscule pour le nom affiché
                    panier_normalise[article] = {}
                    for mag_lower, prix in magasins_normalises.items():
                        # Capitaliser le nom du magasin
                        mag_capitalized = mag_lower.capitalize()
                        panier_normalise[article][mag_capitalized] = prix
                    
                    # Restaurer les dates
                    if dates_normalisees:
                        panier_normalise[article]["_dates"] = {}
                        for mag_lower, date in dates_normalisees.items():
                            mag_capitalized = mag_lower.capitalize()
                            panier_normalise[article]["_dates"][mag_capitalized] = date
                else:
                    panier_normalise[article] = magasins
            
            # Sauvegarder les données normalisées si différentes
            if panier_normalise != panier:
                paniers[nom] = panier_normalise
                with open(FICHIER_PANIERS, 'w', encoding='utf-8') as f:
                    json.dump(paniers, f, indent=2, ensure_ascii=False)
            
            return panier_normalise
    return {}

def sauvegarder_panier(panier, nom="defaut"):
    """Sauvegarde le panier avec un nom dans le fichier JSON."""
    paniers = {}
    if FICHIER_PANIERS.exists():
        with open(FICHIER_PANIERS, 'r', encoding='utf-8') as f:
            paniers = json.load(f)
    
    paniers[nom] = panier
    
    with open(FICHIER_PANIERS, 'w', encoding='utf-8') as f:
        json.dump(paniers, f, indent=2, ensure_ascii=False)

def lister_paniers():
    """Liste tous les paniers sauvegardés, triés par date (plus récent en premier)."""
    if FICHIER_PANIERS.exists():
        with open(FICHIER_PANIERS, 'r', encoding='utf-8') as f:
            paniers = json.load(f)
            noms = list(paniers.keys())
            
            # Fonction pour extraire une date du nom du panier
            def extraire_date(nom):
                import re
                from datetime import datetime
                # Chercher un pattern de date DD.MM.YYYY ou DD/MM/YYYY
                match = re.search(r'(\d{2})[./](\d{2})[./](\d{4})', nom)
                if match:
                    jour, mois, annee = match.groups()
                    try:
                        return datetime(int(annee), int(mois), int(jour))
                    except:
                        pass
                # Si pas de date trouvée, mettre à la fin
                return datetime.min
            
            # Trier par date décroissante (plus récent en premier)
            noms_tries = sorted(noms, key=extraire_date, reverse=True)
            return noms_tries
    return ["defaut"]

def supprimer_panier(nom):
    """Supprime un panier par son nom."""
    if FICHIER_PANIERS.exists():
        with open(FICHIER_PANIERS, 'r', encoding='utf-8') as f:
            paniers = json.load(f)
        
        if nom in paniers:
            del paniers[nom]
            with open(FICHIER_PANIERS, 'w', encoding='utf-8') as f:
                json.dump(paniers, f, indent=2, ensure_ascii=False)
            return True
    return False
