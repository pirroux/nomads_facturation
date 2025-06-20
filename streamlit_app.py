import streamlit as st
import os
from create_invoice_excel import create_invoice_dataframe, format_excel
import pandas as pd
from datetime import datetime
import pytz
import json
from pathlib import Path
from pdf_extractor import extract_text_from_pdf
from data_extractor import extract_data
import tempfile

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
                # Traiter directement les fichiers uploadés sans les sauvegarder
                all_invoices_data = {}

                for uploaded_file in uploaded_files:
                    try:
                        # Créer un fichier temporaire pour l'extraction
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name

                        # Extraire le texte du PDF
                        pages_text = extract_text_from_pdf(tmp_path)
                        if not pages_text:
                            st.error(f"Impossible d'extraire le texte de {uploaded_file.name}")
                            continue

                        # Fusionner le texte de toutes les pages
                        combined_text = "\n\n".join(pages_text)

                        # Déterminer le type de facture
                        is_internet = "UGS" in combined_text
                        is_acompte = "Facture d'acompte" in combined_text

                        if is_internet:
                            facture_type = "internet"
                        elif is_acompte:
                            facture_type = "acompte"
                        else:
                            facture_type = "meg"

                        # Extraire les données structurées
                        extracted_data = extract_data(combined_text, facture_type)

                        # Structure de base pour les données
                        data = {
                            'type': facture_type,
                            'articles': extracted_data.get('articles', []),
                            'TOTAL': extracted_data.get('TOTAL', {
                                'total_ht': 0,
                                'total_ttc': 0,
                                'tva': 0,
                                'remise': 0
                            }),
                            'client_name': extracted_data.get('client_name', ''),
                            'numero_facture': extracted_data.get('numero_facture', ''),
                            'date_facture': extracted_data.get('date_facture', ''),
                            'date_commande': extracted_data.get('date_commande', ''),
                            'commentaire': extracted_data.get('commentaire', ''),
                            'Type_Vente': extracted_data.get('Type_Vente', ''),
                            'Réseau_Vente': extracted_data.get('Réseau_Vente', ''),
                            'nombre_articles': len(extracted_data.get('articles', []))
                        }

                        # Ajouter au dictionnaire principal
                        all_invoices_data[uploaded_file.name] = {
                            'text': combined_text,
                            'data': data
                        }

                        st.success(f"✓ {uploaded_file.name} traité avec succès")

                        # Nettoyer le fichier temporaire
                        os.unlink(tmp_path)

                    except Exception as e:
                        st.error(f"Erreur lors du traitement de {uploaded_file.name}: {str(e)}")
                        continue

                # Vérifier si des données ont été trouvées
                if all_invoices_data:
                    try:
                        df = create_invoice_dataframe(all_invoices_data)

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
                            st.write(f"Nombre de factures traitées : {len(all_invoices_data)}")

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
                        st.write("Données extraites :", all_invoices_data)
                else:
                    st.error("Aucune donnée extraite des fichiers uploadés. Veuillez réessayer.")

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
