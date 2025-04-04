import pdfplumber
import os
from pathlib import Path

def extract_text_from_pdf(pdf_path):
    """
    Extrait le texte d'un fichier PDF, page par page.

    Args:
        pdf_path (str): Chemin vers le fichier PDF

    Returns:
        list: Liste de textes extraits, un par page
    """
    try:
        if not os.path.exists(pdf_path):
            print(f"Le fichier {pdf_path} n'existe pas.")
            return []

        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
                else:
                    pages_text.append("")  # Page vide

        return pages_text
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte du PDF {pdf_path}: {str(e)}")
        return []

def main():
    """Fonction principale pour tester l'extraction de texte"""
    pdf_folder = Path("data_factures/facturesv3")

    if not pdf_folder.exists():
        print(f"Le dossier {pdf_folder} n'existe pas.")
        return

    for pdf_path in pdf_folder.glob("*.pdf"):
        print(f"Traitement de {pdf_path.name}...")
        pages_text = extract_text_from_pdf(str(pdf_path))
        if pages_text:
            print(f"Texte extrait avec succès ({len(pages_text)} pages)")
            for i, text in enumerate(pages_text):
                print(f"- Page {i+1}: {len(text)} caractères")
                # Afficher les 100 premiers caractères pour vérification
                if text:
                    print(f"  Aperçu: {text[:100]}...")
        else:
            print(f"Échec de l'extraction du texte de {pdf_path.name}")

if __name__ == "__main__":
    main()
