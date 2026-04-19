import pandas as pd

def calculer_totaux(panier, magasins):
    """Calcule le total par magasin."""
    totaux = {magasin: 0.0 for magasin in magasins}
    
    for article, prix_magasins in panier.items():
        for magasin, prix in prix_magasins.items():
            # Ignorer les clés spéciales comme _dates
            if not magasin.startswith("_") and magasin in totaux:
                try:
                    prix_float = float(prix)
                    totaux[magasin] += prix_float
                except (ValueError, TypeError):
                    pass
    
    return totaux

def analyse_ecarts(panier, magasins):
    """Analyse les écarts de prix par article."""
    ecarts = {}
    
    for article, prix_magasins in panier.items():
        # Filtrer uniquement les magasins avec un prix > 0 (ignorer _dates et autres clés spéciales)
        prix_par_magasin = {m: p for m, p in prix_magasins.items() if not m.startswith("_") and isinstance(p, (int, float)) and p > 0}
        
        if len(prix_par_magasin) >= 2:
            # Trouver le magasin avec le prix min et max
            magasin_min = min(prix_par_magasin, key=prix_par_magasin.get)
            magasin_max = max(prix_par_magasin, key=prix_par_magasin.get)
            min_prix = prix_par_magasin[magasin_min]
            max_prix = prix_par_magasin[magasin_max]
            
            ecarts[article] = {
                'magasin_min': magasin_min,
                'min': min_prix,
                'magasin_max': magasin_max,
                'max': max_prix,
                'ecart': max_prix - min_prix,
                'economie': round((max_prix - min_prix) / max_prix * 100, 1) if max_prix > 0 else 0
            }
    
    return ecarts
