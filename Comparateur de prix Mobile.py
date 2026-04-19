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

# Configuration pour mobile
st.set_page_config(
    page_title="Comparateur Prix",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar fermée par défaut sur mobile
)

# CSS pour optimiser l'affichage mobile
st.markdown("""
<style>
    /* Boutons plus grands pour toucher facilement */
    .stButton > button {
        min-height: 50px !important;
        font-size: 18px !important;
    }
    
    /* Champs de saisie plus grands */
    .stTextInput > div > div > input {
        min-height: 50px !important;
        font-size: 18px !important;
    }
    
    /* Selectbox plus grandes */
    .stSelectbox > div > div {
        min-height: 50px !important;
    }
    
    /* Titres plus compacts */
    h1 {
        font-size: 24px !important;
    }
    h2 {
        font-size: 20px !important;
    }
    h3 {
        font-size: 18px !important;
    }
    
    /* Espacement réduit */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Cards pour mobile */
    .mobile-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛒 Comparateur Prix")

# Initialisation
magasins = []

# Fonctions de gestion des magasins
def charger_magasins_personnalises():
    config_file = Path("config_magasins.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("magasins_personnalises", [])
    return []

def sauvegarder_magasins_personnalises(magasins_perso):
    config_file = Path("config_magasins.json")
    exclus = st.session_state.get("magasins_exclus", [])
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({"magasins_personnalises": magasins_perso, "magasins_exclus": exclus}, f, indent=2)

def sauvegarder_magasins_exclus():
    config_file = Path("config_magasins.json")
    magasins_perso = st.session_state.get("magasins_personnalises", [])
    exclus = st.session_state.get("magasins_exclus", [])
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({"magasins_personnalises": magasins_perso, "magasins_exclus": exclus}, f, indent=2)

def get_all_magasins():
    magasins_perso = charger_magasins_personnalises()
    exclus = st.session_state.get("magasins_exclus", [])
    seen = set()
    result = []
    for mag in magasins_perso:
        if mag and mag not in exclus:
            mag_lower = mag.lower()
            if mag_lower not in seen:
                seen.add(mag_lower)
                result.append(mag)
    return result

# Initialiser session_state
if "magasins_personnalises" not in st.session_state:
    st.session_state.magasins_personnalises = charger_magasins_personnalises()
if "magasins_exclus" not in st.session_state:
    st.session_state.magasins_exclus = []
if "nom_panier_courant" not in st.session_state:
    st.session_state.nom_panier_courant = "defaut"
if "magasin_courant" not in st.session_state:
    st.session_state.magasin_courant = None

magasins = get_all_magasins()
panier = charger_panier(st.session_state.nom_panier_courant)

# =====================================================
# NAVIGATION PAR ONGLET POUR MOBILE
# =====================================================
tabs = st.tabs(["📁 Paniers", "🏪 Magasins", "📦 Articles", "📊 Analyse"])

# =====================================================
# ONGLET 1: GESTION DES PANIERS
# =====================================================
with tabs[0]:
    st.subheader("📁 Gestion Paniers")
    
    paniers_existants = lister_paniers()
    
    # Panier actuel
    st.caption(f"Panier: **{st.session_state.nom_panier_courant}**")
    
    # Menu de sélection
    if paniers_existants and st.session_state.nom_panier_courant not in paniers_existants:
        st.session_state.nom_panier_courant = paniers_existants[0]
    
    options_paniers = ["➕ Créer", "🗑️ Supprimer"] + paniers_existants
    
    if st.session_state.nom_panier_courant in options_paniers:
        current_idx = options_paniers.index(st.session_state.nom_panier_courant)
    elif paniers_existants:
        current_idx = options_paniers.index(paniers_existants[0])
        st.session_state.nom_panier_courant = paniers_existants[0]
    else:
        current_idx = 0
    
    panier_selectionne = st.selectbox(
        "Choisir panier",
        options_paniers,
        index=current_idx,
        key="mobile_select_panier"
    )
    
    # Actions
    if panier_selectionne == "➕ Créer":
        with st.container(border=True):
            nouveau_nom = st.text_input("Nom", placeholder="ex: Courses 20.04.2026", key="mobile_new_panier")
            if st.button("✓ Créer", use_container_width=True, type="primary", key="mobile_btn_creer_panier"):
                if nouveau_nom and nouveau_nom.strip():
                    nom = nouveau_nom.strip()
                    if nom not in paniers_existants:
                        st.session_state.nom_panier_courant = nom
                        sauvegarder_panier({}, nom)
                        st.success(f"✅ Panier '{nom}' créé!")
                        st.rerun()
    
    elif panier_selectionne == "🗑️ Supprimer":
        with st.container(border=True):
            st.markdown("**🗑️ Supprimer**")
            if paniers_existants:
                panier_suppr = st.selectbox("Panier à suppr", paniers_existants, key="mobile_panier_suppr")
                if st.button("🗑️ Confirmer", use_container_width=True, type="primary", key="mobile_btn_suppr_panier"):
                    if supprimer_panier(panier_suppr):
                        if st.session_state.nom_panier_courant == panier_suppr:
                            restants = [p for p in paniers_existants if p != panier_suppr]
                            st.session_state.nom_panier_courant = restants[0] if restants else "defaut"
                        st.success(f"🗑️ Panier '{panier_suppr}' supprimé!")
                        st.rerun()
            else:
                st.info("Aucun panier")
    
    elif panier_selectionne != st.session_state.nom_panier_courant:
        st.session_state.nom_panier_courant = panier_selectionne
        st.rerun()

# =====================================================
# ONGLET 2: GESTION DES MAGASINS
# =====================================================
with tabs[1]:
    st.subheader("🏪 Gestion Magasins")
    
    tous_magasins = get_all_magasins()
    
    if not st.session_state.magasin_courant and tous_magasins:
        st.session_state.magasin_courant = tous_magasins[0]
    
    st.caption(f"Magasin: **{st.session_state.magasin_courant or 'Aucun'}**")
    
    # Menu de sélection
    options_magasins = ["➕ Créer", "🗑️ Supprimer"] + sorted(tous_magasins)
    
    if st.session_state.magasin_courant in options_magasins:
        mag_idx = options_magasins.index(st.session_state.magasin_courant)
    elif tous_magasins:
        mag_idx = options_magasins.index(sorted(tous_magasins)[0])
        st.session_state.magasin_courant = sorted(tous_magasins)[0]
    else:
        mag_idx = 0
    
    magasin_selectionne = st.selectbox(
        "Choisir magasin",
        options_magasins,
        index=mag_idx,
        key="mobile_select_magasin"
    )
    
    # Actions
    if magasin_selectionne == "➕ Créer":
        with st.container(border=True):
            nouveau_mag = st.text_input("Nom magasin", placeholder="ex: Monoprix", key="mobile_new_magasin")
            if st.button("✓ Créer", use_container_width=True, type="primary", key="mobile_btn_creer_mag"):
                if nouveau_mag and nouveau_mag.strip():
                    nom = nouveau_mag.strip()
                    if nom not in tous_magasins:
                        # Retirer des exclus si présent
                        if nom in st.session_state.magasins_exclus:
                            st.session_state.magasins_exclus.remove(nom)
                            sauvegarder_magasins_exclus()
                        st.session_state.magasins_personnalises.append(nom)
                        sauvegarder_magasins_personnalises(st.session_state.magasins_personnalises)
                        st.session_state.magasin_courant = nom
                        st.success(f"✅ Magasin '{nom}' créé!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Déjà existe")
    
    elif magasin_selectionne == "🗑️ Supprimer":
        with st.container(border=True):
            st.markdown("**🗑️ Supprimer**")
            if tous_magasins:
                mag_suppr = st.selectbox("Magasin à suppr", sorted(tous_magasins), key="mobile_mag_suppr")
                if st.button("🗑️ Confirmer", use_container_width=True, type="primary", key="mobile_btn_suppr_mag"):
                    if mag_suppr in st.session_state.magasins_personnalises:
                        st.session_state.magasins_personnalises.remove(mag_suppr)
                        sauvegarder_magasins_personnalises(st.session_state.magasins_personnalises)
                    else:
                        # Ajouter aux exclus
                        if mag_suppr not in st.session_state.magasins_exclus:
                            st.session_state.magasins_exclus.append(mag_suppr)
                            sauvegarder_magasins_exclus()
                    
                    if st.session_state.magasin_courant == mag_suppr:
                        restants = get_all_magasins()
                        st.session_state.magasin_courant = restants[0] if restants else None
                    st.success(f"🗑️ Magasin '{mag_suppr}' supprimé!")
                    st.rerun()
            else:
                st.info("Aucun magasin")
    
    elif magasin_selectionne != st.session_state.magasin_courant:
        st.session_state.magasin_courant = magasin_selectionne
        st.rerun()

# =====================================================
# ONGLET 3: GESTION DES ARTICLES
# =====================================================
with tabs[2]:
    st.subheader("📦 Articles du Panier")
    st.caption(f"Panier: **{st.session_state.nom_panier_courant}**")
    
    panier = charger_panier(st.session_state.nom_panier_courant)
    tous_magasins = get_all_magasins()
    
    if not tous_magasins:
        st.warning("⚠️ Créez d'abord un magasin dans l'onglet Magasins")
    else:
        # Ajouter un article
        with st.expander("➕ Ajouter article"):
            nom_article = st.text_input("Nom article", placeholder="ex: Pommes", key="mobile_new_article")
            
            # Sélection du magasin pour le prix
            mag_prix = st.selectbox("Magasin", tous_magasins, key="mobile_mag_prix")
            prix = st.number_input("Prix", min_value=0.0, step=0.01, key="mobile_prix")
            
            if st.button("➕ Ajouter", use_container_width=True, type="primary", key="mobile_btn_add_article"):
                if nom_article and nom_article.strip():
                    nom = nom_article.strip()
                    if nom not in panier:
                        panier[nom] = {m: 0.0 for m in tous_magasins}
                    panier[nom][mag_prix] = prix
                    sauvegarder_panier(panier, st.session_state.nom_panier_courant)
                    st.success(f"✅ '{nom}' ajouté!")
                    st.rerun()
        
        # Liste des articles
        if panier:
            st.divider()
            st.markdown("**Articles:**")
            
            for nom_article, prix_dict in list(panier.items()):
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**{nom_article}**")
                        # Afficher les prix par magasin
                        for mag, prix in prix_dict.items():
                            if not mag.startswith("_") and prix > 0:
                                st.caption(f"{mag}: {prix:.2f}€")
                    
                    with col2:
                        if st.button("🗑️", key=f"mobile_del_{nom_article}", use_container_width=True):
                            del panier[nom_article]
                            sauvegarder_panier(panier, st.session_state.nom_panier_courant)
                            st.rerun()
                    
                    # Modifier prix
                    with st.expander("✏️ Modifier prix"):
                        for mag in tous_magasins:
                            current_prix = prix_dict.get(mag, 0.0)
                            new_prix = st.number_input(
                                mag,
                                value=float(current_prix),
                                min_value=0.0,
                                step=0.01,
                                key=f"mobile_edit_{nom_article}_{mag}"
                            )
                            if new_prix != current_prix:
                                panier[nom_article][mag] = new_prix
                                sauvegarder_panier(panier, st.session_state.nom_panier_courant)
        else:
            st.info("Panier vide. Ajoutez des articles!")

# =====================================================
# ONGLET 4: ANALYSE
# =====================================================
with tabs[3]:
    st.subheader("📊 Analyse des Prix")
    st.caption(f"Panier: **{st.session_state.nom_panier_courant}**")
    
    panier = charger_panier(st.session_state.nom_panier_courant)
    
    if panier:
        # Totaux par magasin
        st.markdown("**💰 Total par magasin:**")
        totaux = calculer_totaux(panier)
        
        for mag, total in sorted(totaux.items(), key=lambda x: x[1]):
            if total > 0:
                st.metric(mag, f"{total:.2f}€")
        
        # Meilleur prix
        if totaux:
            meilleur = min(totaux.items(), key=lambda x: x[1])
            st.success(f"🏆 Meilleur: {meilleur[0]} à {meilleur[1]:.2f}€")
        
        # Graphique (version simplifiée pour mobile)
        st.divider()
        st.markdown("**📈 Comparaison:**")
        
        try:
            import plotly.graph_objects as go
            
            mags = [m for m, t in totaux.items() if t > 0]
            totals = [t for t in totaux.values() if t > 0]
            
            if mags and totals:
                fig = go.Figure(data=[
                    go.Bar(x=mags, y=totals, marker_color='lightblue')
                ])
                fig.update_layout(
                    title="Total par magasin",
                    xaxis_title="",
                    yaxis_title="€",
                    height=400,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.caption("Graphique non disponible")
    else:
        st.info("Ajoutez des articles pour voir l'analyse!")

# =====================================================
# BARRE DE NAVIGATION INFÉRIEURE (FACULTATIVE)
# =====================================================
st.divider()
cols = st.columns(4)
with cols[0]:
    st.caption("📁 Paniers")
with cols[1]:
    st.caption("🏪 Magasins")
with cols[2]:
    st.caption("📦 Articles")
with cols[3]:
    st.caption("📊 Analyse")
