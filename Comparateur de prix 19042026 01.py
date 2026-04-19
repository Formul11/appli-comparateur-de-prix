



import streamlit as st
import json
import re
from pathlib import Path
from datetime import datetime
from modules.panier import charger_panier, sauvegarder_panier, lister_paniers, supprimer_panier
from modules.analyse import calculer_totaux, analyse_ecarts
from modules.graphiques import graphique_totaux, graphique_ecarts
# Make OCR optional - app works without Tesseract
try:
    from modules.ocr_ticket import extraire_texte_ticket, parser_ticket_intelligent, detecter_magasin
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    extraire_texte_ticket = parser_ticket_intelligent = detecter_magasin = None

st.set_page_config(page_title="Comparateur de prix", layout="wide")

st.title("🛒 Comparateur de prix PRO")

magasins = []

# Charger les magasins personnalisés sauvegardés
def charger_magasins_personnalises():
    """Charge les magasins personnalisés depuis le fichier de configuration."""
    config_file = Path("config_magasins.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("magasins_personnalises", [])
    return []

def charger_magasins_exclus():
    """Charge les magasins exclus depuis le fichier de configuration."""
    config_file = Path("config_magasins.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("magasins_exclus", [])
    return []

def sauvegarder_magasins_personnalises(magasins_perso):
    """Sauvegarde les magasins personnalisés."""
    config_file = Path("config_magasins.json")
    exclus = st.session_state.get("magasins_exclus", [])
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({"magasins_personnalises": magasins_perso, "magasins_exclus": exclus}, f, indent=2)

def sauvegarder_magasins_exclus():
    """Sauvegarde les magasins exclus."""
    config_file = Path("config_magasins.json")
    magasins_perso = st.session_state.get("magasins_personnalises", [])
    exclus = st.session_state.get("magasins_exclus", [])
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({"magasins_personnalises": magasins_perso, "magasins_exclus": exclus}, f, indent=2)

def get_all_magasins():
    """Retourne la liste complète des magasins (personnalisés uniquement - exclus)."""
    magasins_perso = charger_magasins_personnalises()
    # Récupérer les magasins exclus depuis session_state si disponible
    exclus = st.session_state.get("magasins_exclus", [])
    # Filtrer les exclus et normaliser
    seen = set()
    result = []
    for mag in magasins_perso:
        if mag and mag not in exclus:  # Vérifier exclusion avant normalisation
            mag_lower = mag.lower()
            if mag_lower not in seen:
                seen.add(mag_lower)
                result.append(mag)
    return result

# Initialiser les magasins personnalisés et exclus dans session_state
if "magasins_personnalises" not in st.session_state:
    st.session_state.magasins_personnalises = charger_magasins_personnalises()
if "magasins_exclus" not in st.session_state:
    # Charger les magasins exclus depuis le fichier
    st.session_state.magasins_exclus = charger_magasins_exclus()

# Fusionner pour obtenir tous les magasins disponibles
magasins = get_all_magasins()

# Gestion du panier courant
if "nom_panier_courant" not in st.session_state:
    st.session_state.nom_panier_courant = "defaut"

# Charger le panier courant
def charger_panier_courant():
    return charger_panier(st.session_state.nom_panier_courant)

panier = charger_panier_courant()

# =====================================================
# SECTION IMPORT OCR - EN HAUT DE PAGE
# =====================================================
with st.container(border=True):
    st.subheader("📸 Scanner ticket de caisse")
    
    uploaded_file_top = st.file_uploader(
        "Prenez une photo de votre ticket de caisse",
        type=['png', 'jpg', 'jpeg'],
        help="Téléchargez une image claire de votre ticket pour extraction automatique des articles",
        key="uploaded_file_top"
    )
    
    # Stocker dans session_state
    if uploaded_file_top is not None:
        st.session_state.uploaded_file = uploaded_file_top

# -------------------------------------------------------
# TRAITEMENT OCR DU TICKET (juste sous l'import)
# -------------------------------------------------------
if st.session_state.get("uploaded_file") is not None:
    st.subheader("🔍 Traitement OCR du ticket")
    
    uploaded_file = st.session_state.uploaded_file
    
    from PIL import Image
    import io
    
    image = Image.open(io.BytesIO(uploaded_file.getvalue()))
    
    # Afficher l'image centrée dans un cadre blanc + bouton fermer
    col_img_left, col_img_center, col_img_right = st.columns([1, 3, 1])
    with col_img_center:
        with st.container():
            st.markdown("""
                <style>
                .stContainer { background-color: white; padding: 20px; border-radius: 10px; }
                </style>
            """, unsafe_allow_html=True)
            st.image(image, caption="Ticket de caisse", use_container_width=True)
    
    with col_img_right:
        st.caption("")
        if st.button("❌ Fermer", key="btn_fermer_ticket", help="Supprimer le ticket"):
            # Supprimer le ticket de session_state
            if "uploaded_file" in st.session_state:
                del st.session_state.uploaded_file
            if "articles_ocr" in st.session_state:
                del st.session_state.articles_ocr
            if "texte_ocr" in st.session_state:
                del st.session_state.texte_ocr
            st.rerun()
    
    # Initialiser session_state pour stocker les articles extraits
    if "articles_ocr" not in st.session_state:
        st.session_state.articles_ocr = {}
    if "texte_ocr" not in st.session_state:
        st.session_state.texte_ocr = ""
    
    # Option mode debug
    mode_debug = st.checkbox("🔧 Mode debug (voir le texte brut)", value=False)
    
    if st.button("🔍 Extraire les articles"):
        if not OCR_AVAILABLE:
            st.error("❌ OCR non disponible - Tesseract non installé")
            st.warning("""
            **Pour installer Tesseract OCR:**
            1. Téléchargez: https://github.com/UB-Mannheim/tesseract/wiki
            2. Installez et notez le chemin (ex: C:\\Program Files\\Tesseract-OCR)
            3. Ajoutez au PATH Windows ou configurez pytesseract.pytesseract.tesseract_cmd
            """)
            st.info("💡 En attendant, utilisez la saisie manuelle ci-dessous 👇")
            
            # Activer la saisie manuelle automatiquement
            st.session_state.ocr_manuel_actif = True
        else:
            with st.spinner("Analyse OCR en cours..."):
                texte_brut = extraire_texte_ticket(image)
                st.session_state.texte_ocr = texte_brut
                resultat_ocr = parser_ticket_intelligent(texte_brut, image)
            
            st.session_state.ocr_resultat = resultat_ocr
            st.session_state.articles_ocr = resultat_ocr["articles"]
            st.session_state.magasin_detecte = resultat_ocr["magasin"]
            st.session_state.date_ticket = resultat_ocr["date"]
            
            if resultat_ocr["qualite_image"]:
                qualite = resultat_ocr["qualite_image"]
                if qualite["qualite"] == "Faible":
                    st.warning(f"📸 Qualité: **{qualite['qualite']}** | " + " | ".join(qualite["messages"]))
                else:
                    st.info(f"📸 Qualité: **{qualite['qualite']}** ({qualite['resolution']})")
            
            if st.session_state.articles_ocr:
                mag_info = f" | 🏬 {st.session_state.magasin_detecte}" if st.session_state.magasin_detecte else ""
                date_info = f" | 📅 {st.session_state.date_ticket}" if st.session_state.date_ticket else ""
                st.success(f"✅ {resultat_ocr['nombre_articles']} articles trouvés !{mag_info}{date_info}")
                
                if resultat_ocr["total_detecte"]:
                    diff = abs(resultat_ocr["total_detecte"] - resultat_ocr["total_calcule"])
                    if diff < 1.0:
                        st.caption(f"💰 Total: **{resultat_ocr['total_detecte']:.2f}€** ✓")
                    else:
                        st.caption(f"💰 Total: {resultat_ocr['total_detecte']:.2f}€ | Calculé: {resultat_ocr['total_calcule']:.2f}€")
            else:
                st.error("❌ Aucun article trouvé. Utilisez une image bien éclairée.")
                if mode_debug and texte_brut:
                    with st.expander("📋 Texte OCR brut", expanded=True):
                        st.text(texte_brut)
    
    # Section saisie manuelle (visible si OCR indisponible ou si l'utilisateur veut ajouter manuellement)
    if not OCR_AVAILABLE or st.session_state.get("ocr_manuel_actif"):
        st.subheader("✏️ Saisie manuelle depuis le ticket")
        st.caption("Entrez les articles que vous voyez sur le ticket")
        
        col_man1, col_man2, col_man3 = st.columns([3, 1, 1])
        with col_man1:
            article_manuel = st.text_input("Nom de l'article", placeholder="ex: Pain de mie", key="article_manuel")
        with col_man2:
            prix_manuel = st.number_input("Prix (€)", min_value=0.0, step=0.01, key="prix_manuel")
        with col_man3:
            magasin_manuel = st.selectbox("Magasin", sorted(magasins), key="magasin_manuel")
        
        if st.button("➕ Ajouter cet article", key="btn_ajout_manuel_ticket"):
            if article_manuel and prix_manuel > 0:
                # Créer ou mettre à jour l'article dans le panier
                if article_manuel not in panier:
                    panier[article_manuel] = {m: 0.0 for m in magasins}
                panier[article_manuel][magasin_manuel] = prix_manuel
                if "_dates" not in panier[article_manuel]:
                    panier[article_manuel]["_dates"] = {}
                from datetime import date
                panier[article_manuel]["_dates"][magasin_manuel] = date.today().isoformat()
                sauvegarder_panier(panier, st.session_state.nom_panier_courant)
                st.success(f"✅ '{article_manuel}' ajouté ({magasin_manuel}: {prix_manuel:.2f}€)")
                st.rerun()
            else:
                st.error("Veuillez entrer un nom d'article et un prix")
        
        st.divider()
    
    # Articles extraits
    if st.session_state.articles_ocr:
        st.subheader("Articles détectés :")
        
        col_global, col_info = st.columns([1, 2])
        with col_global:
            magasin_global = st.selectbox(
                "🏬 Magasin",
                sorted(magasins),
                index=sorted(magasins).index(magasins[0]) if magasins else 0,
                key="magasin_global_ocr"
            )
        with col_info:
            if st.session_state.get("magasin_detecte"):
                st.caption(f"✓ Auto-détecté: **{st.session_state.magasin_detecte}**")
        
        if "magasins_selection" not in st.session_state:
            st.session_state.magasins_selection = {}
        
        for nom_article in st.session_state.articles_ocr.keys():
            st.session_state.magasins_selection[nom_article] = magasin_global
        
        for nom_article, prix in st.session_state.articles_ocr.items():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                nom_edite = st.text_input(
                    "Article",
                    value=nom_article,
                    key=f"edit_{nom_article}",
                    label_visibility="collapsed"
                )
                if nom_edite != nom_article:
                    st.session_state.articles_ocr[nom_edite] = st.session_state.articles_ocr.pop(nom_article)
            with col2:
                st.write(f"{prix:.2f} €")
            with col3:
                st.write(f"*{magasin_global}*")
            with col4:
                if st.button("�️", key=f"del_ocr_{nom_article}"):
                    del st.session_state.articles_ocr[nom_article]
                    st.rerun()
        
        if st.button("➕ Ajouter tous les articles au panier"):
            for nom_article, prix in st.session_state.articles_ocr.items():
                prix_pour_magasins = {m: 0.0 for m in magasins}
                magasin_choisi = st.session_state.magasins_selection.get(nom_article, magasins[0] if magasins else "")
                prix_pour_magasins[magasin_choisi] = prix
                panier[nom_article] = prix_pour_magasins
            
            sauvegarder_panier(panier, st.session_state.nom_panier_courant)
            st.success(f"🎉 {len(st.session_state.articles_ocr)} articles ajoutés !")
            st.session_state.articles_ocr = {}
            st.session_state.magasins_selection = {}
            st.rerun()

# =====================================================
# SECTION SCANNER CODE-BARRES - EN HAUT DE PAGE
# =====================================================
with st.container(border=True):
    st.subheader("📱 Scanner code-barres")
    
    # Base de données de codes-barres (simulation)
    DB_CODE_BARRES_TOP = {
        "1234567890123": {"nom": "Pommes Golden", "categorie": "Fruits", "prix_reference": 2.50},
        "1234567890124": {"nom": "Bananes", "categorie": "Fruits", "prix_reference": 1.80},
        "1234567890125": {"nom": "Carottes", "categorie": "Légumes", "prix_reference": 1.20},
        "1234567890126": {"nom": "Tomates", "categorie": "Légumes", "prix_reference": 2.80},
        "1234567890127": {"nom": "Lait Entier", "categorie": "Produits Laitiers", "prix_reference": 1.15},
        "1234567890128": {"nom": "Yaourt Nature", "categorie": "Produits Laitiers", "prix_reference": 2.10},
        "1234567890129": {"nom": "Fromage Comté", "categorie": "Fromage", "prix_reference": 18.50},
        "1234567890130": {"nom": "Pain de campagne", "categorie": "Boulangerie", "prix_reference": 2.20},
        "1234567890131": {"nom": "Baguette", "categorie": "Boulangerie", "prix_reference": 1.10},
        "1234567890132": {"nom": "Riz Basmati", "categorie": "Épicerie", "prix_reference": 3.50},
        "1234567890133": {"nom": "Pâtes Penne", "categorie": "Épicerie", "prix_reference": 1.45},
        "1234567890134": {"nom": "Huile d'olive", "categorie": "Épicerie", "prix_reference": 6.80},
        "1234567890135": {"nom": "Sucre", "categorie": "Épicerie", "prix_reference": 1.60},
        "1234567890136": {"nom": "Eau minérale", "categorie": "Boissons", "prix_reference": 0.50},
        "1234567890137": {"nom": "Jus d'orange", "categorie": "Boissons", "prix_reference": 2.30},
        "1234567890138": {"nom": "Café moulu", "categorie": "Boissons", "prix_reference": 4.50},
    }
    
    col_scan1_top, col_scan2_top, col_scan3_top = st.columns([2, 1, 1])
    
    with col_scan1_top:
        if "code_barres_scan_top" not in st.session_state:
            st.session_state.code_barres_scan_top = ""
        
        code_barres_top = st.text_input(
            "Saisir un code-barres",
            placeholder="Ex: 1234567890123",
            value=st.session_state.code_barres_scan_top,
            key="code_barres_input_top",
            help="Entrez le code-barres du produit (13 chiffres)"
        )
        st.session_state.code_barres_scan_top = code_barres_top
    
    with col_scan2_top:
        if st.button("🔍 Rechercher", key="btn_scan_top", type="primary"):
            st.session_state.rechercher_code = code_barres_top
    
    with col_scan3_top:
        if st.button("📷 Simuler scan", key="btn_camera_top", help="Simuler un scan"):
            import random
            code_scanne = random.choice(list(DB_CODE_BARRES_TOP.keys()))
            st.session_state.code_barres_scan_top = code_scanne
            st.session_state.rechercher_code = code_scanne
            st.rerun()
    
    # Afficher le résultat si recherche demandée
    if st.session_state.get("rechercher_code") and st.session_state.rechercher_code in DB_CODE_BARRES_TOP:
        produit = DB_CODE_BARRES_TOP[st.session_state.rechercher_code]
        st.success(f"✅ {produit['nom']} - Prix réf: {produit['prix_reference']:.2f}€")
        
        # Vérifier si le produit existe dans le panier
        prix_trouves = {}
        for article, prix_saisis in panier.items():
            if article.lower() == produit['nom'].lower() or produit['nom'].lower() in article.lower():
                for mag, prix in prix_saisis.items():
                    if not mag.startswith("_") and isinstance(prix, (int, float)) and prix > 0:
                        prix_trouves[mag] = prix
        
        if prix_trouves:
            meilleur = min(prix_trouves.items(), key=lambda x: x[1])
            st.info(f"🏆 Meilleur prix trouvé: {meilleur[0]} à {meilleur[1]:.2f}€")
        else:
            st.caption("💡 Produit non encore dans vos paniers. Ajoutez-le manuellement ci-dessous.")
        
        # Réinitialiser pour éviter affichage persistant
        st.session_state.rechercher_code = None

# =====================================================
# Sidebar pour la gestion des paniers
with st.sidebar:
    paniers_existants = lister_paniers()
    
    # Toujours revenir sur le panier le plus récent (premier de la liste triée par date)
    # sauf si l'utilisateur a explicitement sélectionné un autre panier
    if paniers_existants and st.session_state.nom_panier_courant not in paniers_existants:
        st.session_state.nom_panier_courant = paniers_existants[0]
    
    # Gestion des paniers - affichage direct dans la sidebar avec cadre unique
    with st.container(border=True):
        st.subheader("📁 Gestion paniers")
        st.caption(f"Panier actuel: **{st.session_state.nom_panier_courant}**")
        
        # Ajouter les options de création et suppression en haut de la liste
        options_paniers = ["➕ Créer panier", "🗑️ Supprimer panier"] + paniers_existants
        
        # Déterminer l'index : utiliser le panier courant s'il existe, sinon le premier panier (plus récent)
        if st.session_state.nom_panier_courant in options_paniers:
            current_index = options_paniers.index(st.session_state.nom_panier_courant)
        elif paniers_existants:
            # Sélectionner le premier panier (plus récent) par défaut
            current_index = options_paniers.index(paniers_existants[0])
            st.session_state.nom_panier_courant = paniers_existants[0]
        else:
            current_index = 0
        
        panier_selectionne = st.selectbox(
            "Sélectionner un panier",
            options_paniers,
            index=current_index,
            key="select_panier",
            label_visibility="collapsed"
        )
        
        # Gestion de la sélection
        if panier_selectionne == "➕ Créer panier":
            st.session_state.show_create_panier = True
            st.session_state.show_delete_panier = False
        elif panier_selectionne == "🗑️ Supprimer panier":
            st.session_state.show_delete_panier = True
            st.session_state.show_create_panier = False
        elif panier_selectionne != st.session_state.nom_panier_courant:
            st.session_state.nom_panier_courant = panier_selectionne
            st.session_state.show_create_panier = False
            st.session_state.show_delete_panier = False
            st.rerun()
        
        # Afficher le formulaire de création uniquement si l'option est sélectionnée
        if st.session_state.get("show_create_panier") and panier_selectionne == "➕ Créer panier":
            nouveau_nom = st.text_input("Nom du panier", placeholder="Nom du nouveau panier...", key="new_panier_name_form", label_visibility="collapsed")
            if st.button("✓ Créer", key="btn_creer", use_container_width=True, type="primary"):
                if nouveau_nom and nouveau_nom.strip():
                    st.session_state.nom_panier_courant = nouveau_nom.strip()
                    sauvegarder_panier({}, nouveau_nom.strip())
                    st.session_state.show_create_panier = False
                    st.success(f"✅ Panier '{nouveau_nom.strip()}' créé !")
                    st.rerun()
                else:
                    st.error("Veuillez entrer un nom.")
        
        # Afficher le formulaire de suppression uniquement si l'option est sélectionnée
        if st.session_state.get("show_delete_panier") and panier_selectionne == "🗑️ Supprimer panier":
            st.markdown("**🗑️ Supprimer panier**")
            if paniers_existants:
                panier_suppr = st.selectbox("Panier à supprimer", paniers_existants, key="panier_suppr", label_visibility="collapsed")
                if st.button("🗑️ Supprimer", key="btn_supprimer", use_container_width=True, type="primary"):
                    if supprimer_panier(panier_suppr):
                        # Si le panier supprimé était le panier courant, basculer vers un autre
                        if st.session_state.nom_panier_courant == panier_suppr:
                            paniers_restants = [p for p in paniers_existants if p != panier_suppr]
                            st.session_state.nom_panier_courant = paniers_restants[0] if paniers_restants else "defaut"
                        st.session_state.show_delete_panier = False
                        st.success(f"🗑️ Panier '{panier_suppr}' supprimé.")
                        st.rerun()
            else:
                st.info("Aucun panier à supprimer.")

st.subheader("📦 Panier actuel")

if panier:
    # Menu déroulant pour actions groupées
    col_action, col_btn = st.columns([2, 1])
    with col_action:
        action_groupe = st.selectbox(
            "Action pour tous les articles",
            ["Sélectionner une action...", "Vider le panier", "Analyser les prix"],
            key="action_groupe_panier"
        )
    with col_btn:
        if action_groupe == "Vider le panier":
            if st.button("🗑️ Confirmer vidage"):
                panier.clear()
                sauvegarder_panier(panier, st.session_state.nom_panier_courant)
                st.success("Panier vidé !")
                st.rerun()
        elif action_groupe == "Analyser les prix":
            if st.button("📊 Analyser"):
                st.session_state.analyser_prix = True
                st.rerun()
    
    # Afficher chaque article avec édition et suppression
    for idx_article, (nom_article, prix_dict) in enumerate(list(panier.items())):
        # Container avec bordure pour chaque article
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 5, 1])
            with col1:
                # Champ éditable pour renommer l'article
                nom_edite = st.text_input(
                    "Article",
                    value=nom_article,
                    key=f"edit_panier_{nom_article}",
                    label_visibility="collapsed"
                )
                # Si le nom a changé, mettre à jour le panier
                if nom_edite != nom_article:
                    panier[nom_edite] = panier.pop(nom_article)
                    sauvegarder_panier(panier, st.session_state.nom_panier_courant)
                    st.rerun()
            with col2:
                # Afficher et permettre l'édition des prix par magasin
                dates_dict = prix_dict.get("_dates", {})
                magasins_prix = [(m, p) for m, p in prix_dict.items() if not m.startswith("_")]
            
            for idx, (mag, prix) in enumerate(magasins_prix):
                try:
                    prix_float = float(prix)
                except (ValueError, TypeError):
                    prix_float = 0.0
                
                if prix_float > 0:
                    cols_prix = st.columns([2, 1, 0.5])
                    with cols_prix[0]:
                        # Selectbox pour changer le magasin - TRIÉE
                        mag_list = [mag] + sorted([m for m in magasins if m != mag])
                        nouveau_mag = st.selectbox(
                            "Magasin",
                            mag_list,
                            index=0,
                            key=f"edit_mag_{nom_article}_{idx}",
                            label_visibility="collapsed"
                        )
                    with cols_prix[1]:
                        # Input pour modifier le prix
                        nouveau_prix = st.number_input(
                            "Prix",
                            value=prix_float,
                            min_value=0.0,
                            step=0.01,
                            format="%.2f",
                            key=f"edit_prix_{nom_article}_{idx}",
                            label_visibility="collapsed"
                        )
                    with cols_prix[2]:
                        # Sous-colonnes pour aligner les boutons suppression et ajout
                        sub_cols = st.columns([1, 1])
                        with sub_cols[0]:
                            # Bouton pour supprimer ce prix/magasin
                            if st.button("🗑️", key=f"del_prix_{nom_article}_{idx}", help="Supprimer ce magasin"):
                                if mag in panier[nom_article]:
                                    del panier[nom_article][mag]
                                    if "_dates" in panier[nom_article] and mag in panier[nom_article]["_dates"]:
                                        del panier[nom_article]["_dates"][mag]
                                    sauvegarder_panier(panier, st.session_state.nom_panier_courant)
                                    st.rerun()
                    
                    # Si le magasin ou le prix a changé
                    if nouveau_mag != mag or nouveau_prix != prix_float:
                        # Récupérer la date avant modification
                        ancienne_date = panier[nom_article].get("_dates", {}).get(mag, "")
                        
                        # Supprimer l'ancienne entrée
                        if mag in panier[nom_article]:
                            del panier[nom_article][mag]
                            if "_dates" in panier[nom_article] and mag in panier[nom_article]["_dates"]:
                                del panier[nom_article]["_dates"][mag]
                        
                        # Ajouter la nouvelle entrée
                        panier[nom_article][nouveau_mag] = nouveau_prix
                        if "_dates" not in panier[nom_article]:
                            panier[nom_article]["_dates"] = {}
                        # Garder l'ancienne date si c'est le même magasin, sinon nouvelle date
                        panier[nom_article]["_dates"][nouveau_mag] = ancienne_date if nouveau_mag == mag else datetime.now().isoformat()
                        
                        sauvegarder_panier(panier, st.session_state.nom_panier_courant)
                        st.rerun()
            
            # Formulaire d'ajout de magasin - HORS DE LA BOUCLE DES PRIX
            # Pour éviter la duplication de clé Streamlit
            show_add_key = f"show_add_form_{nom_article}"
            
            # Initialiser l'état si nécessaire
            if show_add_key not in st.session_state:
                st.session_state[show_add_key] = False
            
            # Bouton pour afficher/masquer le formulaire (après la boucle des prix)
            col_btn_space = st.columns([5, 1])
            with col_btn_space[1]:
                btn_label = "➕ Ajouter" if not st.session_state.get(show_add_key, False) else "➖ Fermer"
                if st.button(btn_label, key=f"btn_toggle_mag_{nom_article}", help="Ajouter un magasin"):
                    st.session_state[show_add_key] = not st.session_state.get(show_add_key, False)
                    st.rerun()
            
            # Afficher le formulaire si l'état est True (en dessous des prix)
            if st.session_state.get(show_add_key, False):
                with st.container(border=True):
                    st.markdown("**➕ Nouveau magasin**")
                    
                    # Magasins disponibles = tous les magasins sauf ceux déjà présents pour cet article
                    # Obtenir la liste des magasins déjà présents (peu importe le prix)
                    magasins_existants = [m.strip() for m in prix_dict.keys() if not m.startswith("_")]
                    # Comparaison insensible à la casse
                    magasins_existants_lower = [m.lower() for m in magasins_existants]
                    magasins_disponibles = [m for m in magasins if m.strip().lower() not in magasins_existants_lower]
                    
                    # Debug: afficher les listes
                    st.caption(f"Magasins existants: {magasins_existants}")
                    st.caption(f"Tous les magasins: {magasins}")
                    st.caption(f"Magasins disponibles: {magasins_disponibles}")
                    
                    # Créer une liste avec seulement les magasins disponibles (pas encore ajoutés) - TRIÉE
                    magasins_select = []
                    
                    # Magasins disponibles triés (pour ajout uniquement - ceux pas encore dans l'article)
                    for m in sorted(magasins_disponibles):
                        magasins_select.append(f"➕ {m}")
                    
                    # Si aucun magasin disponible, afficher un message
                    if not magasins_disponibles:
                        st.info("ℹ️ Tous les magasins sont déjà ajoutés à cet article.")
                    
                    # Créer des clés de session pour stocker les valeurs
                    new_mag_key = f"new_mag_val_{nom_article}"
                    new_prix_key = f"new_prix_val_{nom_article}"
                    
                    col_new1, col_new2 = st.columns([2, 1])
                    with col_new1:
                        new_mag_affiche = st.selectbox(
                            "Magasin",
                            magasins_select,
                            key=f"new_mag_select_{nom_article}"
                        )
                        
                        # Extraire le nom du magasin (format: "➕ Nom")
                        mag_nom = new_mag_affiche[2:].strip()
                        st.session_state[new_mag_key] = mag_nom
                            
                    with col_new2:
                        new_prix = st.number_input(
                            "Prix",
                            value=0.0,
                            min_value=0.0,
                            step=0.01,
                            format="%.2f",
                            key=f"new_prix_{nom_article}"
                        )
                        # Stocker dans session state
                        st.session_state[new_prix_key] = new_prix
                        
                        # Message d'erreur si prix = 0
                        if new_prix <= 0:
                            st.warning("⚠️ Veuillez entrer un prix supérieur à 0")
                    
                    col_btn1, col_btn2 = st.columns([1, 1])
                    with col_btn1:
                        confirm_disabled = new_prix <= 0
                        
                        if st.button("✓ Ajouter", key=f"confirm_new_mag_{nom_article}", type="primary", disabled=confirm_disabled):
                            new_mag_val = st.session_state.get(new_mag_key)
                            new_prix_val = st.session_state.get(new_prix_key)
                            if new_mag_val and new_prix_val > 0:
                                panier[nom_article][new_mag_val] = new_prix_val
                                if "_dates" not in panier[nom_article]:
                                    panier[nom_article]["_dates"] = {}
                                panier[nom_article]["_dates"][new_mag_val] = datetime.now().isoformat()
                                sauvegarder_panier(panier, st.session_state.nom_panier_courant)
                                st.success(f"✅ {new_mag_val} ajouté à {new_prix_val:.2f}€")
                                # Garder le formulaire ouvert pour ajouter d'autres magasins
                                st.rerun()
                    with col_btn2:
                        if st.button("❌ Annuler", key=f"cancel_new_mag_{nom_article}"):
                            st.session_state[show_add_key] = False
                            st.rerun()
                
                if not magasins_prix:
                    st.write("-")
                    
            with col3:
                if st.button("❌", key=f"del_{nom_article}"):
                    del panier[nom_article]
                    sauvegarder_panier(panier, st.session_state.nom_panier_courant)
        
        # Ligne de séparation en bas
        st.divider()

    # Résumé du panier
    total_articles = len(panier)
    st.info(f"📊 {total_articles} article(s) dans le panier")
