import streamlit as st
import requests
import os
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
from datetime import datetime

# --- 1. CONFIGURATION & FONTS ---

# Config Page Streamlit
st.set_page_config(page_title="Neuro-Assistant", page_icon="🧠", layout="centered")

# URL n8n
DEFAULT_URL = "https://drchoulli.app.n8n.cloud/webhook/neuroassistant-vision"
if "N8N_WEBHOOK_URL" in st.secrets:
    N8N_URL = st.secrets["N8N_WEBHOOK_URL"]
else:
    N8N_URL = DEFAULT_URL

# Téléchargement Police Arabe (Amiri)
font_path = "Amiri-Regular.ttf"
if not os.path.exists(font_path):
    url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
    try:
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        st.error(f"Erreur téléchargement police: {e}")

# --- 2. CONFIGURATION DES COULEURS (DESIGN) ---
COLOR_PRIMARY = (0, 51, 102)     # Bleu Roi (Titres)
COLOR_ACCENT = (23, 162, 184)    # Cyan (Lignes)
COLOR_WARNING = (220, 53, 69)    # Rouge (Alertes)
COLOR_TEXT = (50, 50, 50)        # Gris Foncé (Texte)

# --- 3. CLASSE PDF PERSONNALISÉE (HEADER/FOOTER) ---
class PDF(FPDF):
    def header(self):
        # Titre Principal
        try:
            self.add_font('Amiri', '', font_path, uni=True)
            self.set_font('Amiri', '', 20)
        except:
            self.set_font('Arial', 'B', 18)
            
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 10, "Service de Neurochirurgie", ln=True, align='C')
        
        # Sous-titre
        self.set_font_size(12)
        self.set_text_color(100, 100, 100) # Gris
        self.cell(0, 6, "Guide de Sortie Patient / ورقة خروج", ln=True, align='C')
        
        # Ligne de séparation
        self.ln(5)
        self.set_draw_color(*COLOR_ACCENT)
        self.set_line_width(0.5)
        self.line(10, 32, 200, 32)
        self.ln(10) # Espace après le header

    def footer(self):
        self.set_y(-15)
        try:
            self.set_font('Amiri', '', 9)
        except:
            self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        
        # Gauche : Dr Choulli
        self.cell(0, 10, 'Dr. CHOULLI - Neurochirurgie', 0, 0, 'L')
        # Droite : Page number
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')

# --- 4. FONCTION DE GÉNÉRATION INTELLIGENTE ---
def create_pdf(text_content):
    pdf = PDF()
    pdf.add_page()
    
    # Chargement Police
    try:
        pdf.add_font('Amiri', '', font_path, uni=True)
    except:
        pass

    # Date du document
    date_jour = datetime.now().strftime("%d/%m/%Y")
    pdf.set_font("Amiri", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Date: {date_jour}", ln=True, align='R')
    pdf.ln(5)

    # Analyse ligne par ligne pour le style
    lines = text_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # --- STYLE: TITRES DE SECTION (Détectés par **) ---
        if "**" in line and (line[0].isdigit() or len(line) < 60):
            clean_line = line.replace('**', '').replace(':', '')
            
            # Traitement Arabe
            reshaped = arabic_reshaper.reshape(clean_line)
            bidi_text = get_display(reshaped)
            
            pdf.ln(6)
            # Fond coloré
            pdf.set_fill_color(*COLOR_PRIMARY) 
            pdf.set_text_color(255, 255, 255) # Blanc
            pdf.set_font("Amiri", "", 14)
            
            # Affichage du bandeau
            pdf.cell(0, 9, bidi_text, ln=True, align='R', fill=True)
            
            # Reset
            pdf.set_text_color(*COLOR_TEXT)
            pdf.ln(2)

        # --- STYLE: ALERTES (Détectées par ⚠️ ou URGENCE) ---
        elif "⚠️" in line or "URGENCE" in line.upper():
            reshaped = arabic_reshaper.reshape(line)
            bidi_text = get_display(reshaped)
            
            pdf.set_text_color(*COLOR_WARNING) # Rouge
            pdf.set_font("Amiri", "", 12)
            pdf.multi_cell(0, 8, txt=bidi_text, align='R')
            pdf.set_text_color(*COLOR_TEXT) # Reset

        # --- STYLE: TEXTE NORMAL ---
        else:
            reshaped = arabic_reshaper.reshape(line)
            bidi_text = get_display(reshaped)
            
            pdf.set_font("Amiri", "", 12)
            
            # Indentation pour les listes
            if line.startswith("-") or line.startswith("*"):
                 # Petite astuce : on ajoute un espace visuel
                 pass 
            
            pdf.multi_cell(0, 7, txt=bidi_text, align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- 5. FONCTION APPEL N8N ---
def call_n8n(text_input=None, uploaded_file=None, language="Français"):
    data_payload = {
        "text_input": text_input if text_input else "",
        "language": language
    }
    files_payload = {}
    
    if uploaded_file:
        uploaded_file.seek(0)
        files_payload = {
            'data': (uploaded_file.name, uploaded_file, uploaded_file.type)
        }

    try:
        response = requests.post(N8N_URL, data=data_payload, files=files_payload)
        response.raise_for_status() 
        return response.json().get("result", "Erreur: Réponse vide de n8n")
    except Exception as e:
        return f"Erreur connexion n8n : {str(e)}"

# --- 6. INTERFACE UI ---

st.title("🧠 Neuro-Assistant")
st.caption("Générateur de guides de sortie | Dr. CHOULLI")

# Sidebar
with st.sidebar:
    st.header("Paramètres")
    langue = st.selectbox("Langue", ["Français", "Darija (Maroc)", "Arabe Classique"])
    st.info("💡 Darija inclut l'écriture Arabizi et Arabe.")
    st.markdown("---")
    st.success("Système Connecté ✅")

# Input
input_method = st.radio("Source", ["📷 Photo (Upload)", "📝 Texte (Copier-Coller)"], horizontal=True)

text_input = ""
uploaded_file = None

if input_method == "📝 Texte (Copier-Coller)":
    text_input = st.text_area("Collez le CRH ici :", height=200)
else:
    uploaded_file = st.file_uploader("Photo du CRH", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Aperçu", width=300)

# Action
if st.button("🚀 Générer le Guide PDF", type="primary"):
    has_content = (input_method == "📝 Texte (Copier-Coller)" and text_input) or \
                  (input_method == "📷 Photo (Upload)" and uploaded_file)
                  
    if not has_content:
        st.warning("Veuillez fournir un document.")
    else:
        with st.spinner("Analyse intelligente en cours..."):
            result_text = call_n8n(text_input, uploaded_file, language=langue)
            
            # Colonnes pour afficher côte à côte résultat et bouton
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.success("Analyse terminée !")
                st.text_area("Aperçu du texte", value=result_text, height=300)
            
            with col2:
                st.markdown("### Téléchargement")
                st.write("Votre document officiel est prêt.")
                # PDF
                pdf_bytes = create_pdf(result_text)
                st.download_button(
                    label="📄 Télécharger PDF",
                    data=pdf_bytes,
                    file_name=f"Guide_Sortie_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
