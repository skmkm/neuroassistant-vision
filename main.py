import streamlit as st
import requests
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import arabic_reshaper
from bidi.algorithm import get_display
from io import BytesIO
import re

# --- 1. CONFIGURATION & FONTS ---

DEFAULT_URL = "https://drchoulli.app.n8n.cloud/webhook/neuroassistant-vision"

if "N8N_WEBHOOK_URL" in st.secrets:
    N8N_URL = st.secrets["N8N_WEBHOOK_URL"]
else:
    N8N_URL = DEFAULT_URL

# Téléchargement de la police Arabe
font_path = "Amiri-Regular.ttf"
font_bold_path = "Amiri-Bold.ttf"

if not os.path.exists(font_path):
    url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
    try:
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        st.error(f"Erreur téléchargement police: {e}")

if not os.path.exists(font_bold_path):
    url_bold = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"
    try:
        response = requests.get(url_bold)
        with open(font_bold_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        pass  # Bold est optionnel

# --- 2. FONCTION DE COMMUNICATION AVEC N8N ---

def call_n8n(text_input=None, uploaded_file=None, language="Français"):
    """Envoie les données à n8n via une requête Multipart."""
    
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
        return f"Erreur technique de connexion n8n : {str(e)}"

# --- 3. GÉNÉRATEUR PDF MODERNE ET ÉLÉGANT ---

def create_beautiful_pdf(text_content, language="Français"):
    """Génère un PDF moderne avec design professionnel"""
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Enregistrer les polices
    try:
        pdfmetrics.registerFont(TTFont('Amiri', font_path))
        if os.path.exists(font_bold_path):
            pdfmetrics.registerFont(TTFont('Amiri-Bold', font_bold_path))
        has_arabic_font = True
    except:
        has_arabic_font = False
    
    is_arabic = "Arabe" in language or "Darija" in language
    
    # === HEADER DESIGN ===
    def draw_header():
        # Bande de couleur gradient en haut
        c.setFillColor(colors.HexColor('#2C3E50'))
        c.rect(0, height - 3*cm, width, 3*cm, fill=1, stroke=0)
        
        # Titre principal
        c.setFillColor(colors.white)
        if has_arabic_font and is_arabic:
            c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 20)
        else:
            c.setFont("Helvetica-Bold", 20)
        
        title = "دليل الخروج من المستشفى" if is_arabic else "GUIDE DE SORTIE"
        c.drawCentredString(width/2, height - 1.5*cm, title)
        
        # Sous-titre
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, height - 2*cm, "Service de Neurochirurgie")
        
        # Logo ou icône (simulé avec un cercle)
        c.setFillColor(colors.HexColor('#3498DB'))
        c.circle(2*cm, height - 1.5*cm, 0.6*cm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(2*cm, height - 1.7*cm, "🧠")
    
    # === FOOTER DESIGN ===
    def draw_footer(page_num):
        c.setStrokeColor(colors.HexColor('#3498DB'))
        c.setLineWidth(2)
        c.line(2*cm, 2*cm, width - 2*cm, 2*cm)
        
        c.setFillColor(colors.HexColor('#7F8C8D'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, 1.5*cm, f"Page {page_num} - Document confidentiel")
        c.drawString(2*cm, 1.5*cm, "🏥 CHU Hassan II")
    
    # === TRAITEMENT DU CONTENU ===
    draw_header()
    
    # Marges et position initiale
    margin_left = 2*cm
    margin_right = width - 2*cm
    y_position = height - 4*cm
    line_height = 0.5*cm
    page_num = 1
    
    lines = text_content.split('\n')
    
    for line in lines:
        # Gestion du changement de page
        if y_position < 3*cm:
            draw_footer(page_num)
            c.showPage()
            page_num += 1
            draw_header()
            y_position = height - 4*cm
        
        line = line.strip()
        
        if not line:
            y_position -= line_height * 0.5
            continue
        
        # === DÉTECTION DES TITRES ET SECTIONS ===
        
        # Titre principal (Guide de Sortie)
        if "Guide de Sortie" in line or "دليل الخروج" in line:
            c.setFillColor(colors.HexColor('#2C3E50'))
            if has_arabic_font and is_arabic:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 16)
            else:
                c.setFont("Helvetica-Bold", 16)
            
            if is_arabic:
                reshaped = arabic_reshaper.reshape(line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right, y_position, bidi)
            else:
                c.drawString(margin_left, y_position, line)
            
            y_position -= line_height * 2
            continue
        
        # Sections numérotées (1., 2., 3., 4.)
        if re.match(r'^[1-4]\.\s', line):
            # Boîte colorée pour les sections
            section_colors = {
                '1.': '#3498DB',  # Bleu
                '2.': '#27AE60',  # Vert
                '3.': '#E74C3C',  # Rouge
                '4.': '#F39C12'   # Orange
            }
            
            section_num = line[0]
            color = section_colors.get(f"{section_num}.", '#3498DB')
            
            # Barre latérale colorée
            c.setFillColor(colors.HexColor(color))
            c.rect(margin_left - 0.3*cm, y_position - 0.2*cm, 0.2*cm, 0.6*cm, fill=1, stroke=0)
            
            # Texte de section
            c.setFillColor(colors.HexColor(color))
            if has_arabic_font and is_arabic:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 14)
            else:
                c.setFont("Helvetica-Bold", 14)
            
            if is_arabic:
                reshaped = arabic_reshaper.reshape(line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right, y_position, bidi)
            else:
                c.drawString(margin_left + 0.2*cm, y_position, line)
            
            y_position -= line_height * 1.8
            continue
        
        # Sous-sections avec tirets ou puces
        if line.startswith('-') or line.startswith('•') or line.startswith('*'):
            c.setFillColor(colors.HexColor('#34495E'))
            if has_arabic_font and is_arabic:
                c.setFont("Amiri", 11)
            else:
                c.setFont("Helvetica", 11)
            
            # Puce graphique
            c.setFillColor(colors.HexColor('#3498DB'))
            if is_arabic:
                c.circle(margin_right - 0.3*cm, y_position + 0.15*cm, 0.08*cm, fill=1)
            else:
                c.circle(margin_left + 0.3*cm, y_position + 0.15*cm, 0.08*cm, fill=1)
            
            c.setFillColor(colors.HexColor('#34495E'))
            clean_line = line.lstrip('-•* ')
            
            if is_arabic:
                reshaped = arabic_reshaper.reshape(clean_line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right - 0.6*cm, y_position, bidi)
            else:
                c.drawString(margin_left + 0.6*cm, y_position, clean_line)
            
            y_position -= line_height * 1.2
            continue
        
        # Mots-clés importants (ATTENTION, ALERTE, etc.)
        if any(keyword in line.upper() for keyword in ['ATTENTION', 'ALERTE', 'IMPORTANT', 'URGENCE', 'WARNING']):
            # Fond d'alerte
            c.setFillColor(colors.HexColor('#FFEBEE'))
            c.roundRect(margin_left - 0.3*cm, y_position - 0.1*cm, 
                       margin_right - margin_left + 0.6*cm, 0.5*cm, 
                       0.1*cm, fill=1, stroke=0)
            
            c.setFillColor(colors.HexColor('#C0392B'))
            if has_arabic_font and is_arabic:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 11)
            else:
                c.setFont("Helvetica-Bold", 11)
            
            if is_arabic:
                reshaped = arabic_reshaper.reshape(line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right, y_position, bidi)
            else:
                c.drawString(margin_left, y_position, line)
            
            y_position -= line_height * 1.5
            continue
        
        # Questions (Q:)
        if line.startswith('Q:') or line.startswith('Q :'):
            c.setFillColor(colors.HexColor('#2980B9'))
            if has_arabic_font and is_arabic:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 11)
            else:
                c.setFont("Helvetica-Bold", 11)
            
            if is_arabic:
                reshaped = arabic_reshaper.reshape(line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right, y_position, bidi)
            else:
                c.drawString(margin_left, y_position, line)
            
            y_position -= line_height * 1.2
            continue
        
        # Réponses (R:)
        if line.startswith('R:') or line.startswith('R :'):
            c.setFillColor(colors.HexColor('#16A085'))
            if has_arabic_font and is_arabic:
                c.setFont("Amiri", 11)
            else:
                c.setFont("Helvetica", 11)
            
            if is_arabic:
                reshaped = arabic_reshaper.reshape(line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right - 0.5*cm, y_position, bidi)
            else:
                c.drawString(margin_left + 0.5*cm, y_position, line)
            
            y_position -= line_height * 1.2
            continue
        
        # Texte normal
        c.setFillColor(colors.HexColor('#2C3E50'))
        if has_arabic_font and is_arabic:
            c.setFont("Amiri", 11)
        else:
            c.setFont("Helvetica", 11)
        
        try:
            if is_arabic:
                reshaped = arabic_reshaper.reshape(line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right, y_position, bidi)
            else:
                # Gestion du text wrapping pour le français
                max_width = margin_right - margin_left
                if c.stringWidth(line, "Helvetica", 11) > max_width:
                    words = line.split()
                    current_line = ""
                    for word in words:
                        test_line = current_line + " " + word if current_line else word
                        if c.stringWidth(test_line, "Helvetica", 11) <= max_width:
                            current_line = test_line
                        else:
                            c.drawString(margin_left, y_position, current_line)
                            y_position -= line_height
                            current_line = word
                    if current_line:
                        c.drawString(margin_left, y_position, current_line)
                else:
                    c.drawString(margin_left, y_position, line)
        except:
            c.drawString(margin_left, y_position, line[:80])
        
        y_position -= line_height
    
    # Footer de la dernière page
    draw_footer(page_num)
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# --- 4. INTERFACE UTILISATEUR (STREAMLIT) ---

