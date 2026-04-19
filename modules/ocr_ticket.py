import re
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime

# Dictionnaire de corrections orthographiques communes pour les articles de supermarché
CORRECTIONS_ARTICLES = {
    'pomme': ['pommme', 'pommmes', 'pomes', 'pommees'],
    'pommes': ['pommme', 'pommmes', 'pomes', 'pommees', 'pomme'],
    'poire': ['poirrre', 'poires', 'poirres'],
    'poires': ['poirrre', 'poire', 'poirres'],
    'pain': ['painn', 'pains', 'painss'],
    'lait': ['laiit', 'laitt', 'lai'],
    'beurre': ['beurrre', 'beur', 'beurres'],
    'fromage': ['frommage', 'fromages', 'frommages'],
    'yaourt': ['yaourrt', 'yaourts', 'yahourt'],
    'oeufs': ['oeuf', 'oeufss', 'eufs', 'eoufs'],
    'farine': ['farinne', 'farines'],
    'sucre': ['sucrre', 'sucres'],
    'sel': ['sell', 'selll'],
    'poivre': ['poivrre', 'poivres'],
    'huile': ['huilee', 'huilles'],
    'vinaigre': ['vinaigrre', 'vinaigres'],
    'moutarde': ['moutardre', 'moutardes'],
    'ketchup': ['ketchupp', 'ketchups'],
    'mayonnaise': ['mayonnaisse', 'mayonnais'],
    'jambon': ['jambonn', 'jambons'],
    'saucisson': ['saucissonn', 'saucissons'],
    'poulet': ['poullet', 'poulets'],
    'boeuf': ['boeuff', 'boeufs'],
    'porc': ['porcc', 'porcs'],
    'poisson': ['poissonn', 'poissons'],
    'saumon': ['saumonn', 'saumons'],
    'thon': ['thonn', 'thons'],
    'riz': ['rizz', 'rizzz'],
    'pates': ['patess', 'patte', 'pate'],
    'nouilles': ['nouille', 'nouilless'],
    'carottes': ['carotte', 'carotess'],
    'pommes de terre': ['pomme de terre', 'pdt', 'pommes de terress'],
    'oignons': ['oignon', 'oignonss'],
    'ail': ['aill', 'ailll'],
    'tomates': ['tomate', 'tomatess'],
    'concombre': ['concombres', 'concombrre'],
    'salade': ['salades', 'saladre'],
    'epinards': ['epinard', 'epinardss'],
    'haricots': ['haricot', 'haricotss'],
    'petits pois': ['petit pois', 'petits poiss'],
    'mais': ['maiss', 'maiss'],
    'champignons': ['champignon', 'champignonss'],
    'citron': ['citronn', 'citrons'],
    'orange': ['orangre', 'oranges'],
    'banane': ['bananes', 'banannne'],
    'pamplemousse': ['pamplemoussse', 'pamplemousses'],
    'raisins': ['raisin', 'raisinss'],
    'peche': ['peches', 'pechess'],
    'abricot': ['abricots', 'abricotss'],
    'fraise': ['fraises', 'fraisses'],
    'framboise': ['framboises', 'framboisses'],
    'myrtille': ['myrtilles', 'myrtillles'],
    'cerise': ['cerises', 'cerisses'],
    'prune': ['prunes', 'pruness'],
    'pasteque': ['pasteques', 'pastèque'],
    'melon': ['melons', 'melonnn'],
    'cafe': ['cafee', 'caffé', 'caffee'],
    'the': ['thee', 'thé', 'theee'],
    'jus': ['juss', 'juss'],
    'eau': ['eaux', 'eauu'],
    'soda': ['sodas', 'sodaa'],
    'biere': ['bierres', 'bieres'],
    'vin': ['vinn', 'vins'],
    'champagne': ['champagnes', 'champagnne'],
    'whisky': ['whiskys', 'whiskyy'],
    'vodka': ['vodkas', 'vodkaa'],
    'rhum': ['rhumm', 'rhums'],
    'chocolat': ['chocolatt', 'chocolats'],
    'bonbons': ['bonbon', 'bonbonss'],
    'gateau': ['gateaux', 'gateauu'],
    'biscuits': ['biscuit', 'biscuitss'],
    'chips': ['chipss', 'chip'],
    'cacahuetes': ['cacahuette', 'cacahuetes', 'acahuetes', 'cachuetas', 'acahuetas', 'cacahuete'],
    'noix': ['noixx', 'noixxx'],
    'amandes': ['amande', 'amandess'],
    'noisettes': ['noisette', 'noisettes'],
    'lessive': ['lessives', 'lessivve'],
    'savon': ['savons', 'savonn'],
    'shampoing': ['shampoings', 'shampoinng'],
    'dentifrice': ['dentifrices', 'dentifricce'],
    'papier toilette': ['papier toilettes', 'pq', 'papier toilettte'],
    'essuie-tout': ['essuie tout', 'essuie-touts'],
    'sac poubelle': ['sacs poubelle', 'sac poubelles'],
    'aluminium': ['aluminium', 'alu'],
    'film etirable': ['film etirables', 'film alimentaire'],
    'cotons': ['coton', 'cotonss'],
    'pansements': ['pansement', 'pansementss'],
    # Corrections supplémentaires
    'cheque': ['cheque', 'cheq', 'cheques', 'chequee'],
    # Corrections pour erreurs OCR sévères (tickets flous/mal scannés)
    'cacahuetes grillees': ['acahuetes oft leg', 'cachuetas grillees', 'acahuetes gril lee', 'cacahuetes gril lee'],
    'fromage blanc': ['fromage blann', 'fromage blan', 'fromblanc'],
    'fromage blanc vanille': ['fromage blann vars', 'fromage blanc vars', 'fromblanc vanille'],
    'confiture': ['onf ture', 'confuture', 'onfuture', 'conf ture'],
    'confiture abricot': ['onf ture abricot', 'onfuture abricot', 'confuture abricot'],
    'croustilles': ['te croustille', 'croustille', 'crostilles'],
    'petites croustilles': ['te croustille', 'petite croustille'],
    'fruits vitalite': ['ts vitalite', 'fruit vitalite', 'fruits vitalit'],
    'mouchoirs xl': ['meuches xl', 'mouche xl', 'meuche xl'],
    'mouchoirs': ['meuches', 'mouche', 'meuche'],
    'hache': ['hachee', 'hach', 'ache'],
    'viande hachee': ['viande hache', 'viand hachee'],
    'saucisses': ['sauciss', 'saucisse', 'aucisses'],
    'knacki': ['knack', 'kncki', 'knaki'],
    'jambon blanc': ['jambonn blanc', 'jambo blanc'],
    'pate brisee': ['pate brise', 'pate brice'],
    'pates feuilletees': ['pates feuillete', 'pate feuilletees'],
    'compote': ['compot', 'compte', 'compotee'],
    'compote pomme': ['compot pomme', 'compte pomme'],
    'yaourt nature': ['yaourt nat', 'yaour nature'],
    'yaourt aux fruits': ['yaourt au fruit', 'yaour aux fruits'],
    'petits suisses': ['petits suiss', 'petit suisses', 'peti suisses'],
    'beurre demi-sel': ['beurre dem sel', 'beurre demi sel'],
    'beurre doux': ['beurre dou', 'beur doux'],
    'creme fraiche': ['creme fraich', 'crem fraiche'],
    'creme epaisse': ['creme epais', 'crem epaisse'],
    'emmental rape': ['emmental rap', 'emental rape'],
    'gruyere rape': ['gruyere rap', 'gruyer rape'],
    'mozzarella': ['mozzarela', 'mozarella', 'mozzarel'],
    'chapelure': ['chapelur', 'chapel'],
    'biscottes': ['biscott', 'biscote'],
    'pains de mie': ['pains de mi', 'pain de mie'],
    'pains complets': ['pains complet', 'pain complets'],
    'pains aux cereales': ['pains aux cereal', 'pain aux cereales'],
    'madeleines': ['madelein', 'madeleine'],
    'muffins': ['muffin', 'muffi'],
    'donuts': ['donut', 'donu'],
    'croissants': ['croissant', 'croissn'],
    'pains au chocolat': ['pains au choco', 'pain au chocolat'],
    'brioche': ['brioch', 'briochh'],
    'galette des rois': ['galette des roi', 'galette de rois'],
}

