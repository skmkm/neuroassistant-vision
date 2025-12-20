import streamlit as st
import os
import requests
import cloudinary
import cloudinary.uploader
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
from io import BytesIO
from PIL import Image

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Neuro-Sortie (Vision AI)",
    layout="centered"
)

# =========================
# ENV VARIABLES
# =========================
N8N_WEBHOOK = os.getenv("https://drchoulli.app.n8n.cloud/webhook-test/neuroassistant-vision")
cloudinary.config(
    cloud_name=os.getenv("dg7wbulwt"),
    api_key=os.getenv("249434414629186"),
    api_secret=os.getenv("ruC39Cwcem43hdeJFF2U6M3u5Go"),
    secure=True
)

# =========================
# FONT SETUP
# =========================
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
FONT_PATH = "Amiri-Regular.ttf"

if not os.path.exists(FONT_PATH):
    r = requests.get(FONT_URL)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)

# =========================
# PDF CLASS
# =========================
class ArabicPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Amiri", "", FONT_PATH, uni=True)
        self.set_font("Amiri", "", 14)

    def rtl(self, text):
        return get_display(arabic_reshaper.reshape(text))

    def write_rtl(self, text):
        self.multi_cell(0, 10, self.rtl(text))

def generate_pdf(text, language):
    pdf = ArabicPDF()
    pdf.add_page()

    if language in ["Arabe Classique", "Darija (Maroc)"]:
        pdf.write_rtl(text)
    else:
        pdf.multi_cell(0, 10, text)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# =========================
# CLOUDINARY UPLOAD
# =========================
def upload_to_cloudinary(file):
    result = cloudinary.uploader.upload(
        file,
        folder="neuroassistant_crh",
        resource_type="image"
    )
    return result["secure_url"]

# =========================
# STREAMLIT UI
# =========================
st.title("🧠 Neuro-Sortie (Vision AI)")

mode = st.radio("Input type", ["Text Input", "Camera/Image Upload"])

language = st.selectbox(
    "Language",
    ["Français", "Darija (Maroc)", "Arabe Classique"]
)

model = st.selectbox(
    "Model",
    ["gpt-4o", "gpt-4o-mini"]
)

text_input = ""
image_url = ""

if mode == "Text Input":
    text_input = st.text_area("Paste CRH or medical report", height=250)
else:
    uploaded = st.file_uploader(
        "Upload CRH Image",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded:
        st.image(uploaded, caption="Uploaded CRH", use_column_width=True)
        with st.spinner("Uploading securely..."):
            image_url = upload_to_cloudinary(uploaded)

# =========================
# GENERATE PDF ACTION
# =========================
if st.button("📄 Generate PDF", use_container_width=True):

    if mode == "Text Input" and not text_input.strip():
        st.error("Please provide medical text.")
        st.stop()

    if mode == "Camera/Image Upload" and not image_url:
        st.error("Please upload an image.")
        st.stop()

    payload = {
        "input_type": "image" if image_url else "text",
        "language": language,
        "model": model,
        "image_url": image_url,
        "text": text_input
    }

    with st.spinner("Analyzing medical data..."):
        try:
            response = requests.post(N8N_WEBHOOK, json=payload)
            response.raise_for_status()
            patient_text = response.json()["patient_guide"]
        except Exception as e:
            st.error(f"Error contacting AI backend: {e}")
            st.stop()

        pdf = generate_pdf(patient_text, language)

    st.success("Patient Exit Guide Generated")

    st.download_button(
        "⬇️ Download PDF",
        pdf,
        file_name="Neuro_Sortie_Patient.pdf",
        mime="application/pdf"
    )