st.set_page_config(page_title="Neuro-Assistant", page_icon="🧠")

st.title("🧠 Neuro-Assistant (Sortie Patient)")
st.caption("Générateur de guides de sortie via n8n & Cloudinary - By Dr. CHOULLI")

with st.sidebar:
    st.header("Paramètres")
    langue = st.selectbox(
        "Langue de sortie",
        ["Français", "Darija (Maroc)", "Arabe Classique"]
    )
    st.info("ℹ️ Darija inclura l'écriture Arabizi et Arabe.")
    st.markdown("---")
    st.text(f"Connecté à : {N8N_URL.split('/')[2]}...")

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

if st.button("🚀 Analyser et Générer le Guide"):
    
    has_content = (input_method == "📝 Texte (Copier-Coller)" and text_input) or \
                  (input_method == "📷 Photo (Upload)" and uploaded_file)
                  
    if not has_content:
        st.warning("Veuillez fournir un texte ou une image avant de lancer l'analyse.")
    else:
        with st.spinner("Envoi à n8n -> Upload Cloudinary -> Analyse GPT-4o..."):
            result_text = call_n8n(text_input, uploaded_file, language=langue)
            
            st.success("Analyse terminée !")
            st.markdown("---")
            st.subheader("Aperçu du Guide :")
            st.text_area("Résultat", value=result_text, height=400)
            
            try:
                pdf_bytes = create_beautiful_pdf(result_text, langue)
                
                st.download_button(
                    label="📥 Télécharger le PDF Design",
                    data=pdf_bytes,
                    file_name="Guide_Sortie_Patient.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Erreur génération PDF: {str(e)}")
