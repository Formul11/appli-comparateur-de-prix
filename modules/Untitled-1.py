

import json
import os
from rapidfuzz import process, fuzz
from unidecode import unidecode

FICHIER_PRODUITS = "produits.json"

def charger_produits():
    """Charge la base de produits depuis produits.json."""
    if os.path.exists(FICHIER_PRODUITS):
        with open(FICHIER_PRODUITS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def sauvegarder_produits(produits):
    """Sauvegarde la base de produits (triée et unique)."""
    produits_uniques = sorted(list(set(produits)))
    with open(FICHIER_PRODUITS, "w", encoding="utf-8") as f:
        json.dump(produits_uniques, f, indent=4, ensure_ascii=False)

def nettoyer_nom(nom: str) -> str:
    """Nettoyage OCR : majuscules, accents, espaces multiples."""
    nom = nom.upper()
    nom = unidecode(nom)
    nom = " ".join(nom.split())
    return nom

def corriger_ou_apprendre(nom: str, seuil=80):
    """
    Corrige un nom OCR ou l'ajoute à la base si inconnu.

    Retourne :
        nom_final (str)
        is_new (bool)
        is_corrected (bool)
    """
    produits = charger_produits()
    nom_nettoye = nettoyer_nom(nom)

    # Base vide → premier apprentissage
    if not produits:
        produits.append(nom_nettoye)
        sauvegarder_produits(produits)
        return nom_nettoye, True, False

    # Recherche du produit le plus similaire
    meilleur, score, _ = process.extractOne(
        nom_nettoye,
        produits,
        scorer=fuzz.WRatio
    )

    # Correction si similarité suffisante
    if score >= seuil:
        return meilleur, False, True

    # Sinon → nouveau produit appris
    produits.append(nom_nettoye)
    sauvegarder_produits(produits)
    return nom_nettoye, True, False