# Configuration du chemin Tesseract pour Windows
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\acker\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
]

# Trouver et configurer Tesseract
for path in TESSERACT_PATHS:
    if Path(path).exists():
        pytesseract.pytesseract.tesseract_cmd = path
        break

# Mots-clés pour détecter les magasins sur les tickets (élargi)
MAGASINS_KEYWORDS = {
    'Carrefour': ['carrefour', 'market', 'carrefour market', 'cf market'],
    'Leclerc': ['leclerc', 'e.leclerc', 'eleclerc', 'e leclerc'],
    'Lidl': ['lidl'],
    'Auchan': ['auchan', 'auchan hyper', 'auchan supermarche'],
    'Intermarché': ['intermarche', 'intermarché', 'intermarché contact'],
    'Casino': ['casino', 'casino supermarche', 'supermarche casino'],
    'Monoprix': ['monoprix'],
    'Franprix': ['franprix'],
    'Cora': ['cora'],
    'Hyper U': ['hyper u', 'systeme u', 'super u'],
    'Aldi': ['aldi'],
    'Leader Price': ['leader price'],
    'Simply Market': ['simply market', 'simply'],
    'Match': ['match'],
    'Colruyt': ['colruyt'],
    'Delhaize': ['delhaize'],
    'Biocoop': ['biocoop'],
    'Naturalia': ['naturalia'],
    'Picard': ['picard'],
    'Thiriet': ['thiriet'],
}

def pretraitement_image(image):
    """Améliore la qualité de l'image pour l'OCR avec plusieurs techniques avancées."""
    # Convertir en niveaux de gris
    img = image.convert('L')
    
    # Redimensionner si l'image est trop petite (meilleure précision OCR)
    width, height = img.size
    min_width = 2000  # Augmenté pour meilleure précision
    if width < min_width:
        ratio = min_width / width
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Détection et correction de l'angle (deskew simple)
    img = _corriger_inclinaison(img)
    
    # Augmenter le contraste plus agressivement
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(4.0)  # Augmenté pour meilleur contraste
    
    # Améliorer la luminosité
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.2)
    
    # Réduire le bruit
    img = img.filter(ImageFilter.MedianFilter(size=5))
    
    # Dilatation et érosion pour renforcer les caractères
    img = img.filter(ImageFilter.MaxFilter(size=3))
    img = img.filter(ImageFilter.MinFilter(size=3))
    
    # Netteté finale
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)
    
    # Seuillage adaptatif (Otsu-like simplifié)
    img = _seuillage_adaptatif(img)
    
    return img

