import re
from datetime import datetime
from typing import Dict, List

class InvoiceExtractor:
    def __init__(self):
        """
        Initialise l'extracteur
        """
        pass  # Plus besoin des credentials Google Cloud

    def extract_amounts(self, text: str, invoice_type: str) -> Dict:
        """
        Extrait les montants selon le type de facture
        """
        amounts = {
            'total_ttc': 0.0,
            'total_ht': 0.0,
            'tva': 0.0,
            'frais_expedition': 0.0,
            'type_expedition': "" if invoice_type == 'internet' else None,
            'remise': ''  # Ajout du champ remise
        }

        if invoice_type == 'internet':
            # Patterns plus précis pour factures internet
            total_pattern = r'Total\s+([\d\s]+[,.]?\d*)\s*€\s*\(dont\s+([\d\s]+[,.]?\d*)\s*€\s*TVA\)'
            expedition_pattern = r'Expédition\s+(?:([^€\n]*?)(?:(\d+[,.]?\d*)\s*€)?)?\s*(?:\(TTC\))?\s*(?:via\s*)?([^\n]*?)(?=\s*(?:Total|$))'

            # Extraction total TTC et TVA
            total_match = re.search(total_pattern, text, re.IGNORECASE)
            if total_match:
                amounts['total_ttc'] = self.convert_to_float(total_match.group(1))
                amounts['tva'] = self.convert_to_float(total_match.group(2))
                amounts['total_ht'] = amounts['total_ttc'] - amounts['tva']

            # Extraction frais et type d'expédition
            expedition_match = re.search(expedition_pattern, text, re.IGNORECASE)
            if expedition_match:
                if expedition_match.group(2):  # Si on a un montant
                    amounts['frais_expedition'] = self.convert_to_float(expedition_match.group(2))
                # Combine les parties du type d'expédition (avant et après le montant)
                type_expedition = ' '.join(filter(None, [
                    expedition_match.group(1),
                    expedition_match.group(3)
                ])).strip()
                if type_expedition:
                    amounts['type_expedition'] = type_expedition

        elif invoice_type == 'meg':
            # Patterns spécifiques pour les totaux dans les factures MEG
            total_ht_pattern = r'Total\s+HT\s+([\d\s]+[,.]?\d*)\s*€'
            tva_pattern = r'TVA\s+([\d\s]+[,.]?\d*)\s*€'
            total_ttc_pattern = r'Total\s+TTC\s+([\d\s]+[,.]?\d*)\s*€'

            # Vérifier si c'est une facture multi-pages
            page_indicators = re.findall(r'Page\s+(\d+)\s+de\s+(\d+)', text)
            is_multipage = len(page_indicators) > 0

            # Si c'est une facture multi-pages, essayer une approche de page par page
            if is_multipage:
                print(f"Facture multi-pages détectée: {len(page_indicators)} indicateurs de page trouvés")

                # Diviser par les indicateurs "Page X de Y"
                pages = []
                last_pos = 0

                # Trouver chaque début de page en utilisant le motif "Page X de Y"
                page_positions = [(m.start(), m.group()) for m in re.finditer(r'Page\s+\d+\s+de\s+\d+', text)]

                if page_positions:
                    # Ajouter tout ce qui précède la première occurrence comme page 1
                    if page_positions[0][0] > 0:
                        pages.append(text[:page_positions[0][0]])

                    # Diviser le reste du texte par les indicateurs de page
                    for i in range(len(page_positions)):
                        start = page_positions[i][0] + len(page_positions[i][1])
                        end = page_positions[i+1][0] if i+1 < len(page_positions) else len(text)
                        pages.append(text[start:end])

                    # Chercher d'abord les montants dans la dernière page ou l'avant-dernière
                    # (car les totaux sont souvent là)
                    for page_index in range(len(pages)-1, -1, -1):
                        page_content = pages[page_index]

                        # Chercher la section "Détail de la TVA" dans cette page
                        if 'Détail de la TVA' in page_content:
                            section = page_content.split('Détail de la TVA')[1]

                            # Extraction total HT
                            total_ht_match = re.search(total_ht_pattern, section)
                            if total_ht_match:
                                amounts['total_ht'] = self.convert_to_float(total_ht_match.group(1))

                            # Extraction TVA
                            tva_match = re.search(tva_pattern, section)
                            if tva_match:
                                amounts['tva'] = self.convert_to_float(tva_match.group(1))

                            # Extraction total TTC
                            total_ttc_match = re.search(total_ttc_pattern, section)
                            if total_ttc_match:
                                amounts['total_ttc'] = self.convert_to_float(total_ttc_match.group(1))

                            # Si on a trouvé tous les montants, on peut sortir
                            if amounts['total_ht'] > 0 and amounts['tva'] > 0 and amounts['total_ttc'] > 0:
                                print("Tous les montants trouvés, arrêt de la recherche page par page")
                                break

                        # Si on n'a pas trouvé la section "Détail de la TVA", chercher directement les montants
                        else:
                            # Extraction total HT
                            if amounts['total_ht'] == 0:
                                total_ht_match = re.search(total_ht_pattern, page_content)
                                if total_ht_match:
                                    amounts['total_ht'] = self.convert_to_float(total_ht_match.group(1))

                            # Extraction TVA
                            if amounts['tva'] == 0:
                                tva_match = re.search(tva_pattern, page_content)
                                if tva_match:
                                    amounts['tva'] = self.convert_to_float(tva_match.group(1))

                            # Extraction total TTC
                            if amounts['total_ttc'] == 0:
                                total_ttc_match = re.search(total_ttc_pattern, page_content)
                                if total_ttc_match:
                                    amounts['total_ttc'] = self.convert_to_float(total_ttc_match.group(1))

            # Si ce n'est pas une facture multi-pages ou si l'approche par page n'a pas fonctionné,
            # essayer avec l'approche originale améliorée (texte entier)
            if amounts['total_ht'] == 0 or amounts['tva'] == 0 or amounts['total_ttc'] == 0:
                # Pour les factures multi-pages, s'assurer que les recherches sont indépendantes des sauts de ligne
                processed_text = text.replace('\n\n', ' ')

                # Chercher d'abord dans la section "Détail de la TVA"
                detail_tva_section = None
                if 'Détail de la TVA' in processed_text:
                    # Diviser le texte à "Détail de la TVA" et prendre tout ce qui suit
                    sections = processed_text.split('Détail de la TVA')
                    if len(sections) > 1:
                        detail_tva_section = sections[1]

                # Si on a trouvé la section, chercher les montants dedans
                if detail_tva_section:
                    # Extraction total HT si pas encore trouvé
                    if amounts['total_ht'] == 0:
                        total_ht_match = re.search(total_ht_pattern, detail_tva_section)
                        if total_ht_match:
                            amounts['total_ht'] = self.convert_to_float(total_ht_match.group(1))

                    # Extraction TVA si pas encore trouvé
                    if amounts['tva'] == 0:
                        tva_match = re.search(tva_pattern, detail_tva_section)
                        if tva_match:
                            amounts['tva'] = self.convert_to_float(tva_match.group(1))

                    # Extraction total TTC si pas encore trouvé
                    if amounts['total_ttc'] == 0:
                        total_ttc_match = re.search(total_ttc_pattern, detail_tva_section)
                        if total_ttc_match:
                            amounts['total_ttc'] = self.convert_to_float(total_ttc_match.group(1))
                else:
                    # Si on n'a pas trouvé la section, chercher dans tout le texte

                    # Extraction total HT si pas encore trouvé
                    if amounts['total_ht'] == 0:
                        total_ht_match = re.search(total_ht_pattern, processed_text)
                        if total_ht_match:
                            amounts['total_ht'] = self.convert_to_float(total_ht_match.group(1))

                    # Extraction TVA si pas encore trouvé
                    if amounts['tva'] == 0:
                        tva_match = re.search(tva_pattern, processed_text)
                        if tva_match:
                            amounts['tva'] = self.convert_to_float(tva_match.group(1))

                    # Extraction total TTC si pas encore trouvé
                    if amounts['total_ttc'] == 0:
                        total_ttc_match = re.search(total_ttc_pattern, processed_text)
                        if total_ttc_match:
                            amounts['total_ttc'] = self.convert_to_float(total_ttc_match.group(1))

            # Si on n'a pas trouvé les totaux, essayer avec d'autres patterns plus flexibles
            if amounts['total_ht'] == 0 or amounts['tva'] == 0 or amounts['total_ttc'] == 0:
                # Patterns alternatifs qui fonctionnent même avec des sauts de page/ligne
                alt_total_ht_pattern = r'(?:Total|Montant)\s+(?:HT|H\.T\.)\D*([\d\s]+[,.]?\d*)\s*€'
                alt_tva_pattern = r'(?:TVA|T\.V\.A\.)\D*([\d\s]+[,.]?\d*)\s*€'
                alt_total_ttc_pattern = r'(?:Total|Montant)\s+(?:TTC|T\.T\.C\.)\D*([\d\s]+[,.]?\d*)\s*€'

                if amounts['total_ht'] == 0:
                    alt_match = re.search(alt_total_ht_pattern, text, re.IGNORECASE)
                    if alt_match:
                        amounts['total_ht'] = self.convert_to_float(alt_match.group(1))

                if amounts['tva'] == 0:
                    alt_match = re.search(alt_tva_pattern, text, re.IGNORECASE)
                    if alt_match:
                        amounts['tva'] = self.convert_to_float(alt_match.group(1))

                if amounts['total_ttc'] == 0:
                    alt_match = re.search(alt_total_ttc_pattern, text, re.IGNORECASE)
                    if alt_match:
                        amounts['total_ttc'] = self.convert_to_float(alt_match.group(1))

            # Vérifications et calculs
            if amounts['total_ht'] > 0 and amounts['tva'] > 0 and amounts['total_ttc'] == 0:
                amounts['total_ttc'] = amounts['total_ht'] + amounts['tva']
                print(f"Total TTC calculé: {amounts['total_ttc']} €")
            elif amounts['total_ttc'] > 0 and amounts['tva'] > 0 and amounts['total_ht'] == 0:
                amounts['total_ht'] = amounts['total_ttc'] - amounts['tva']
                print(f"Total HT calculé: {amounts['total_ht']} €")
            elif amounts['total_ttc'] > 0 and amounts['total_ht'] > 0 and amounts['tva'] == 0:
                amounts['tva'] = amounts['total_ttc'] - amounts['total_ht']
                print(f"TVA calculée: {amounts['tva']} €")

        # Recherche d'une remise totale
        remise_patterns = [
            r'Remise\s+(?:totale|globale)?\s*:?\s*(-?\d+[.,]?\d*)\s*[€%]',
            r'Remise\s+(-?\d+[.,]?\d*)\s*[€%]',
            r'Total\s+remise\s*:?\s*(-?\d+[.,]?\d*)\s*[€%]'
        ]

        # Pour les remises, chercher dans tout le texte
        for pattern in remise_patterns:
            remise_match = re.search(pattern, text, re.IGNORECASE)
            if remise_match:
                # Convertir la valeur de remise en float
                remise_value = self.convert_to_float(remise_match.group(1))
                # S'assurer que la remise est toujours positive, même si elle est négative dans la facture
                amounts['remise'] = abs(remise_value)
                print(f"Remise trouvée: {amounts['remise']}")
                break

        return amounts

    def convert_to_float(self, amount_str: str) -> float:
        """
        Convertit une chaîne de montant en float
        """
        return float(amount_str.replace(',', '.').replace(' ', ''))

    def detect_invoice_type(self, text: str) -> str:
        """
        Détecte le type de facture basé sur son contenu
        UGS en majuscule indique une facture internet
        Sinon c'est une facture MEG
        """
        # Recherche plus précise pour les factures internet
        internet_indicators = [
            "UGS",
            "N° de commande",
            "Date de commande",
            "Livraison gratuite"
        ]

        if any(indicator in text for indicator in internet_indicators):
            return "internet"
        return "meg"

    def extract_articles(self, text: str, invoice_type: str) -> List[Dict]:
        """
        Extrait les articles selon le type de facture
        """
        articles = []

        if invoice_type == 'internet':
            # Pattern simplifié pour articles internet
            code_pattern = r'UGS\s*:\s*([^\n]+)'
            current_code = ""

            # Ignore les lignes qui commencent par ces mots
            ignore_starts = ['UGS', 'Poids', 'Taille', 'Colori', 'Total', 'Sous-total', 'Expédition', 'En cas']

            for line in text.split('\n'):
                line = line.strip()

                # Ignore les lignes vides ou commençant par des mots à ignorer
                if not line or any(line.startswith(word) for word in ignore_starts):
                    if 'UGS' in line:
                        # Extraction du code UGS
                        match = re.search(code_pattern, line)
                        if match:
                            current_code = match.group(1).strip()
                    continue

                # Cherche un nombre (quantité) et un prix dans la ligne
                quantite_match = re.search(r'\s(\d+)\s+(\d+[,.]?\d*)\s*€', line)

                if quantite_match:
                    try:
                        description = line[:quantite_match.start()].strip()
                        quantite = int(quantite_match.group(1))
                        prix_unitaire = self.convert_to_float(quantite_match.group(2))

                        articles.append({
                            'reference': current_code,
                            'description': description,
                            'quantite': quantite,
                            'prix_unitaire': prix_unitaire,
                            'montant_ht': 0.0,  # Par défaut
                            'tva': 0.0,         # Par défaut
                            'remise': 0.0       # Par défaut
                        })
                        current_code = ""  # Réinitialise le code pour le prochain article
                    except (ValueError, IndexError) as e:
                        # Exception silencieuse
                        continue

        elif invoice_type == 'meg':
            # Pattern pour les articles MEG (code existant)
            article_pattern = (
                r'ART(\d+)\s*-\s*([^\n]+?)\s*'  # Référence et description
                r'(\d+,\d+)\s*'                 # Quantité
                r'(\d+[\s\d]*,\d+)\s*€\s*'      # Prix unitaire
                r'(\d+,\d+)%\s*'                # Remise
                r'(\d+[\s\d]*,\d+)\s*€\s*'      # Montant HT
                r'(\d+,\d+)%'                   # TVA
            )

            for match in re.finditer(article_pattern, text, re.MULTILINE | re.DOTALL):
                try:
                    prix_unitaire = match.group(4).replace(' ', '')
                    montant_ht = match.group(6).replace(' ', '')

                    articles.append({
                        'reference': f"ART{match.group(1)}",
                        'description': match.group(2).strip(),
                        'quantite': float(match.group(3).replace(',', '.')),
                        'prix_unitaire': float(prix_unitaire.replace(',', '.')),
                        'remise': float(match.group(5).replace(',', '.')) / 100,
                        'montant_ht': float(montant_ht.replace(',', '.')),
                        'tva': float(match.group(7).replace(',', '.'))
                    })
                except (IndexError, ValueError) as e:
                    # Exception silencieuse
                    continue

        return articles

    def extract_invoice_data(self, text: str) -> Dict:
        """
        Extrait les données structurées du texte de la facture
        """
        # Détection du type de facture
        invoice_type = self.detect_invoice_type(text)

        # Structure de base des données
        data = {
            'type': invoice_type,
            'articles': [],
            'nombre_articles': 0,
            'TOTAL': {
                'total_ttc': 0.0,
                'total_ht': 0.0,
                'tva': 0.0,
                'frais_expedition': 0.0
            },
            'Réseau_Vente': "",
            'Type_Vente': "",
            'commentaire': "",
            'statut_paiement': "Payé" if invoice_type == 'internet' else "",
            'reglement': "carte bancaire" if invoice_type == 'internet' else "",
            'numero_client': "",
            'client_name': "",
            'date_facture': "",
            'date_commande': ""
        }

        # Patterns adaptés selon le type de facture
        patterns = {
            'numero_facture': (
                r'N° de facture\s*:\s*([^\n]+)' if invoice_type == 'internet'
                else r'N°\s*:\s*([A-Z0-9-]+)'
            ),
            'date_facture': (
                r'Date de facture\s*:\s*(\d{1,2}\s+\w+\s+\d{4})' if invoice_type == 'internet'
                else r'Date[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})'
            ),
            'date_commande': (
                r'Date de commande\s*:\s*(\d{1,2}\s+\w+\s+\d{4})' if invoice_type == 'internet'
                else None
            ),
            'numero_client': r'N°\s*client\s*:\s*(CLT\d+)',
            'client_name': (
                # Pour les factures internet
                r'FACTURE\s*\n(?!.*?NOMADS)([^\n]+?)(?:\s*N°\s*(?:de\s*facture|de\s*commande)|Résidence|Date|$)' if invoice_type == 'internet'
                # Pour les factures MEG
                else r'N°\s*client\s*:\s*(?:CLT\d+)\s*\n(?!.*?NOMADS)([^\n]+?)(?:\s*NOMADS|\s*$)'
            ),
            'Réseau_Vente': r'20\.(?:0[1-9]|10)\.\d{2}',  # Pattern pour 20.XX.XX complet
            'Type_Vente': r'20\.(?:0[1-9]|10)',  # Pattern pour 20.XX uniquement
            'commentaire': r'Commentaire\s*:\s*([^\n]+)',
            'statut_paiement': r'Statut paiement\s*:\s*([^\n]+)',
            'reglement': r'Règlement\s*:?\s*([^\n]+)' if invoice_type == 'meg' else None
        }

        # Extraction des informations de base
        for key, pattern in patterns.items():
            if pattern:
                if key in ['Réseau_Vente', 'Type_Vente']:
                    # Recherche dans tout le texte
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        data[key] = match.group(0)
                else:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        # Vérification supplémentaire pour client_name
                        if key == 'client_name':
                            if value and 'NOMADS' not in value.upper():
                                data[key] = value
                        elif key == 'reglement' and invoice_type == 'meg' and ('cheque' in value.lower() or 'chèque' in value.lower()):
                            value = 'cheque'
                        else:
                            data[key] = value
                    elif key == 'numero_facture' and invoice_type == 'internet':
                        # Si pas de numéro de facture, essayer le numéro de commande
                        commande_match = re.search(r'N° de commande\s*:\s*(\d+)', text)
                        if commande_match:
                            data[key] = commande_match.group(1).strip()

        # Extraction des articles
        articles = self.extract_articles(text, invoice_type)
        data['articles'] = articles
        data['nombre_articles'] = len(articles)

        # Extraction des montants
        amounts = self.extract_amounts(text, invoice_type)
        data['TOTAL'].update(amounts)

        # Conversion des dates
        for date_key in ['date_facture', 'date_commande']:
            if data.get(date_key):
                try:
                    date_fr = data[date_key]
                    mois_fr = {
                        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
                        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
                        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
                    }
                    for mois, num in mois_fr.items():
                        date_fr = date_fr.replace(mois, num)
                    jour, mois, annee = re.match(r'(\d{1,2})\s*(\d{2})\s*(\d{4})', date_fr).groups()
                    data[date_key] = f"{annee}-{mois}-{jour.zfill(2)}"
                except (ValueError, AttributeError):
                    pass

        return {
            "invoice_data": data,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
