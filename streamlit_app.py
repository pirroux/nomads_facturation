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

# Set page configuration (must be the first Streamlit command)
st.set_page_config(
    page_title="Analyse de Factures PDF",
    page_icon="📊",
    layout="centered"
)

# Function to reload environment variables
def reload_env():
    load_dotenv()

# Initial load of environment variables
reload_env()

# Set the path to the service account key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

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
                    all_invoices_data = load_invoice_data()

                    # Filter only the uploaded files
                    uploaded_filenames = [f.name for f in uploaded_files]

                    # Debug information
                    st.write("Fichiers disponibles dans factures.json:", list(all_invoices_data.keys()))
                    st.write("Fichiers uploadés:", uploaded_filenames)

                    filtered_invoices_data = {
                        filename: data
                        for filename, data in all_invoices_data.items()
                        if filename in uploaded_filenames
                    }

                    # Vérifier si des données ont été trouvées
                    if filtered_invoices_data:
                        try:
                            df = create_invoice_dataframe(filtered_invoices_data)

                            if not df.empty:
                                # Generate the filename with timestamp
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
                                st.error("Le DataFrame généré est vide. Veuillez vérifier les données.")
                        except Exception as e:
                            st.error(f"Erreur lors de la création du fichier Excel : {str(e)}")
                            st.write("Données filtrées :", filtered_invoices_data)
                    else:
                        st.error("Aucune donnée trouvée pour les fichiers uploadés. Veuillez réessayer.")

                else:
                    st.error(f"❌ Erreur lors de l'analyse (Status {response.status_code})")

        except Exception as e:
            st.error(f"🚨 Une erreur est survenue : {str(e)}")

def process_and_create_excel():
    """Fonction simple qui utilise create_excel_from_data"""
    try:
        # This function is not being used, consider removing it
        pass
    except Exception as e:
        st.error(f"Erreur lors de la création de l'Excel : {str(e)}")
        return None, None