def _corriger_inclinaison(img):
    """Correction simple de l'inclinaison basée sur la projection de profil."""
    # Pour l'instant, retourne l'image telle quelle
    # Une implémentation complète nécessiterait OpenCV
    return img

def _seuillage_adaptatif(img):
    """Seuillage adaptatif basé sur la moyenne locale."""
    img_array = np.array(img)
    
    # Calculer le seuil moyen global
    seuil_global = np.mean(img_array)
    
    # Appliquer un seuillage adaptatif
    # Pixels plus clairs que la moyenne -> blanc, sinon noir
    img_seuil = np.where(img_array > seuil_global - 10, 255, 0).astype(np.uint8)
    
    return Image.fromarray(img_seuil, mode='L')

def extraire_texte_ticket(image):
    """Extrait le texte d'une image de ticket de caisse avec OCR multi-stratégie avancée."""
    try:
        # Prétraitement avancé de l'image
        image_traitee = pretraitement_image(image)
        
        # Configuration OCR optimisée pour tickets avec plusieurs modes
        configs = [
            '--psm 3 -l fra+eng --oem 3',   # Mode complet auto avec LSTM
            '--psm 4 -l fra+eng --oem 3',   # Mode colonne
            '--psm 6 -l fra+eng --oem 3',   # Mode bloc uniforme
            '--psm 11 -l fra+eng --oem 3',  # Mode sparse text
            '--psm 12 -l fra+eng --oem 3',  # Mode sparse text with OSD
            '--psm 3 -l fra --oem 3',       # Français uniquement
            '--psm 6 -l fra --oem 3',       # Mode bloc uniforme FR
            '--psm 4 -l fra --oem 3',       # Mode colonne FR
            '--psm 11 -l fra --oem 3',      # Mode sparse text FR
        ]
        
        # Essayer différentes configurations
        textes = []
        scores = []
        for config in configs:
            try:
                texte = pytesseract.image_to_string(image_traitee, config=config)
                if texte and len(texte.strip()) > 10:  # Minimum réduit pour tickets courts
                    textes.append(texte)
                    # Score amélioré: longueur + chiffres + lignes avec prix potentiels
                    lignes_non_vides = len([l for l in texte.split('\n') if l.strip()])
                    nb_chiffres = len(re.findall(r'\d', texte))
                    # Bonus pour les lignes qui ressemblent à des articles avec prix
                    nb_lignes_prix = len(re.findall(r'[A-Za-z].*\d+[,.]\d{2}', texte))
                    score = lignes_non_vides * 2 + nb_chiffres + nb_lignes_prix * 5
                    scores.append(score)
            except Exception:
                continue
        
        # Combiner les résultats intelligemment
        if textes:
            # Trier par score décroissant
            textes_scores = sorted(zip(textes, scores), key=lambda x: x[1], reverse=True)
            
            # Prendre les 3 meilleurs résultats
            meilleurs_textes = [t[0] for t in textes_scores[:3]]
            
            # Fusionner tous les textes uniques
            toutes_lignes = set()
            texte_final = ""
            
            for texte in meilleurs_textes:
                for ligne in texte.split('\n'):
                    ligne_clean = ligne.strip()
                    if ligne_clean and len(ligne_clean) > 2:
                        # Clé de déduplication (normalisée)
                        cle = re.sub(r'\s+', ' ', ligne_clean.lower())
                        cle = re.sub(r'[,.]\d{2}$', '', cle)  # Ignorer le prix pour la déduplication
                        if cle not in toutes_lignes:
                            toutes_lignes.add(cle)
                            texte_final += ligne + '\n'
            
            return texte_final
        
        return ""
    except Exception as e:
        return f"Erreur OCR: {str(e)}"

def detecter_magasin(texte_ocr):
    """Détecte automatiquement le magasin depuis le ticket."""
    texte_lower = texte_ocr.lower()
    
    for magasin, keywords in MAGASINS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in texte_lower:
                return magasin
    
    return None

