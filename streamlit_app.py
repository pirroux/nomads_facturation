import streamlit as st
import requests
import base64
import os
from dotenv import load_dotenv
from create_invoice_excel import create_excel_from_data, load_invoice_data, create_invoice_dataframe, format_excel
from google.cloud import storage
import pandas as pd
from datetime import datetime
import pytz

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration de l'API endpoint
API_URL = os.getenv("API_URL", "http://fastapi:8000")
PROJECT_ID = os.getenv("PROJECT_ID", "nomadsfacturation")

# Vérification des variables d'environnement
if not PROJECT_ID:
    st.error("PROJECT_ID is not set in the environment variables.")

# Initialiser le client Storage
try:
    storage_client = storage.Client()
    bucket_name = f"{PROJECT_ID}-temp-files"
    bucket = storage_client.bucket(bucket_name)
except Exception as e:
    st.error(f"Error initializing Google Cloud Storage: {str(e)}")

# Set page configuration (must be the first Streamlit command)
st.set_page_config(
    page_title="Analyse de Factures PDF",
    page_icon="📊",
    layout="centered"
)

# Centrer le titre Nomads Surfing
st.markdown("<h1 style='text-align: center;'>Nomads Surfing 🌊</h1>", unsafe_allow_html=True)

# Centrer le sous-titre sur une seule ligne
st.markdown("<h2 style='text-align: center;'>Analyse automatique de factures PDF</h2>", unsafe_allow_html=True)

# Upload multiple PDF files
uploaded_files = st.file_uploader(" ", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write("📄 Fichier chargé :", uploaded_file.name)

    # Bouton pour lancer l'analyse
    if st.button("Analyser"):
        try:
            with st.spinner("🔄 Analyse en cours..."):
                # Préparer les fichiers pour l'envoi
                files = [("files", (file.name, file.getvalue(), "application/pdf")) for file in uploaded_files]

                # Envoyer tous les fichiers en une seule requête
                response = requests.post(f"{API_URL}/analyze_pdfs/", files=files, timeout=60)

                if response.status_code == 200:
                    st.success("✅ Analyse des documents terminée avec succès ! 🎉")

                    # Load the invoice data after processing
                    invoices_data = load_invoice_data()

                    # Create the Excel file using the create_invoice_dataframe function
                    # This ensures that the total quantities are calculated correctly
                    df = create_invoice_dataframe(invoices_data)

                    # Generate the filename with timestamp (same as in create_invoice_excel.py)
                    paris_tz = pytz.timezone('Europe/Paris')
                    current_time = datetime.now(paris_tz)
                    timestamp = current_time.strftime('%y%m%d%H%M%S')
                    filename = f'factures_auto_{timestamp}.xlsx'

                    # Create the Excel file with formatting
                    os.makedirs('temp_files', exist_ok=True)
                    excel_path = os.path.join('temp_files', filename)

                    # Use the same Excel formatting logic as in create_invoice_excel.py
                    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name='Factures', index=False)
                        format_excel(writer, df)

                    # Provide download link for the generated Excel file
                    with open(excel_path, 'rb') as f:
                        excel_data = f.read()

                    st.success(f"📂 Fichier Excel créé avec succès ! 🤙")

                    # Proposer le téléchargement via Streamlit
                    st.download_button(
                        label=f"📎 Télécharger {filename}",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                else:
                    st.error(f"❌ Erreur lors de l'analyse (Status {response.status_code})")

        except Exception as e:
            st.error(f"🚨 Une erreur est survenue : {str(e)}")

# Ensure this is called to update the data
invoices_data = load_invoice_data()

def process_and_create_excel():
    """Fonction simple qui utilise create_excel_from_data"""
    try:
        # Charger les données
        invoices_data = load_invoice_data()

        # Utiliser directement la fonction de create_invoice_excel.py
        df = create_invoice_dataframe(invoices_data)

        # Generate the filename with timestamp (same as in create_invoice_excel.py)
        paris_tz = pytz.timezone('Europe/Paris')
        current_time = datetime.now(paris_tz)
        timestamp = current_time.strftime('%y%m%d%H%M%S')
        filename = f'factures_auto_{timestamp}.xlsx'

        # Create the Excel file with formatting
        os.makedirs('temp_files', exist_ok=True)
        excel_path = os.path.join('temp_files', filename)

        # Use the same Excel formatting logic as in create_invoice_excel.py
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Factures', index=False)
            format_excel(writer, df)

        # Lire le fichier Excel créé
        with open(excel_path, 'rb') as f:
            excel_data = f.read()

        return excel_data, filename

    except Exception as e:
        st.error(f"Erreur lors de la création de l'Excel : {str(e)}")
        return None, None
