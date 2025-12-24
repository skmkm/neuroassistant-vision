import streamlit as st
import requests
import os
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- 1. CONFIGURATION & FONTS ---

# Configuration de l'URL n8n
# On cherche d'abord dans les secrets Streamlit, sinon on utilise l'URL de test fournie
DEFAULT_URL = "https://drchoulli.app.n8n.cloud/webhook/neuroassistant-vision"

if "N8N_WEBHOOK_URL" in st.secrets:
    N8N_URL = st.secrets["N8N_WEBHOOK_URL"]
else:
    N8N_URL = DEFAULT_URL

# Gestion de la police Arabe (Indispensable pour le PDF)
# Le script télécharge la police "Amiri" si elle n'est pas présente
font_path = "Amiri-Regular.ttf"
if not os.path.exists(font_path):
    url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
    try:
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        st.error(f"Erreur téléchargement police: {e}")

# --- 2. FONCTION DE COMMUNICATION AVEC N8N ---

def call_n8n(text_input=None, uploaded_file=None, language="Français"):
    """
    Envoie les données à n8n via une requête Multipart.
    C'est ici que l'image part vers n8n pour être uploadée sur CLOUDINARY.
    """
    
    # 1. Préparation des données textuelles
    data_payload = {
        "text_input": text_input if text_input else "",
        "language": language
    }
    
    files_payload = {}
    
    # 2. Gestion de l'image pour Cloudinary
    # Si une image est fournie, on l'envoie en binaire brut (Multipart)
    if uploaded_file:
        # On rembobine le fichier pour être sûr de lire depuis le début
        uploaded_file.seek(0)
        
        # IMPORTANT : C'est ce bloc qui permet à n8n de recevoir le fichier
        # et de l'envoyer au nœud Cloudinary.
        # Le champ s'appelle 'data' pour correspondre à la config n8n.
        files_payload = {
            'data': (uploaded_file.name, uploaded_file, uploaded_file.type)
        }

    try:
        # Envoi de la requête POST vers votre Webhook n8n
        response = requests.post(N8N_URL, data=data_payload, files=files_payload)
        
        # Vérification des erreurs HTTP (404, 500...)
        response.raise_for_status() 
        
        # Extraction du résultat JSON renvoyé par le dernier nœud de n8n
        return response.json().get("result", "Erreur: Réponse vide de n8n")
        
    except Exception as e:
        return f"Erreur technique de connexion n8n : {str(e)}"

# --- 3. GÉNÉRATEUR PDF (COMPATIBLE ARABE) ---

def create_pdf(text_content):
    """
    Génère un PDF en gérant l'écriture de Droite-à-Gauche (RTL) pour l'Arabe/Darija
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Configuration de la police
    try:
        pdf.add_font('Amiri', '', font_path, uni=True)
        pdf.set_font("Amiri", size=12)
    except:
        # Fallback si la police n'a pas pu être chargée
        st.warning("Police Arabe non chargée, le texte risque d'être illisible.")
        pdf.set_font("Arial", size=12)

    # Traitement ligne par ligne pour le support RTL
    lines = text_content.split('\n')
    
    for line in lines:
        try:
            # 1. Reshape : Lie les lettres arabes entre elles
            reshaped_text = arabic_reshaper.reshape(line)
            # 2. Bidi : Inverse l'ordre pour l'affichage RTL
            bidi_text = get_display(reshaped_text)
            
            # Align='R' force l'alignement à droite
            pdf.multi_cell(0, 10, txt=bidi_text, align='R')
        except:
            # Si erreur sur une ligne, on l'affiche telle quelle
            pdf.multi_cell(0, 10, txt=line)
            
    return pdf.output(dest='S').encode('latin-1')

# --- 4. INTERFACE UTILISATEUR (STREAMLIT) ---

st.set_page_config(page_title="Neuro-Assistant", page_icon="🧠")

st.title("🧠 Neuro-Assistant (Sortie Patient)")
st.caption("Générateur de guides de sortie via n8n & Cloudinary - By Dr. CHOULLI")

# -- Zone de Gauche (Configuration) --
with st.sidebar:
    st.header("Paramètres")
    langue = st.selectbox(
        "Langue de sortie",
        ["Français", "Darija (Maroc)", "Arabe Classique"]
    )
    st.info("ℹ️ Darija inclura l'écriture Arabizi et Arabe.")
    st.markdown("---")
    st.text(f"Connecté à : {N8N_URL.split('/')[2]}...")

# -- Zone Principale (Input) --
st.subheader("Source du Dossier Médical (CRH)")
input_method = st.radio("Choisir le format :", ["📷 Photo (Upload)", "📝 Texte (Copier-Coller)"], horizontal=True)

text_input = ""
uploaded_file = None

if input_method == "📝 Texte (Copier-Coller)":
    text_input = st.text_area("Collez le texte du CRH ici :", height=200, placeholder="Patient opéré d'une hernie discale...")
else:
    uploaded_file = st.file_uploader("Chargez la photo du CRH", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Aperçu du document", width=300)

# -- Bouton d'Action --
if st.button("🚀 Analyser et Générer le Guide"):
    
    # Vérification que l'utilisateur a mis quelque chose
    has_content = (input_method == "📝 Texte (Copier-Coller)" and text_input) or \
                  (input_method == "📷 Photo (Upload)" and uploaded_file)
                  
    if not has_content:
        st.warning("Veuillez fournir un texte ou une image avant de lancer l'analyse.")
    else:
        with st.spinner("Envoi à n8n -> Upload Cloudinary -> Analyse GPT-4o..."):
            # Appel Backend
            result_text = call_n8n(text_input, uploaded_file, language=langue)
            
            # Affichage Résultat
            st.success("Analyse terminée !")
            st.markdown("---")
            st.subheader("Aperçu du Guide :")
            st.text_area("Résultat", value=result_text, height=400)
            
            # Génération PDF
            pdf_bytes = create_pdf(result_text)
            
            st.download_button(
                label="📥 Télécharger le PDF (Compatible Arabe)",
                data=pdf_bytes,
                file_name="Guide_Sortie_Patient.pdf",
                mime="application/pdf"
            )
