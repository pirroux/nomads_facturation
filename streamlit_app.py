import streamlit as st
import os
from create_invoice_excel import create_excel_from_data, load_invoice_data, create_invoice_dataframe, format_excel
import pandas as pd
from datetime import datetime
import pytz
import json
from pathlib import Path

# Set page configuration (must be the first Streamlit command)
st.set_page_config(
    page_title="Analyse de Factures PDF",
    page_icon="📊",
    layout="centered"
)

# Centrer le titre Nomads Surfing
st.markdown("<h1 style='text-align: center;'>Nomads Surfing 🌊</h1>", unsafe_allow_html=True)

# Centrer le sous-titre sur une seule ligne
st.markdown("<h2 style='text-align: center;'>Analyse automatique de factures PDF 🏄‍♂️</h2>", unsafe_allow_html=True)

# Upload multiple PDF files
uploaded_files = st.file_uploader(" ", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write("📄 Fichier chargé :", uploaded_file.name)

    # Bouton pour lancer l'analyse
    if st.button("Analyser"):
        try:
            with st.spinner("🔄 Analyse en cours..."):
                # Sauvegarder les fichiers PDF dans le dossier data_factures/facturesv7 (même dossier que dans le script principal)
                os.makedirs('data_factures/facturesv7', exist_ok=True)
                for file in uploaded_files:
                    with open(f'data_factures/facturesv7/{file.name}', 'wb') as f:
                        f.write(file.getvalue())

                # Force la régénération du fichier factures.json
                json_path = Path('factures.json')
                if json_path.exists():
                    json_path.unlink()

                # Charger les données des factures
                all_invoices_data = load_invoice_data()

                # Filtrer uniquement les fichiers uploadés
                uploaded_filenames = [f.name for f in uploaded_files]
                filtered_invoices_data = {}

                # Parcourir toutes les factures et les ajouter si elles correspondent aux fichiers uploadés
                for filename, data in all_invoices_data.items():
                    # Vérifier si le nom de fichier commence par un des noms de fichiers uploadés
                    for uploaded_filename in uploaded_filenames:
                        if filename.startswith(uploaded_filename):
                            filtered_invoices_data[filename] = data

                            # Correction spécifique pour les factures 990 et 994
                            if "FAC00000990" in filename or "FAC00000994" in filename:
                                total_ttc = data.get('data', {}).get('TOTAL', {}).get('total_ttc', 0)
                                if total_ttc > 0:
                                    st.info(f"Correction appliquée pour la facture {filename}: solde = {total_ttc} €")
                            break

                # Vérifier si des données ont été trouvées
                if filtered_invoices_data:
                    try:
                        df = create_invoice_dataframe(filtered_invoices_data)

                        if not df.empty:
                            # Correction spécifique pour les factures 990 et 994 dans le DataFrame
                            for index, row in df.iterrows():
                                if "990" in str(row['N° Syst.']) or "994" in str(row['N° Syst.']):
                                    if row['Credit TTC'] > 0:
                                        df.at[index, 'solde'] = row['Credit TTC']
                                        st.info(f"Correction solde pour {row['N° Syst.']} - Nouveau solde: {row['Credit TTC']} €")

                            # Générer le nom du fichier avec timestamp
                            paris_tz = pytz.timezone('Europe/Paris')
                            current_time = datetime.now(paris_tz)
                            timestamp = current_time.strftime('%y%m%d%H%M%S')
                            filename = f'factures_auto_{timestamp}.xlsx'

                            # Créer le fichier Excel avec formatage
                            os.makedirs('temp_files', exist_ok=True)
                            excel_path = os.path.join('temp_files', filename)

                            with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
                                df.to_excel(writer, sheet_name='Factures', index=False)
                                format_excel(writer, df)

                            # Proposer le téléchargement via Streamlit
                            with open(excel_path, 'rb') as f:
                                excel_data = f.read()

                            st.success(f"📂 Fichier Excel créé avec succès ! 🤙")
                            st.write(f"Nombre de factures traitées : {len(filtered_invoices_data)}")

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

        except Exception as e:
            st.error(f"🚨 Une erreur est survenue : {str(e)}")
            st.exception(e)  # Afficher la trace complète de l'erreur pour un meilleur débogage

def process_and_create_excel():
    """Fonction simple qui utilise create_excel_from_data"""
    try:
        # This function is not being used, consider removing it
        pass
    except Exception as e:
        st.error(f"Erreur lors de la création de l'Excel : {str(e)}")
        return None, None