def nettoyer_nom_article(nom):
    """Nettoie et normalise le nom de l'article avec filtrage avancé."""
    if not nom:
        return ""
    
    # Supprimer les caractères spéciaux et codes
    nom = re.sub(r'[@#*%&$\(\)\[\]\{\}]', ' ', nom)
    
    # Supprimer les codes barres EAN (8-13 chiffres)
    nom = re.sub(r'\b\d{8,13}\b', '', nom)
    
    # Supprimer les codes produits courts (1-6 chiffres) PARTOUT dans le texte
    nom = re.sub(r'\b\d{1,6}\b', '', nom)
    
    # Supprimer les codes produits avec lettres (ex: C12345, REF123, PRBS 199)
    nom = re.sub(r'\b[A-Z]{2,6}\s*\d{1,6}\b', '', nom, flags=re.IGNORECASE)
    nom = re.sub(r'\b[A-Z]\d{4,10}\b', '', nom, flags=re.IGNORECASE)
    
    # Supprimer les poids/volumes (500g, 1L, 250ml, etc.) mais garder le contexte
    nom = re.sub(r'\b\d+(?:[,.]?\d*)?\s*(g|gr|kg|l|lt|ml|cl|mg)\b', '', nom, flags=re.IGNORECASE)
    
    # Supprimer les quantités explicites (x2, *3, (2), etc.)
    nom = re.sub(r'\bx\s*\d+\b', '', nom, flags=re.IGNORECASE)
    nom = re.sub(r'\*\s*\d+', '', nom)
    nom = re.sub(r'\(\s*\d+\s*\)', '', nom)
    
    # Supprimer les pourcentages et remises
    nom = re.sub(r'-?\d+\s*%', '', nom)
    
    # Supprimer les codes de réduction (ex: -20%, PROMO, etc.)
    nom = re.sub(r'\bPROMO\w*\b', '', nom, flags=re.IGNORECASE)
    nom = re.sub(r'\bSOLDES?\b', '', nom, flags=re.IGNORECASE)
    nom = re.sub(r'\bOFFRE?\w*\b', '', nom, flags=re.IGNORECASE)
    
    # Nettoyer les caractères spéciaux restants (mais garder les chiffres dans le nom)
    nom = re.sub(r'[^\w\s\-\'\.]', ' ', nom)
    
    # Supprimer les espaces multiples et les espaces en début/fin
    nom = re.sub(r'\s+', ' ', nom).strip()
    
    # Supprimer les articles trop courts (moins de 3 caractères ou moins de 2 lettres)
    if len(nom) < 3:
        return ""
    # Vérifier qu'il y a au moins 2 lettres
    lettres = re.findall(r'[A-Za-z]', nom)
    if len(lettres) < 2:
        return ""
    
    # Supprimer les articles qui ne contiennent que des chiffres
    if nom.isdigit():
        return ""
    
    # Supprimer les articles qui contiennent des mots exclus
    mots_exclus = ['total', 'carte', 'especes', 'espec', 'rendu', 'tva', 'ht', 'ttc']
    if any(mot in nom.lower() for mot in mots_exclus):
        return ""
    
    return nom

