"""
Interface Streamlit — DocComprendre
Permet de coller ou uploader un document et d'obtenir une explication structurée.
"""

import streamlit as st
import requests
import json

API_URL = "http://localhost:8080"

# ─────────────────────────────────────────
# Config page
# ─────────────────────────────────────────

st.set_page_config(
    page_title="DocComprendre",
    page_icon="📄",
    layout="wide",
)

st.title("📄 DocComprendre")
st.caption("Comprenez vos documents administratifs et médicaux en français, arabe ou darija.")

# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Paramètres")
    langue = st.selectbox(
        "Langue de réponse",
        options=["fr", "ar", "ary"],
        format_func=lambda x: {"fr": "🇫🇷 Français", "ar": "🇲🇦 Arabe", "ary": "🇲🇦 Darija"}[x],
    )
    st.divider()
    st.info(
        "**ℹ️ Ce que fait cet assistant :**\n"
        "- Explique le contenu de vos documents\n"
        "- Liste les actions à faire\n"
        "- Définit les mots difficiles\n\n"
        "**Ce qu'il ne fait pas :**\n"
        "- Aucun conseil médical ou juridique\n"
        "- Aucune invention — tout est sourcé\n"
        "- Aucune conservation de vos données"
    )

# ─────────────────────────────────────────
# Zone de saisie du document
# ─────────────────────────────────────────

st.subheader("1️⃣ Entrez votre document")

onglet_texte, onglet_fichier = st.tabs(["📝 Coller du texte", "📎 Uploader un fichier"])

texte_document = ""

with onglet_texte:
    texte_document = st.text_area(
        "Collez ici le texte de votre document",
        height=200,
        placeholder="Ex : Madame, Monsieur, Suite à votre déclaration...",
    )

with onglet_fichier:
    fichier_upload = st.file_uploader(
        "Choisissez un fichier",
        type=["pdf", "png", "jpg", "jpeg", "bmp", "txt"],
        help="Formats supportés : PDF, images (PNG, JPG), texte"
    )

    if fichier_upload:
        st.success(f"✅ Fichier chargé : {fichier_upload.name}")
        # Le texte sera extrait côté API

# ─────────────────────────────────────────
# Bouton d'explication
# ─────────────────────────────────────────

st.subheader("2️⃣ Obtenir l'explication")

# Détecter si on a du texte ou un fichier
mode = "fichier" if fichier_upload else "texte"
peut_expliquer = texte_document.strip() or fichier_upload

if st.button("🔍 Expliquer ce document", type="primary", disabled=not peut_expliquer):
    with st.spinner("Analyse en cours... (30-60 secondes)"):
        try:
            if mode == "fichier":
                # Upload de fichier
                files = {"fichier": (fichier_upload.name, fichier_upload, fichier_upload.type)}
                data_form = {"langue": langue}

                resp = requests.post(
                    f"{API_URL}/expliquer-fichier",
                    files=files,
                    data=data_form,
                    timeout=300,
                )
            else:
                # Texte collé
                resp = requests.post(
                    f"{API_URL}/expliquer",
                    json={"texte": texte_document, "langue": langue},
                    timeout=300,
                )

            resp.raise_for_status()
            data = resp.json()

            # ─── Résumé ───
            st.success("✅ Explication générée")
            st.subheader("📋 Résumé")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Type de document", data.get("type_document", "—"))
            with col2:
                st.metric("Émetteur", data.get("emetteur") or "Non mentionné")
            st.write(data.get("resume_simple", ""))

            # ─── Actions ───
            actions = data.get("actions", [])
            if actions:
                st.subheader("✅ Actions à faire")
                for a in actions:
                    date = f" — avant le **{a['date_limite']}**" if a.get("date_limite") else ""
                    note = f" *(note : {a['note']})*" if a.get("note") else ""
                    st.markdown(f"- {a['action']}{date}{note}")

            # ─── Termes ───
            termes = data.get("termes", [])
            if termes:
                st.subheader("📚 Mots difficiles expliqués")
                for t in termes:
                    with st.expander(f"**{t['terme']}**"):
                        st.write(t["explication"])
                        if t.get("source"):
                            st.caption(f"Source : {t['source']}")

            # ─── Avertissement ───
            if data.get("avertissement"):
                st.warning(f"⚠️ {data['avertissement']}")

            # ─── Incertitudes ───
            incertitudes = data.get("incertitudes", [])
            if incertitudes:
                st.subheader("❓ Informations manquantes dans le document")
                for i in incertitudes:
                    st.markdown(f"- {i}")

            # ─── Citations ───
            citations = data.get("citations", [])
            if citations:
                with st.expander("🔗 Passages cités"):
                    for c in citations:
                        st.markdown(f"> {c}")

        except requests.exceptions.ConnectionError:
            st.error("❌ Impossible de joindre l'API. Lancez d'abord : `python -m src.api.main`")
        except requests.exceptions.Timeout:
            st.error("⏱️ Timeout — le modèle met trop de temps. Réessayez avec un texte plus court.")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

# ─────────────────────────────────────────
# Zone de questions
# ─────────────────────────────────────────

if texte_document.strip():
    st.divider()
    st.subheader("3️⃣ Poser une question sur ce document")

    question = st.text_input(
        "Votre question",
        placeholder="Ex : Quelle est la date limite de paiement ?",
    )

    if st.button("💬 Poser la question", disabled=not question.strip()):
        with st.spinner("Recherche de la réponse..."):
            try:
                resp = requests.post(
                    f"{API_URL}/question",
                    json={
                        "question": question,
                        "texte_document": texte_document,
                        "langue": langue,
                    },
                    timeout=300,
                )
                resp.raise_for_status()
                data = resp.json()
                st.info(f"💬 **Réponse :** {data['reponse']}")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