else:
    st.info("Aucun article dans le panier.")

st.divider()

# Sélection du mode d'analyse
col_analyse1, col_analyse2 = st.columns([2, 1])
with col_analyse1:
    mode_analyse = st.selectbox(
        "Analyser les prix",
        ["Panier actuel", "Tous les paniers (cumulé)"],
        key="mode_analyse"
    )
with col_analyse2:
    analyser_btn = st.button("📊 Analyser", key="btn_analyser")

if analyser_btn or st.session_state.get("analyser_prix", False):
    # Réinitialiser le flag
    st.session_state.analyser_prix = False
    
    # Déterminer quel panier analyser
    if mode_analyse == "Tous les paniers (cumulé)":
        # Charger tous les paniers et les fusionner
        tous_les_paniers = {}
        for nom_p in lister_paniers():
            p = charger_panier(nom_p)
            for article, prix_dict in p.items():
                if article in tous_les_paniers:
                    # Fusionner les prix (prendre le max si différent)
                    for m, prix in prix_dict.items():
                        if prix > 0:
                            if tous_les_paniers[article].get(m, 0) == 0:
                                tous_les_paniers[article][m] = prix
                else:
                    tous_les_paniers[article] = prix_dict.copy()
        panier_a_analyser = tous_les_paniers
        st.info(f"📁 Analyse de **{len(lister_paniers())}** paniers combinés ({len(panier_a_analyser)} articles uniques)")
    else:
        panier_a_analyser = panier
        st.info(f"📁 Analyse du panier **{st.session_state.nom_panier_courant}** ({len(panier_a_analyser)} articles)")
    
    if not panier_a_analyser:
        st.error("Le panier est vide.")
    else:
        totaux = calculer_totaux(panier_a_analyser, magasins)
        ecarts = analyse_ecarts(panier_a_analyser, magasins)

        # Option pour désactiver les graphiques
        afficher_graphiques = st.checkbox("📊 Afficher les graphiques", value=True, key="afficher_graphiques")

        colA, colB = st.columns(2)

        with colA:
            # Vérifier s'il y a des totaux non nuls
            totaux_non_nuls = {mag: total for mag, total in totaux.items() if total > 0}
            
            if totaux_non_nuls:
                st.subheader("🏆 Total par magasin")
                
                # Trier les magasins par prix croissant
                totaux_tries = dict(sorted(totaux_non_nuls.items(), key=lambda x: x[1]))
                magasin_le_moins_cher = min(totaux_tries, key=totaux_tries.get)
                magasin_le_plus_cher = max(totaux_tries, key=totaux_tries.get)
                
                for mag, total in totaux_tries.items():
                    with st.container():
                        col1, col2 = st.columns([2, 3])
                        with col1:
                            if mag == magasin_le_moins_cher:
                                st.markdown(f"🟢 **{mag}**")
                                st.caption("🏆 Moins cher")
                            elif mag == magasin_le_plus_cher:
                                st.markdown(f"🔴 **{mag}**")
                                st.caption("📈 Plus cher")
                            else:
                                st.markdown(f"🟠 **{mag}**")
                        with col2:
                            st.markdown(f"**{total:.2f}€**")
                        st.divider()
                
                if afficher_graphiques:
                    st.plotly_chart(graphique_totaux(totaux_non_nuls), use_container_width=True)
            else:
                st.info("💡 Ajoutez des articles avec des prix pour voir les totaux par magasin.")

        with colB:
            st.subheader("📈 Écarts par article")
            
            if ecarts:
                for article, data in ecarts.items():
                    with st.container():
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**{article}**")
                            st.caption(f"💰 Économie: {data['economie']}%")
                        with col2:
                            st.markdown(
                                f"🟢 **{data['magasin_min']}**: {data['min']:.2f}€  \n"
                                f"🔴 **{data['magasin_max']}**: {data['max']:.2f}€  \n"
                                f"📊 Écart: **{data['ecart']:.2f}€**"
                            )
                        st.divider()
            else:
                st.info("Ajoutez des prix pour plusieurs magasins pour voir les écarts.")
            
            if afficher_graphiques:
                st.plotly_chart(graphique_ecarts(ecarts), use_container_width=True)

        # Afficher le résultat uniquement s'il y a des totaux non nuls
        totaux_non_nuls = {mag: total for mag, total in totaux.items() if total > 0}
        if totaux_non_nuls:
            magasin_min = min(totaux_non_nuls, key=totaux_non_nuls.get)
            st.success(f"🎯 Le magasin le moins cher est **{magasin_min}** avec un total de **{totaux_non_nuls[magasin_min]:.2f} €**.")