def parser_ticket(texte_ocr):
    """Parse le texte OCR pour extraire articles et prix avec détection optimisée."""
    articles = {}
    
    if texte_ocr is None or not texte_ocr.strip():
        return articles
    
    lignes = texte_ocr.split('\n')
    
    # Mots à exclure étendus
    mots_exclus = {
        'total', 'carte', 'especes', 'espec', 'rendu', 'tva', 'ht', 'ttc',
        'numero', 'ticket', 'caisse', 'date', 'heure', 'merci', 'remercie',
        'bienvenue', 'aurevoir', 'client', 'fidele', 'fid', 'cb', 'visa',
        'mastercard', 'american', 'express', 'payer', 'paye', 'monnaie',
        'remise', 'promo', 'reduction', 'offre', 'avantage', 'points',
        'sous-total', 'sous', 'article', 'articles', 'quantite', 'qty',
        'reference', 'ref', 'code', 'ean', 'montant', 'montants', 'facture',
        'facturee', 'tickete', 'adresse', 'tel', 'telephone', 'siret',
        'siren', 'tva intracom', 'port', 'portable', 'fax', 'email',
        'www', 'http', 'https', 'facebook', 'instagram',
        'cheque', 'cheques', 'chq', 'espece', 'liquide', 'carte bancaire',
        'debit', 'credit', 'virement', 'prelevement', 'tip', 'pourboire',
        'annule', 'remboursement', ' avoir', 'avoir ', 'ticket cadeau',
        'tpe', 'terminal', 'pinpad', 'signature', 'contactless',
        'frais', 'frais de', 'frais de service', 'service', 'emballage',
        'consigne', 'consignes', 'sac', 'sacs', 'cotisation', 'adhesion',
        # Ajouts pour plus de robustesse
        'rembours', 'rendre', 'rendu', 'monnaie', 'piece', 'centimes',
        'cb', 'carte', 'bancaire', 'paiement', 'paye', 'regle',
        'solde', 'soldee', 'credit', 'avoir', 'cadeau', 'bon',
        'reduction', 'remise', 'promo', 'promotion', 'offre', 'fid'
    }
    
    # Patterns OPTIMISÉS avec meilleure priorisation
    patterns = [
        # Format Carrefour/Leclerc: CODE ARTICLE ........ PRIX
        r'\d{1,6}\s+([A-Za-z][A-Za-z0-9\s\-\'\*\.]*?[A-Za-z])\s*\.+\s*(\d+[,.]\d{2})\s*[€\s]?',
        # Format Lidl/Aldi: ARTICLE ........ PRIX
        r'([A-Za-z][A-Za-z0-9\s\-\'\*\.]*?[A-Za-z])\s*\.{3,}\s*(\d+[,.]\d{2})\s*[€\s]?',
        # Format avec tabulation/espaces multiples
        r'([A-Za-z][A-Za-z0-9\s\-\'\.]*?[A-Za-z])\s{3,}(\d+[,.]\d{2})\s*[€\s]?$',
        # Format avec quantité: ARTICLE x2 PRIX ou ARTICLE (x2) PRIX
        r'([A-Za-z][A-Za-z0-9\s\-\'\.]*?[A-Za-z])\s*[x×X\(]\s*\d+[\)]?\s+(\d+[,.]\d{2})\s*[€\s]?',
        # Format simple: ARTICLE PRIX (le plus commun)
        r'([A-Za-z][A-Za-z0-9\s\-\'\.]{2,}?)\s+(\d{1,3}[,.]\d{2})\s*[€\s]?$',
        # Format prix collé: PAIN1.20 ou LAIT 0.90
        r'([A-Za-z]{3,})(\d{1,2}[,.]\d{2})\s*[€\s]?',
        # Format avec poids/volume: ARTICLE 500g 1.20
        r'([A-Za-z][A-Za-z0-9\s\-\']+?)\s+\d+[gmlkGMLK]+\s+(\d+[,.]\d{2})',
        # Format Lidl spécifique avec espaces avant prix
        r'^\s*([A-Za-z][A-Za-z\s\-\']+?[A-Za-z])\s+(\d+[,.]\d{2})\s*$',
        # Format très simple: MOT suivis d'espace puis prix
        r'([A-Za-z0-9]{2,})\s+(\d{1,4}[,.]\d{2})',
        # Format LIDL/ALDI: 1234567890123 ARTICL 2,50
        r'\d{13}\s+([A-Za-z][A-Za-z0-9\s\-]{2,30})\s+(\d{1,4}[,.]\d{2})',
        # Format Carrefour City: ARTICL 0,85 A
        r'([A-Z][A-Za-z\s]{2,25})\s+(\d[,.]\d{2})\s*[A-Z]?\s*$',
        # Format Monoprix: ARTICL..............12,50
        r'([A-Za-z][A-Za-z\s\-]{2,25})\.{2,30}(\d{1,4}[,.]\d{2})',
        # Format Franprix/Casino: ARTICL  1x  0,85
        r'([A-Za-z][A-Za-z\s\-]{2,25})\s+\d*x?\s*(\d[,.]\d{2})',
        # Format avec code court: 1234 ARTICL 2.50
        r'\d{1,4}\s+([A-Za-z][A-Za-z\s\-]{2,25})\s+(\d{1,4}[,.]\d{2})',
        # Format E.Leclerc: ARTICL* 2.50 (étoile après)
        r'([A-Za-z][A-Za-z\s\-]{2,25})\*\s*(\d{1,4}[,.]\d{2})',
        # Format Auchan: ARTICL..2,50€
        r'([A-Za-z][A-Za-z\s\-]{2,25})\.\.*(\d{1,4}[,.]\d{2})\s*€?',
        # Format Intermarché: ARTICL 1 2,50 (quantité + prix)
        r'([A-Za-z][A-Za-z\s\-]{2,25})\s+\d+\s+(\d{1,4}[,.]\d{2})',
        # Format Cora: ARTICL............ 2.50
        r'([A-Za-z][A-Za-z\s\-]{2,25})\s*\.{3,}(\d{1,4}[,.]\d{2})',
        # NOUVEAUX PATTERNS pour améliorer la reconnaissance
        # Format avec € collé: ARTICLE 2.50€
        r'([A-Za-z0-9][A-Za-z0-9\s\-\']{2,}?)\s+(\d{1,4}[,.]\d{2})€',
        # Format avec F comme prix: ARTICLE 2.50F
        r'([A-Za-z0-9][A-Za-z0-9\s\-\']{2,}?)\s+(\d{1,4}[,.]\d{2})F',
        # Format avec quantité entre parenthèses: ARTICLE (1) 2.50
        r'([A-Za-z0-9][A-Za-z0-9\s\-\']{2,}?)\s+\(\s*\d+\s*\)\s+(\d{1,4}[,.]\d{2})',
        # Format avec quantité après étoile: ARTICLE *1 2.50
        r'([A-Za-z0-9][A-Za-z0-9\s\-\']{2,}?)\s*\*\s*\d+\s+(\d{1,4}[,.]\d{2})',
        # Format avec prix après le mot mais avec espace variable
        r'([A-Z][A-Za-z\s]{2,30})\s{1,10}(\d{1,4}[,.]\d{2})\s*$',
        # Format avec prix au format français 1 234,56
        r'([A-Za-z0-9][A-Za-z0-9\s\-\']+?)\s+(\d{1,3}\s\d{3},\d{2})',
        # Format avec prix après des tirets
        r'([A-Za-z0-9][A-Za-z0-9\s\-\']+?)\s+-+\s*(\d{1,4}[,.]\d{2})',
        # Format Lidl spécifique: ARTICL 2.50 A
        r'([A-Z][A-Za-z\s]{2,20})\s+(\d{1,4}[,.]\d{2})\s+[A-Z]$',
        # Format Super U spécifique
        r'([A-Za-z][A-Za-z\s\-]{2,25})\s+\d{1,4}\s+[,.]\s*(\d{2})',
        # Format très court: ART 2.50 (pour articles tronqués)
        r'([A-Z]{1,4})\s+(\d{1,4}[,.]\d{2})',
        # Format avec prix collé au nom (sans espace): BANANE2.50
        r'([A-Za-z]{3,})(\d{1,4}[,.]\d{2})\b',
        # Format avec espace insécable ou tab: ARTICLE\t2.50
        r'([A-Za-z][A-Za-z\s\-]{2,30})\s+[\t\xa0]+(\d{1,4}[,.]\d{2})',
        # Format avec caractères spéciaux comme séparateurs: ARTICLE | 2.50
        r'([A-Za-z][A-Za-z\s\-]{2,30})\s*[|\\/]\s*(\d{1,4}[,.]\d{2})',
        # Format avec prix au début: 2.50 ARTICLE (pour certains tickets inversés)
        r'(\d{1,4}[,.]\d{2})\s+([A-Za-z][A-Za-z\s\-]{2,30})',
        # Format avec lettre après prix: ARTICLE 2.50A
        r'([A-Za-z][A-Za-z\s\-]{2,25})\s+(\d{1,4}[,.]\d{2})[A-Z]$',
        # NOUVEAUX PATTERNS pour tickets denses
        # Format: ARTICLE 12,50 (virgule française)
        r'([A-Za-z][A-Za-z\s\-]{2,40})\s+(\d{1,4},\d{2})\s*$',
        # Format: 1234567 ARTICLE 2.50 (code 7 chiffres)
        r'\d{7}\s+([A-Za-z][A-Za-z\s\-]{2,30})\s+(\d{1,4}[,.]\d{2})',
        # Format: ARTICLE 2.50 EUR
        r'([A-Za-z][A-Za-z\s\-]{2,30})\s+(\d{1,4}[,.]\d{2})\s*(?:EUR|EURO|€)',
        # Format: PRIX ARTICLE (ticket inversé sans €)
        r'(\d{1,4}[,.]\d{2})\s+([A-Za-z][A-Za-z\s\-]{3,40})$',
    ]
    
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne or len(ligne) < 2:  # Réduit pour capturer plus de lignes
            continue
            
        ligne_lower = ligne.lower()
        
        # Ignorer les lignes qui contiennent des mots exclus
        if any(mot in ligne_lower for mot in mots_exclus):
            continue
        
        # Ignorer les lignes trop longues (augmenté à 120 pour capturer plus)
        if len(ligne) > 120:
            continue
        
        # FILTRAGE: Ignorer les lignes qui ressemblent à des codes (trop de chiffres, peu de lettres)
        lettres_count = len(re.findall(r'[A-Za-z]', ligne))
        chiffres_count = len(re.findall(r'\d', ligne))
        # Si plus de chiffres que de lettres et moins de 5 lettres, c'est probablement un code
        if chiffres_count > lettres_count and lettres_count < 5:
            continue
        # Ignorer les lignes qui sont principalement des codes alphanumériques
        if re.match(r'^[A-Z]{2,4}\s+\d{2,4}', ligne):  # Ex: PRBS 199, SN 123
            continue
        
        # Détection spéciale: prix collé au nom sans espace (ex: BANANE2.50)
        # Chercher un motif lettres suivies directement de chiffres.prix
        match_collé = re.search(r'([A-Za-z]{2,})(\d{1,3}[,.]\d{2})\b', ligne)
        if match_collé:
            article_brut = match_collé.group(1)
            prix_str = match_collé.group(2).replace(',', '.')
            try:
                prix = float(prix_str)
                if 0 < prix < 3000:
                    article = nettoyer_nom_article(article_brut)
                    # Validation renforcée: minimum 3 caractères, au moins 2 lettres
                    if len(article) >= 3 and len(re.findall(r'[A-Za-z]', article)) >= 2:
                        articles[article] = prix
                        continue  # Passer à la ligne suivante
            except ValueError:
                pass
            
        # Essayer chaque pattern standard
        for pattern in patterns:
            match = re.search(pattern, ligne, re.IGNORECASE)
            if match:
                article_brut = match.group(1).strip()
                
                # Gérer les patterns avec 2 ou 3 groupes (prix avec séparateur espacé)
                if len(match.groups()) >= 3 and match.group(3):
                    # Format: ARTICLE 1 , 20 ou ARTICLE 1 . 20
                    prix_str = match.group(2) + '.' + match.group(3)
                else:
                    prix_str = match.group(2).replace(',', '.')
                
                try:
                    prix = float(prix_str)
                    
                    # Validation du prix (allégée)
                    if prix <= 0 or prix > 3000:  # Prix impossible
                        continue
                    
                    # Nettoyer le nom de l'article
                    article = nettoyer_nom_article(article_brut)
                    
                    # Validation renforcée du nom
                    if len(article) < 3:  # Minimum 3 caractères
                        continue
                    if len(article) > 80:  # Maximum 80 caractères
                        continue
                    lettres_article = len(re.findall(r'[A-Za-z]', article))
                    if lettres_article < 2:  # Au moins 2 lettres
                        continue
                    if re.match(r'^\d+$', article):  # Que des chiffres
                        continue
                    # Ignorer les articles qui ressemblent à des codes
                    if re.match(r'^[A-Z]{2,4}$', article):  # Ex: SN, PRBS
                        continue
                    
                    articles[article] = prix
                    break  # Sortir de la boucle des patterns si match trouvé
                    
                except ValueError:
                    continue
    
    return articles

