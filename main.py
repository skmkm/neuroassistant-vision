import streamlit as st
import requests
import os
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- 1. CONFIGURATION & FONTS ---

# Récupération de l'URL n8n depuis les secrets
# Si vous testez en local, remplacez os.environ.get par votre URL entre guillemets
N8N_URL = os.environ.get("https://drchoulli.app.n8n.cloud/webhook-test/neuroassistant-vision")

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
    Envoie les données à n8n via une requête Multipart (Standard HTTP).
    Cela permet d'envoyer l'image sans l'encoder en Base64 (plus léger).
    """
    
    # Préparation des données textuelles
    data_payload = {
        "text_input": text_input if text_input else "Analyse ce document.",
        "language": language
    }
    
    files_payload = {}
    
    # Si une image est fournie
    if uploaded_file:
        # On rembobine le fichier (sécurité)
        uploaded_file.seek(0)
        # Format: 'nom_champ_n8n': (nom_fichier, contenu, type_mime)
        # Note: 'data' est le nom du champ binaire qu'on a configuré dans n8n
        files_payload = {
            'data': (uploaded_file.name, uploaded_file, uploaded_file.type)
        }

    try:
        if not N8N_URL:
            return "Erreur: URL N8N manquante dans les Secrets."

        # Envoi de la requête
        response = requests.post(N8N_URL, data=data_payload, files=files_payload)
        response.raise_for_status() # Lève une erreur si n8n renvoie 400/500
        
        # Extraction du résultat JSON
        # On suppose que n8n renvoie { "result": "Le texte généré..." }
        return response.json().get("result", "Erreur: Réponse vide de n8n")
        
    except Exception as e:
        return f"Erreur technique de connexion : {str(e)}"

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

    # Traitement ligne par ligne
    # FPDF ne gère pas le RTL nativement, on utilise arabic_reshaper et bidi
    lines = text_content.split('\n')
    
    for line in lines:
        try:
            # 1. Reshape : Lie les lettres arabes entre elles correctement
            reshaped_text = arabic_reshaper.reshape(line)
            # 2. Bidi : Inverse l'ordre pour l'affichage RTL
            bidi_text = get_display(reshaped_text)
            
            # Align='R' force l'alignement à droite (standard en Arabe)
            pdf.multi_cell(0, 10, txt=bidi_text, align='R')
        except:
            # Si une ligne pose problème (ex: caractères spéciaux), on l'imprime telle quelle
            pdf.multi_cell(0, 10, txt=line)
            
    return pdf.output(dest='S').encode('latin-1')

# --- 4. INTERFACE UTILISATEUR (STREAMLIT) ---

st.set_page_config(page_title="Neuro-Assistant", page_icon="🧠")

st.title("🧠 Neuro-Assistant (Sortie Patient)")
st.caption("Générateur de guides de sortie via IA (Architecture n8n)")

# -- Zone de Gauche (Configuration) --
with st.sidebar:
    st.header("Paramètres")
    langue = st.selectbox(
        "Langue de sortie",
        ["Français", "Darija (Maroc)", "Arabe Classique"]
    )
    st.info("ℹ️ Darija inclura l'écriture Arabizi et Arabe.")

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
        with st.spinner("Transmission à n8n (Cloudinary + OpenAI)..."):
            # Appel Backend
            result_text = call_n8n(text_input, uploaded_file, language=langue)
            
            # Affichage Résultat
            st.success("Analyse terminée !")
            st.markdown("---")
            st.subheader("Aperçu du Guide :")
            st.text_area("Résultat modifiable", value=result_text, height=400)
            
            # Génération PDF
            pdf_bytes = create_pdf(result_text)
            
            st.download_button(
                label="📥 Télécharger le PDF (Compatible Arabe)",
                data=pdf_bytes,
                file_name="Guide_Sortie_Patient.pdf",
                mime="application/pdf"
            )
