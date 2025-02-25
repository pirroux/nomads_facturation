import pandas as pd
from datetime import datetime
import json
import re
import pytz  # Pour gérer les fuseaux horaires
from pathlib import Path
from openpyxl import Workbook
import os

def load_invoice_data():
    """Charge les données des factures depuis le fichier JSON"""
    try:
        with open('factures.json', 'r', encoding='utf-8') as f:
            invoices_data = json.load(f)

            # Calculer le nombre total d'articles pour chaque facture
            for invoice in invoices_data.values():
                articles = invoice['data'].get('articles', [])
                total_quantity = sum(article.get('quantite', 0) for article in articles)  # Ensure to use .get() to avoid KeyError
                invoice['data']['nombre_articles'] = total_quantity  # Mettre à jour le nombre d'articles

            return invoices_data
    except FileNotFoundError:
        print("Erreur: Le fichier factures.json n'a pas été trouvé")
        return {}
    except json.JSONDecodeError:
        print("Erreur: Le fichier factures.json n'est pas un JSON valide")
        return {}

def save_invoice_data(invoices_data):
    """Sauvegarde les données des factures dans le fichier JSON"""
    try:
        with open('factures.json', 'w', encoding='utf-8') as f:
            json.dump(invoices_data, f, ensure_ascii=False, indent=2)
        print("Factures sauvegardées avec succès.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des factures: {str(e)}")

def format_date(date_str: str) -> str:
    """Convertit une date YYYY-MM-DD en MM/DD/YYYY"""
    if not date_str:
        return ''
    try:
        year, month, day = date_str.split('-')
        return f"{month}/{day}/{year}"
    except ValueError:
        return date_str