def parser_ticket_multiligne(texte_ocr):
    """Parse les tickets où l'article est sur une ligne et le prix sur la suivante."""
    articles = {}
    lignes = texte_ocr.split('\n')
    
    # Pattern pour détecter juste un prix (ligne avec seulement un prix)
    pattern_prix_seul = r'^\s*(\d{1,4}[,.]\d{2})\s*[€Ff]?\s*$'
    # Pattern pour détecter un article sans prix (nom seul)
    pattern_article_seul = r'^\s*([A-Za-z][A-Za-z0-9\s\-\'\.]{2,40})\s*$'
    
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if not ligne:
            continue
            
        # Vérifier si cette ligne contient juste un prix
        match_prix = re.search(pattern_prix_seul, ligne)
        if match_prix:
            # Regarder la ligne précédente pour trouver le nom de l'article
            if i > 0:
                ligne_precedente = lignes[i-1].strip()
                match_article = re.search(pattern_article_seul, ligne_precedente)
                if match_article:
                    article_brut = match_article.group(1).strip()
                    prix_str = match_prix.group(1).replace(',', '.')
                    try:
                        prix = float(prix_str)
                        if 0 < prix < 3000:
                            article = nettoyer_nom_article(article_brut)
                            if len(article) >= 2:
                                articles[article] = prix
                    except ValueError:
                        continue
    
    return articles

