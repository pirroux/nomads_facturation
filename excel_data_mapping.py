from pathlib import Path
import json
from pdf_extractor import extract_text_from_pdf
from data_extractor import extract_data
import pandas as pd

def load_patterns() -> dict:
    """Charge les patterns de reconnaissance"""
    return {
        "general": {
            "Type-facture": r"(?i)N°\s*:\s*(FAC\d+)",
            "Client": r"(?i)(?:société|SARL|SA|SAS|EURL|SASU)?\s*([A-Z][A-Za-zÀ-ÿ\s\-']+)",
            "Date facture": r"(?i)Date\s*:\s*(\d{2}/\d{2}/\d{4})",
            "Credit TTC": r"Total\s+TTC\s*:?\s*(\d+[.,]\d+)\s*€"
        },
        "article_pattern": r"ART(\d+)\s*-([^\n]+?)\s+(\d+,\d+)\s+(\d+,\d+)\s*€\s*(\d+,\d+)%\s*(\d+,\d+)\s*€"
    }

def main():
    # Initialise les chemins
    pdf_folder = Path("data_factures")
    output_file = Path("factures.json")

    # Charge les patterns
    patterns = load_patterns()

    # Dictionnaire pour stocker toutes les factures
    all_invoices = {}

    # Traite chaque PDF
    for pdf_path in pdf_folder.glob("*.pdf"):
        try:
            print(f"\nTraitement de {pdf_path.name}...")

            # Extrait le texte
            text = extract_text_from_pdf(str(pdf_path))
            if not text:
                raise ValueError("Pas de texte extrait")

            # Extrait les données structurées
            data = extract_data(text, patterns)

            # Ajoute au dictionnaire principal
            all_invoices[pdf_path.name] = {
                'text': text,
                'data': data
            }

            print(f"✓ {pdf_path.name} traité avec succès")

        except Exception as e:
            print(f"✗ Erreur sur {pdf_path.name}: {str(e)}")
            all_invoices[pdf_path.name] = {
                'error': str(e)
            }

    # Sauvegarde toutes les factures dans un seul fichier JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_invoices, f, ensure_ascii=False, indent=2)
    print(f"\nToutes les factures ont été sauvegardées dans {output_file}")

if __name__ == "__main__":
    main()