# ============================================================
# NOUVELLE FONCTIONNALITÉ: Prédiction du meilleur prix
# ============================================================
st.divider()
st.subheader("🔮 Prédiction : Quel magasin sera le moins cher ?")

# Essayer de charger le modèle ML
try:
    import pandas as pd
    import joblib
    from PIL import Image
    
    # Chargement du modèle
    modele_data = joblib.load("modele_simple.pkl")
    le_magasin = modele_data['le_magasin']
    le_produit = modele_data['le_produit']
    
    # Combiner produits du modèle avec articles du panier
    produits_modele = list(le_produit.classes_)
    articles_panier_pred = list(panier.keys()) if panier else []
    
    # Fusionner sans doublons et trier par ordre alphabétique
    tous_produits = sorted(list(dict.fromkeys(produits_modele + articles_panier_pred)), key=str.lower)
    
    col_pred1, col_pred2 = st.columns(2)
    
    with col_pred1:
        produit_pred = st.selectbox("Produit :", tous_produits, key="pred_produit")
    
    with col_pred2:
        jours_prediction = st.selectbox(
            "Prédiction dans :",
            [7, 14, 30, 60, 90],
            index=2,
            format_func=lambda x: f"{x} jours",
            key="jours_pred"
        )
    
    if st.button("🔮 Prédire le meilleur prix", key="btn_predire"):
        
        # COMPARAISON DES PRIX - Trouver le magasin le moins cher
        st.divider()
        st.markdown("**💰 Où acheter ce produit au meilleur prix ?**")
        
        # Chercher le produit dans le panier courant
        prix_par_magasin = {}
        dates_par_magasin = {}
        historique_prix = {}  # {magasin: [(date, prix), ...]}
        
        for article, prix_saisis in panier.items():
            if article.lower() == produit_pred.lower():
                dates_dict = prix_saisis.get("_dates", {})
                for mag, prix in prix_saisis.items():
                    if not mag.startswith("_") and isinstance(prix, (int, float)) and prix > 0:
                        prix_par_magasin[mag] = prix
                        date_str = dates_dict.get(mag, "Date inconnue")
                        dates_par_magasin[mag] = date_str
                        
                        # Construire l'historique pour la prédiction
                        if mag not in historique_prix:
                            historique_prix[mag] = []
                        if date_str != "Date inconnue":
                            try:
                                from datetime import datetime
                                date_obj = datetime.fromisoformat(date_str)
                                historique_prix[mag].append((date_obj, prix))
                            except:
                                pass
                break
        
        if prix_par_magasin:
            magasin_moins_cher = min(prix_par_magasin, key=prix_par_magasin.get)
            prix_min = prix_par_magasin[magasin_moins_cher]
            date_achat_min = dates_par_magasin.get(magasin_moins_cher, "Date inconnue")
            
            # Formater la date
            if date_achat_min != "Date inconnue":
                from datetime import datetime
                try:
                    date_obj = datetime.fromisoformat(date_achat_min)
                    date_formatee = date_obj.strftime("%d/%m/%Y")
                except:
                    date_formatee = date_achat_min
            else:
                date_formatee = "Date inconnue"
            
            st.success(f"🏆 Meilleur prix pour **{produit_pred}** : **{magasin_moins_cher}** à **{prix_min:.2f} €** (acheté le {date_formatee})")
            
            # Afficher tous les prix connus avec dates
            st.caption("📋 Tous les prix connus :")
            for mag, prix in sorted(prix_par_magasin.items(), key=lambda x: x[1]):
                emoji = "🏆" if mag == magasin_moins_cher else "🛒"
                date_mag = dates_par_magasin.get(mag, "Date inconnue")
                if date_mag != "Date inconnue":
                    try:
                        date_obj = datetime.fromisoformat(date_mag)
                        date_mag = date_obj.strftime("%d/%m/%Y")
                    except:
                        pass
                st.write(f"{emoji} **{mag}**: {prix:.2f} € (le {date_mag})")
            
            # PRÉDICTION FUTURE - Où sera le moins cher dans les jours suivants
            st.divider()
            st.markdown("**🔮 Prédiction: Où sera le moins cher dans les jours suivants ?**")
            
            if len(historique_prix) >= 2:
                # Calculer les tendances
                tendances = {}
                for mag, histo in historique_prix.items():
                    if len(histo) >= 1:
                        # Trier par date
                        histo.sort(key=lambda x: x[0])
                        dernier_prix = histo[-1][1]
                        derniere_date = histo[-1][0]
                        
                        # Calculer la variation moyenne si plusieurs points
                        if len(histo) >= 2:
                            # Calculer la tendance sur les 7 derniers jours ou la période disponible
                            jours_tendance = min(7, len(histo))
                            prix_debut = histo[-jours_tendance][1]
                            prix_fin = dernier_prix
                            nb_jours = (histo[-1][0] - histo[-jours_tendance][0]).days or 1
                            tendance_moy = ((prix_fin - prix_debut) / prix_debut * 100) / nb_jours
                        else:
                            tendance_moy = 0
                        
                        # Calculer les prédictions pour différentes périodes
                        tendances[mag] = {
                            'dernier_prix': dernier_prix,
                            'derniere_date': derniere_date,
                            'tendance': tendance_moy,
                            'predictions': {
                                j: dernier_prix * (1 + tendance_moy/100 * j) 
                                for j in [7, 14, 30, 40, 50, 60, 90]
                            }
                        }
                
                # Trouver le magasin le moins cher prédit pour la période sélectionnée
                if tendances:
                    pred_periode = {mag: data['predictions'][jours_prediction] for mag, data in tendances.items()}
                    magasin_pred = min(pred_periode, key=pred_periode.get)
                    prix_pred = pred_periode[magasin_pred]
                    
                    # Afficher la prédiction principale
                    from datetime import datetime, timedelta
                    date_futur = datetime.now() + timedelta(days=jours_prediction)
                    st.success(f"🔮 **Dans {jours_prediction} jours** (le {date_futur.strftime('%d/%m/%Y')}) : **{magasin_pred}** devrait être le moins cher à **{prix_pred:.2f} €**")
                    
                    # Comparer avec le prix actuel
                    prix_actuel_min = min(data['dernier_prix'] for data in tendances.values())
                    magasin_actuel = min(tendances.keys(), key=lambda x: tendances[x]['dernier_prix'])
                    
                    if prix_pred < prix_actuel_min:
                        economie = prix_actuel_min - prix_pred
                        st.info(f"💰 Économie potentielle : **{economie:.2f} €** par rapport au meilleur prix actuel ({magasin_actuel}: {prix_actuel_min:.2f} €)")
                    elif prix_pred > prix_actuel_min:
                        hausse = prix_pred - prix_actuel_min
                        st.warning(f"⚠️ Attention : le prix pourrait augmenter de **{hausse:.2f} €** dans {jours_prediction} jours")
                    
                    # Tableau comparatif des prédictions
                    st.caption("📊 Prédictions par période :")
                    # Créer un DataFrame pour le tableau
                    data_table = []
                    for mag, data in sorted(tendances.items(), key=lambda x: x[1]['dernier_prix']):
                        emoji_trend = "📉" if data['tendance'] < 0 else "📈" if data['tendance'] > 0 else "➡️"
                        data_table.append({
                            "Magasin": f"{emoji_trend} {mag}",
                            "Prix actuel": f"{data['dernier_prix']:.2f} €",
                            "Tendance": f"{data['tendance']:.2f}%/jour",
                            f"{jours_prediction}j": f"{data['predictions'][jours_prediction]:.2f} €"
                        })
                    
                    df_pred = pd.DataFrame(data_table)
                    st.dataframe(df_pred, use_container_width=True, hide_index=True)
                    
                    st.caption("📈 Prédictions pour toutes les périodes :")
                    for mag, data in sorted(tendances.items(), key=lambda x: x[1]['predictions'][jours_prediction]):
                        emoji = "🏆" if mag == magasin_pred else ""
                        preds = data['predictions']
                        st.write(f"{emoji} **{mag}**: 7j={preds[7]:.2f}€ | 14j={preds[14]:.2f}€ | 30j={preds[30]:.2f}€ | 50j={preds[50]:.2f}€ | 90j={preds[90]:.2f}€")
            else:
                st.warning("💡 Ajoutez des prix pour ce produit sur plusieurs jours pour voir les prédictions de tendances.")
        else:
            st.info(f"💡 Aucun prix enregistré pour **{produit_pred}** dans votre panier. Ajoutez-le avec une date pour voir où l'acheter au meilleur prix !")
        
except FileNotFoundError:
    st.info("📊 Le modèle de prédiction ML (modele_simple.pkl) n'est pas disponible. Cette fonctionnalité est optionnelle.")
    st.caption("Pour activer la prédiction des ventes, placez le fichier 'modele_simple.pkl' dans le dossier de l'application.")
except Exception as e:
    st.error(f"Erreur lors du chargement du modèle ML: {str(e)}")
