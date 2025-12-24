import streamlit as st
import requests
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
from io import BytesIO
import re
import textwrap

# --- 1. CONFIGURATION & FONTS ---

DEFAULT_URL = "https://drchoulli.app.n8n.cloud/webhook/neuroassistant-vision"

if "N8N_WEBHOOK_URL" in st.secrets:
    N8N_URL = st.secrets["N8N_WEBHOOK_URL"]
else:
    N8N_URL = DEFAULT_URL

# Téléchargement des polices Arabe
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
        pass

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

# --- 3. HELPER FUNCTIONS ---

def contains_arabic(text):
    """Détecte si le texte contient des caractères arabes"""
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')
    return bool(arabic_pattern.search(text))

def wrap_text_arabic(text, canvas_obj, font_name, font_size, max_width):
    """Découpe le texte arabe en lignes qui tiennent dans la largeur max"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        reshaped = arabic_reshaper.reshape(test_line)
        bidi = get_display(reshaped)
        
        if canvas_obj.stringWidth(bidi, font_name, font_size) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def wrap_text_latin(text, canvas_obj, font_name, font_size, max_width):
    """Découpe le texte latin/français en lignes"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if canvas_obj.stringWidth(test_line, font_name, font_size) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

# --- 4. GÉNÉRATEUR PDF MODERNE ET ÉLÉGANT ---