def create_invoice_dataframe(invoices_data):
    """Crée un DataFrame à partir des données des factures"""
    headers = [
        'Type-facture', 'n°ordre', 'saisie', 'Syst', 'N° Syst.', 'comptable', 'Type_facture',
        'Type_Vente', 'Réseau_Vente', 'Client', 'Typologie', 'Banque créditée',
        'Date commande', 'Date facture', 'Date expédition', 'Commentaire',
        'date1', 'acompte1', 'date2', 'acompte2', 'Date solde', 'solde',
        'contrôle paiement', 'reste dû', 'AVO', 'tva', 'ttc', 'Credit TTC',
        'Credit HT', 'remise', 'TVA Collectee', 'quantité'
    ]

    # Ajouter les headers pour les articles
    for i in range(1, 21):
        headers.extend([f'supfam{i}', f'fam{i}', f'ref{i}', f'q{i}', f'prix{i}',
                      f'r€{i}', f'ht{i}', f'tva€{i}'])

    rows = []
    for filename, invoice in invoices_data.items():
        try:
            data = invoice['data']
            row = {col: '' for col in headers}  # Initialiser toutes les colonnes avec des valeurs vides

            # Calculer la quantité totale
            total_quantity = sum(article.get('quantite', 0) for article in data.get('articles', []))
            row['quantité'] = total_quantity  # Mettre à jour la colonne 'quantité'

            # Extraire la date
            date = data.get('date', '')
            if data.get('type') == 'internet' and 'text' in invoice:
                date_match = re.search(r'Date de commande\s*:\s*(\d{1,2}\s*\w+\s*\d{4})', invoice['text'])
                if date_match:
                    date_fr = date_match.group(1).strip()
                    mois_fr = {
                        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
                        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
                        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
                    }
                    for mois, num in mois_fr.items():
                        date_fr = date_fr.replace(mois, num)
                    jour, mois, annee = re.match(r'(\d{1,2})\s*(\d{2})\s*(\d{4})', date_fr).groups()
                    date = f"{annee}-{mois}-{jour.zfill(2)}"

            # Extraire les informations d'acompte
            acompte_match = re.search(r'Echéance\(s\)\s*Acompte\s*de\s*(\d+[\s\d]*,\d+)\s*€\s*au\s*(\d{2}/\d{2}/\d{4})', invoice['text'])
            if acompte_match:
                montant_acompte = float(acompte_match.group(1).replace(' ', '').replace(',', '.'))
                date_acompte = acompte_match.group(2)
                jour, mois, annee = date_acompte.split('/')
                date_acompte_iso = f"{annee}-{mois}-{jour}"
            else:
                montant_acompte = ''
                date_acompte_iso = ''

            # Calculer le taux de TVA et le total HT avec remise
            total_ht = data['TOTAL']['total_ht']
            remise = data['TOTAL'].get('remise', 0)
            # Appliquer la remise si elle existe
            if remise:
                total_ht = total_ht - float(remise)
            total_ttc = data['TOTAL']['total_ttc']

            if data.get('type') == 'meg':
                taux_tva = f"{data['articles'][0]['tva']:.2f}%".replace('.', ',') if data['articles'] else ''
            else:
                if total_ht and total_ht != 0:
                    taux_tva = f"{((total_ttc / total_ht) - 1) * 100:.2f}%".replace('.', ',')
                else:
                    taux_tva = ''

            # Remplir les données dans l'ordre exact des colonnes
            row['Type-facture'] = " "
            row['n°ordre'] = " "
            row['saisie'] = ''
            row['Syst'] = 'MEG' if data.get('type') == 'meg' else 'Internet'
            row['N° Syst.'] = data.get('numero_facture', '')
            row['comptable'] = ''
            row['Type_facture'] = ''
            row['Type_Vente'] = data.get('Type_Vente', '')
            row['Réseau_Vente'] = data.get('Réseau_Vente', '')
            row['Client'] = data.get('client_name', '')
            row['Typologie'] = ''
            row['Banque créditée'] = ''
            row['Date commande'] = format_date(data.get('date_commande', ''))
            row['Date facture'] = format_date(data.get('date_facture', ''))
            row['Date expédition'] = ''
            row['Commentaire'] = data.get('commentaire', '')
            row['date1'] = format_date(date_acompte_iso if 'date_acompte_iso' in locals() else '')
            row['acompte1'] = montant_acompte if 'montant_acompte' in locals() else ''
            row['date2'] = ''
            row['acompte2'] = ''
            row['Date solde'] = ''
            row['solde'] = data.get('TOTAL', {}).get('total_ttc', 0)
            row['contrôle paiement'] = data.get('statut_paiement', '')
            row['reste dû'] = data.get('TOTAL', {}).get('total_ttc', 0) - data.get('TOTAL', {}).get('total_ttc', 0)
            row['AVO'] = ''
            row['tva'] = taux_tva
            row['ttc'] = ''
            row['Credit TTC'] = data.get('TOTAL', {}).get('total_ttc', 0)
            row['Credit HT'] = total_ht  # Utiliser le total HT avec remise
            row['remise'] = remise
            row['TVA Collectee'] = data.get('TOTAL', {}).get('tva', 0)

            # Remplir les articles
            articles = data.get('articles', [])
            for i, article in enumerate(articles, 1):
                if i > 20:
                    break

                # Calculs des montants
                if data.get('type') == 'meg':
                    prix_ht = article.get('prix_unitaire', 0)
                    montant_ht = article.get('montant_ht', 0)
                    taux_tva_decimal = article.get('tva', 0) / 100
                    tva_euros = montant_ht * taux_tva_decimal
                else:
                    prix_ttc = article.get('prix_unitaire', 0)
                    taux_tva = ((total_ttc / total_ht) - 1) if total_ht > 0 else 0
                    prix_ht = prix_ttc / (1 + taux_tva)
                    montant_ht = prix_ht * article.get('quantite', 1)
                    tva_euros = montant_ht * taux_tva

                row[f'supfam{i}'] = ''
                row[f'fam{i}'] = ''
                row[f'ref{i}'] = article.get('reference', '')
                row[f'q{i}'] = article.get('quantite', '')
                row[f'prix{i}'] = round(prix_ht, 2)
                row[f'r€{i}'] = article.get('remise', '')
                row[f'ht{i}'] = round(montant_ht, 2)
                row[f'tva€{i}'] = round(tva_euros, 2)

            rows.append(row)

        except Exception as e:
            print(f"Erreur lors du traitement de {filename}: {str(e)}")
            continue

    # Créer le DataFrame en respectant l'ordre exact des colonnes
    df = pd.DataFrame(rows)
    return df[headers]  # Forcer l'ordre exact des colonnes