def parser_ticket_avec_quantite(texte_ocr):
    """Parse le texte OCR en détectant aussi les quantités."""
    articles = {}
    lignes = texte_ocr.split('\n')
    
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne:
            continue
            
        # Pattern pour détecter quantité: ARTICLE x2 5.40 ou ARTICLE (x2) 5.40
        pattern_qty = r'([A-Za-z][A-Za-z\s\-\'\.]+?)\s*(?:x\s*(\d+)|\(\s*x?\s*(\d+)\s*\))?\s*(\d+[,.]\d{2})\s*[€]?'
        match = re.search(pattern_qty, ligne, re.IGNORECASE)
        
        if match:
            article_brut = match.group(1).strip()
            quantite = int(match.group(2) or match.group(3) or 1)
            prix_total_str = match.group(4).replace(',', '.')
            
            try:
                prix_total = float(prix_total_str)
                prix_unitaire = prix_total / quantite if quantite > 1 else prix_total
                
                article = nettoyer_nom_article(article_brut)
                if len(article) >= 3:
                    articles[article] = {
                        'prix_unitaire': round(prix_unitaire, 2),
                        'prix_total': prix_total,
                        'quantite': quantite
                    }
            except ValueError:
                continue
    
    return articles if articles else parser_ticket(texte_ocr)

def afficher_resultat_ocr(texte_ocr, articles_extraits):
    """Formate le résultat pour affichage."""
    magasin_detecte = detecter_magasin(texte_ocr)
    
    resultat = {
        "texte_brut": texte_ocr,
        "magasin_detecte": magasin_detecte,
        "articles_trouves": articles_extraits,
        "nombre_articles": len(articles_extraits)
    }
    return resultat

# =============================================================================
# FONCTIONS INTELLIGENTES OCR
# =============================================================================

def corriger_orthographe(nom_article):
    """Corrige l'orthographe d'un article en utilisant le dictionnaire."""
    nom_lower = nom_article.lower().strip()
    
    # Recherche directe
    if nom_lower in CORRECTIONS_ARTICLES:
        return nom_lower
    
    # Recherche inverse (si le nom est une erreur connue)
    for correct, erreurs in CORRECTIONS_ARTICLES.items():
        if nom_lower in erreurs:
            return correct
    
    # Recherche fuzzy (similarité > 80%)
    meilleur_match = None
    meilleur_score = 0.8
    
    for correct in CORRECTIONS_ARTICLES.keys():
        score = SequenceMatcher(None, nom_lower, correct).ratio()
        if score > meilleur_score:
            meilleur_score = score
            meilleur_match = correct
    
    return meilleur_match if meilleur_match else nom_article

def regrouper_articles_similaires(articles):
    """Regroupe les articles similaires (ex: 'pomme' et 'pommes')."""
    articles_groupes = {}
    
    for nom, prix in articles.items():
        nom_corrige = corriger_orthographe(nom)
        nom_lower = nom_corrige.lower()
        
        # Normaliser les pluriels
        if nom_lower.endswith('s') and len(nom_lower) > 3:
            nom_singulier = nom_lower[:-1]
        else:
            nom_singulier = nom_lower
        
        # Chercher si un article similaire existe déjà
        trouve = False
        for existant in list(articles_groupes.keys()):
            existant_lower = existant.lower()
            
            # Même nom ou très similaire
            if nom_singulier == existant_lower or \
               nom_singulier == existant_lower[:-1] if existant_lower.endswith('s') else False:
                # Garder le prix le plus bas (meilleure offre)
                if prix < articles_groupes[existant]:
                    articles_groupes[nom_corrige] = prix
                    del articles_groupes[existant]
                trouve = True
                break
        
        if not trouve:
            articles_groupes[nom_corrige] = prix
    
    return articles_groupes

def extraire_date_ticket(texte_ocr):
    """Extrait la date du ticket de caisse."""
    patterns_date = [
        r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b',  # DD/MM/YYYY ou DD-MM-YYYY
        r'\b(\d{2})[/-](\d{2})[/-](\d{2})\b',   # DD/MM/YY ou DD-MM-YY
        r'\b(\d{4})[/-](\d{2})[/-](\d{2})\b',   # YYYY/MM/DD
        r'(\d{2})\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})',
        r'(\d{2})\s*(jan|fev|mar|avr|mai|juin|juil|aout|sept|oct|nov|dec)\s*(\d{4})',
    ]
    
    mois_fr = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
        'juillet': 7, 'août': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12,
        'jan': 1, 'fev': 2, 'mar': 3, 'avr': 4, 'mai': 5, 'juin': 6,
        'juil': 7, 'aout': 8, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    texte_lower = texte_ocr.lower()
    
    for pattern in patterns_date:
        match = re.search(pattern, texte_lower)
        if match:
            try:
                if 'janvier' in texte_lower or 'février' in texte_lower or any(m in texte_lower for m in mois_fr.keys()):
                    # Format avec mois en lettres
                    jour = int(match.group(1))
                    mois_str = match.group(2)
                    annee = int(match.group(3))
                    mois = mois_fr.get(mois_str, 1)
                    return f"{jour:02d}/{mois:02d}/{annee}"
                else:
                    # Format numérique
                    groups = match.groups()
                    if len(groups[2]) == 4:  # YYYY
                        return f"{groups[0]}/{groups[1]}/{groups[2]}"
                    else:  # YY
                        annee = int(groups[2])
                        annee_complet = 2000 + annee if annee < 50 else 1900 + annee
                        return f"{groups[0]}/{groups[1]}/{annee_complet}"
            except (ValueError, IndexError):
                continue
    
    return None