def create_beautiful_pdf(text_content, language="Français"):
    """Génère un PDF moderne avec support complet de l'arabe"""
    
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
    
    is_arabic_lang = "Arabe" in language or "Darija" in language
    
    # === HEADER DESIGN ===
    def draw_header():
        c.setFillColor(colors.HexColor('#2C3E50'))
        c.rect(0, height - 3*cm, width, 3*cm, fill=1, stroke=0)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        
        if is_arabic_lang:
            title = "دليل الخروج من المستشفى"
            if has_arabic_font:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 20)
                reshaped = arabic_reshaper.reshape(title)
                bidi = get_display(reshaped)
                c.drawCentredString(width/2, height - 1.5*cm, bidi)
            else:
                c.drawCentredString(width/2, height - 1.5*cm, "GUIDE DE SORTIE")
        else:
            c.drawCentredString(width/2, height - 1.5*cm, "GUIDE DE SORTIE")
        
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, height - 2*cm, "Service de Neurochirurgie")
        
        c.setFillColor(colors.HexColor('#3498DB'))
        c.circle(2*cm, height - 1.5*cm, 0.6*cm, fill=1, stroke=0)
    
    def draw_footer(page_num):
        c.setStrokeColor(colors.HexColor('#3498DB'))
        c.setLineWidth(2)
        c.line(2*cm, 2*cm, width - 2*cm, 2*cm)
        
        c.setFillColor(colors.HexColor('#7F8C8D'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, 1.5*cm, f"Page {page_num}")
        c.drawString(2*cm, 1.5*cm, "CHU Hassan II")
    
    # === TRAITEMENT DU CONTENU ===
    draw_header()
    
    margin_left = 2*cm
    margin_right = width - 2*cm
    max_text_width = margin_right - margin_left - 1*cm
    y_position = height - 4*cm
    line_height = 0.6*cm
    page_num = 1
    
    lines = text_content.split('\n')
    
    for line in lines:
        # Gestion du changement de page
        if y_position < 3.5*cm:
            draw_footer(page_num)
            c.showPage()
            page_num += 1
            draw_header()
            y_position = height - 4*cm
        
        line = line.strip()
        
        if not line:
            y_position -= line_height * 0.3
            continue
        
        # Détection si la ligne contient de l'arabe
        is_arabic_text = contains_arabic(line)
        
        # === TITRE PRINCIPAL ===
        if "Guide de Sortie" in line or "دليل" in line or line.startswith("==="):
            c.setFillColor(colors.HexColor('#2C3E50'))
            font_size = 16
            
            if is_arabic_text and has_arabic_font:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", font_size)
                reshaped = arabic_reshaper.reshape(line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right, y_position, bidi)
            else:
                c.setFont("Helvetica-Bold", font_size)
                c.drawString(margin_left, y_position, line)
            
            y_position -= line_height * 2
            continue
        
        # === SECTIONS NUMÉROTÉES (1., 2., 3., 4.) ===
        if re.match(r'^[1-4]\.\s', line) or re.match(r'^[١-٤]\.', line):
            section_colors = {
                '1': '#3498DB', '2': '#27AE60', '3': '#E74C3C', '4': '#F39C12',
                '١': '#3498DB', '٢': '#27AE60', '٣': '#E74C3C', '٤': '#F39C12'
            }
            
            section_num = line[0]
            color = section_colors.get(section_num, '#3498DB')
            
            # Barre latérale
            if is_arabic_text:
                c.setFillColor(colors.HexColor(color))
                c.rect(margin_right + 0.1*cm, y_position - 0.2*cm, 0.2*cm, 0.6*cm, fill=1, stroke=0)
            else:
                c.setFillColor(colors.HexColor(color))
                c.rect(margin_left - 0.3*cm, y_position - 0.2*cm, 0.2*cm, 0.6*cm, fill=1, stroke=0)
            
            c.setFillColor(colors.HexColor(color))
            font_size = 14
            
            if is_arabic_text and has_arabic_font:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", font_size)
                
                # Wrap si nécessaire
                wrapped_lines = wrap_text_arabic(line, c, "Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 
                                                font_size, max_text_width)
                for wrapped_line in wrapped_lines:
                    reshaped = arabic_reshaper.reshape(wrapped_line)
                    bidi = get_display(reshaped)
                    c.drawRightString(margin_right, y_position, bidi)
                    y_position -= line_height
            else:
                c.setFont("Helvetica-Bold", font_size)
                wrapped_lines = wrap_text_latin(line, c, "Helvetica-Bold", font_size, max_text_width)
                for wrapped_line in wrapped_lines:
                    c.drawString(margin_left + 0.2*cm, y_position, wrapped_line)
                    y_position -= line_height
            
            y_position -= line_height * 0.5
            continue
        
        # === SOUS-SECTIONS AVEC PUCES ===
        if line.startswith('-') or line.startswith('•') or line.startswith('*'):
            c.setFillColor(colors.HexColor('#34495E'))
            font_size = 11
            
            # Puce graphique
            c.setFillColor(colors.HexColor('#3498DB'))
            if is_arabic_text:
                c.circle(margin_right - 0.3*cm, y_position + 0.15*cm, 0.08*cm, fill=1)
            else:
                c.circle(margin_left + 0.3*cm, y_position + 0.15*cm, 0.08*cm, fill=1)
            
            c.setFillColor(colors.HexColor('#34495E'))
            clean_line = line.lstrip('-•* ')
            
            if is_arabic_text and has_arabic_font:
                c.setFont("Amiri", font_size)
                wrapped_lines = wrap_text_arabic(clean_line, c, "Amiri", font_size, max_text_width - 1*cm)
                
                for wrapped_line in wrapped_lines:
                    reshaped = arabic_reshaper.reshape(wrapped_line)
                    bidi = get_display(reshaped)
                    c.drawRightString(margin_right - 0.6*cm, y_position, bidi)
                    y_position -= line_height
            else:
                c.setFont("Helvetica", font_size)
                wrapped_lines = wrap_text_latin(clean_line, c, "Helvetica", font_size, max_text_width - 1*cm)
                
                for wrapped_line in wrapped_lines:
                    c.drawString(margin_left + 0.6*cm, y_position, wrapped_line)
                    y_position -= line_height
            
            continue
        
        # === ALERTES ET MOTS-CLÉS ===
        if any(keyword in line.upper() for keyword in ['ATTENTION', 'ALERTE', 'IMPORTANT', 'URGENCE', 'تنبيه', 'مهم']):
            c.setFillColor(colors.HexColor('#FFEBEE'))
            
            font_size = 11
            
            if is_arabic_text and has_arabic_font:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", font_size)
                wrapped_lines = wrap_text_arabic(line, c, "Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 
                                                font_size, max_text_width)
            else:
                c.setFont("Helvetica-Bold", font_size)
                wrapped_lines = wrap_text_latin(line, c, "Helvetica-Bold", font_size, max_text_width)
            
            # Dessiner le fond pour toutes les lignes
            box_height = len(wrapped_lines) * line_height + 0.2*cm
            c.roundRect(margin_left - 0.3*cm, y_position - 0.1*cm, 
                       margin_right - margin_left + 0.6*cm, box_height, 
                       0.1*cm, fill=1, stroke=0)
            
            c.setFillColor(colors.HexColor('#C0392B'))
            
            for wrapped_line in wrapped_lines:
                if is_arabic_text and has_arabic_font:
                    reshaped = arabic_reshaper.reshape(wrapped_line)
                    bidi = get_display(reshaped)
                    c.drawRightString(margin_right, y_position, bidi)
                else:
                    c.drawString(margin_left, y_position, wrapped_line)
                y_position -= line_height
            
            y_position -= line_height * 0.3
            continue
        
        # === QUESTIONS (Q:) ===
        if line.startswith('Q:') or line.startswith('Q :') or line.startswith('س:'):
            c.setFillColor(colors.HexColor('#2980B9'))
            font_size = 11
            
            if is_arabic_text and has_arabic_font:
                c.setFont("Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", font_size)
                wrapped_lines = wrap_text_arabic(line, c, "Amiri-Bold" if os.path.exists(font_bold_path) else "Amiri", 
                                                font_size, max_text_width)
                for wrapped_line in wrapped_lines:
                    reshaped = arabic_reshaper.reshape(wrapped_line)
                    bidi = get_display(reshaped)
                    c.drawRightString(margin_right, y_position, bidi)
                    y_position -= line_height
            else:
                c.setFont("Helvetica-Bold", font_size)
                wrapped_lines = wrap_text_latin(line, c, "Helvetica-Bold", font_size, max_text_width)
                for wrapped_line in wrapped_lines:
                    c.drawString(margin_left, y_position, wrapped_line)
                    y_position -= line_height
            
            continue
        
        # === RÉPONSES (R:) ===
        if line.startswith('R:') or line.startswith('R :') or line.startswith('ج:'):
            c.setFillColor(colors.HexColor('#16A085'))
            font_size = 11
            
            if is_arabic_text and has_arabic_font:
                c.setFont("Amiri", font_size)
                wrapped_lines = wrap_text_arabic(line, c, "Amiri", font_size, max_text_width - 0.5*cm)
                for wrapped_line in wrapped_lines:
                    reshaped = arabic_reshaper.reshape(wrapped_line)
                    bidi = get_display(reshaped)
                    c.drawRightString(margin_right - 0.5*cm, y_position, bidi)
                    y_position -= line_height
            else:
                c.setFont("Helvetica", font_size)
                wrapped_lines = wrap_text_latin(line, c, "Helvetica", font_size, max_text_width - 0.5*cm)
                for wrapped_line in wrapped_lines:
                    c.drawString(margin_left + 0.5*cm, y_position, wrapped_line)
                    y_position -= line_height
            
            continue
        
        # === TEXTE NORMAL ===
        c.setFillColor(colors.HexColor('#2C3E50'))
        font_size = 11
        
        if is_arabic_text and has_arabic_font:
            c.setFont("Amiri", font_size)
            wrapped_lines = wrap_text_arabic(line, c, "Amiri", font_size, max_text_width)
            
            for wrapped_line in wrapped_lines:
                reshaped = arabic_reshaper.reshape(wrapped_line)
                bidi = get_display(reshaped)
                c.drawRightString(margin_right, y_position, bidi)
                y_position -= line_height
        else:
            c.setFont("Helvetica", font_size)
            wrapped_lines = wrap_text_latin(line, c, "Helvetica", font_size, max_text_width)
            
            for wrapped_line in wrapped_lines:
                c.drawString(margin_left, y_position, wrapped_line)
                y_position -= line_height
    
    draw_footer(page_num)
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# --- 5. INTERFACE UTILISATEUR (STREAMLIT) ---

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
                st.text(str(e))