def format_excel(writer, df):
    """Applique le formatage au fichier Excel"""
    try:
        workbook = writer.book
        worksheet = writer.sheets['Factures']

        # Définir la largeur des colonnes
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            ) + 2
            worksheet.set_column(idx, idx, max_length)

        # Créer des formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'bg_color': '#D9E1F2',
            'border': 1
        })

        # Appliquer le format aux en-têtes
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

    except Exception as e:
        print(f"Erreur lors du formatage Excel: {str(e)}")

def create_excel_from_data(invoices_data):
    """Crée un fichier Excel à partir des données des factures"""
    # Initialiser le DataFrame
    rows = []

    for filename, invoice in invoices_data.items():
        try:
            # Les données sont dans invoice['data']['invoice_data']
            invoice_data = invoice.get('data', {}).get('invoice_data', {})

            # Accéder aux totaux via invoice_data
            totals = invoice_data.get('TOTAL', {})

            row = {
                'Type-facture': " ",
                'n°ordre': " ",
                'saisie': '',
                'Syst': 'MEG' if invoice_data.get('type') == 'meg' else 'Internet',
                'N° Syst.': invoice_data.get('numero_facture', ''),
                'comptable': '',
                'Type_facture': '',
                'Type_Vente': invoice_data.get('Type_Vente', ''),
                'Réseau_Vente': invoice_data.get('Réseau_Vente', ''),
                'Client': invoice_data.get('client_name', ''),
                'Total HT': totals.get('total_ht', 0),
                'Total TTC': totals.get('total_ttc', 0),
                'TVA': totals.get('tva', 0),
                'remise': totals.get('remise', 0)
            }
            rows.append(row)
        except Exception as e:
            print(f"Erreur lors du traitement de {filename}: {str(e)}")
            continue

    # Créer le DataFrame
    df = pd.DataFrame(rows)

    # Sauvegarder en Excel
    excel_path = "temp_files/factures.xlsx"
    df.to_excel(excel_path, index=False)

    # Save the updated invoices data to factures.json
    save_invoice_data(invoices_data)

    return Path(excel_path)

def main():
    try:
        # Charger les données
        invoices_data = load_invoice_data()
        if not invoices_data:
            print("Aucune donnée à traiter")
            return

        # Créer le DataFrame
        df = create_invoice_dataframe(invoices_data)
        if df.empty:
            print("Aucune donnée valide à exporter")
            return

        # Générer le nom du fichier avec la date et l'heure au format YYMMDDHHMMSS en GMT+1
        paris_tz = pytz.timezone('Europe/Paris')
        current_time = datetime.now(paris_tz)

        # Format détaillé :
        # %y : année sur 2 chiffres
        # %m : mois sur 2 chiffres
        # %d : jour sur 2 chiffres
        # %H : heure sur 2 chiffres (format 24h)
        # %M : minutes sur 2 chiffres
        # %S : secondes sur 2 chiffres
        timestamp = current_time.strftime('%y%m%d%H%M%S')

        filename = f'factures_auto_{timestamp}.xlsx'

        # Créer le fichier Excel avec formatage
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Factures', index=False)
            format_excel(writer, df)

        print(f"Fichier Excel créé : {filename}")

    except Exception as e:
        print(f"Erreur lors de l'exécution: {str(e)}")

if __name__ == "__main__":
    main()