def extraire_total_ticket(texte_ocr):
    """Extrait le montant total du ticket."""
    patterns_total = [
        r'total\s*:?\s*(\d+[,.]\d{2})',
        r'total\s+ttc\s*:?\s*(\d+[,.]\d{2})',
        r'ttc\s*:?\s*(\d+[,.]\d{2})',
        r'\btotal\b.*?\d{1,4}[,.]\d{2}.*?\n',
        r'montant\s*total\s*:?\s*(\d+[,.]\d{2})',
    ]
    
    texte_lower = texte_ocr.lower()
    
    for pattern in patterns_total:
        match = re.search(pattern, texte_lower, re.IGNORECASE)
        if match:
            try:
                # Chercher tous les nombres dans la ligne matched
                prix_trouves = re.findall(r'(\d+[,.]\d{2})', match.group(0))
                if prix_trouves:
                    # Prendre le plus grand (généralement le total)
                    prix_numeriques = [float(p.replace(',', '.')) for p in prix_trouves]
                    return max(prix_numeriques)
            except (ValueError, IndexError):
                continue
    
    return None

def analyser_qualite_image(image):
    """Analyse la qualité de l'image pour l'OCR."""
    img = image.convert('L')
    
    # Calculer la netteté (variance du Laplacien approximée)
    img_array = list(img.getdata())
    
    # Calculer le contraste
    min_val = min(img_array)
    max_val = max(img_array)
    contraste = max_val - min_val
    
    # Taille de l'image
    width, height = img.size
    resolution = width * height
    
    # Score global
    score = 0
    messages = []
    
    if contraste < 50:
        messages.append("⚠️ Contraste faible - Essayez d'améliorer l'éclairage")
        score += 1
    elif contraste > 200:
        score += 3
    else:
        score += 2
    
    if resolution < 500000:  # < 0.5 MP
        messages.append("⚠️ Résolution faible - Approchez l'appareil du ticket")
        score += 1
    elif resolution > 2000000:  # > 2 MP
        score += 3
    else:
        score += 2
    
    qualite = "Bonne" if score >= 5 else "Moyenne" if score >= 3 else "Faible"
    
    return {
        "qualite": qualite,
        "score": score,
        "contraste": contraste,
        "resolution": f"{width}x{height}",
        "messages": messages
    }

def parser_ticket_intelligent(texte_ocr=None, image=None):
    """Version intelligente du parser avec corrections et améliorations."""
    # Analyser la qualité si l'image est fournie
    qualite_info = None
    if image:
        qualite_info = analyser_qualite_image(image)
        # Extraire le texte uniquement si non fourni
        if texte_ocr is None:
            texte_ocr = extraire_texte_ticket(image)
    
    # Si pas de texte ou texte None, retourner un résultat vide
    if not texte_ocr or texte_ocr.startswith("Erreur"):
        return {
            "articles": {},
            "magasin": None,
            "date": None,
            "total_detecte": None,
            "total_calcule": 0.0,
            "qualite_image": qualite_info,
            "nombre_articles": 0
        }
    
    # Vérifier que texte_ocr n'est pas None (sécurité supplémentaire)
    if texte_ocr is None:
        texte_ocr = ""
    
    # Parser les articles avec plusieurs méthodes
    articles = parser_ticket(texte_ocr)
    
    # Si peu d'articles trouvés, essayer le parser avec quantité
    if len(articles) < 2:
        articles_qty = parser_ticket_avec_quantite(texte_ocr)
        if isinstance(articles_qty, dict):
            # Convertir format quantité en format simple si nécessaire
            for nom, data in articles_qty.items():
                if isinstance(data, dict) and 'prix_total' in data:
                    articles[nom] = data['prix_total']
                elif isinstance(data, (int, float)):
                    articles[nom] = data
    
    # Essayer le parser multi-ligne pour les tickets avec article/prix sur lignes séparées
    if len(articles) < 2:
        articles_multi = parser_ticket_multiligne(texte_ocr)
        if articles_multi:
            articles.update(articles_multi)
    
    # Corriger l'orthographe
    articles_corriges = {}
    for nom, prix in articles.items():
        nom_corrige = corriger_orthographe(nom)
        articles_corriges[nom_corrige] = prix
    
    # Regrouper les articles similaires
    articles_groupes = regrouper_articles_similaires(articles_corriges)
    
    # Extraire les métadonnées
    magasin = detecter_magasin(texte_ocr)
    date_ticket = extraire_date_ticket(texte_ocr)
    total = extraire_total_ticket(texte_ocr)
    
    # Calculer le total détecté
    total_calcule = sum(articles_groupes.values())
    
    return {
        "articles": articles_groupes,
        "magasin": magasin,
        "date": date_ticket,
        "total_detecte": total,
        "total_calcule": round(total_calcule, 2),
        "qualite_image": qualite_info,
        "nombre_articles": len(articles_groupes)
    }
