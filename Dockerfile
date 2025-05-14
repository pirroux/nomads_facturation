# Utiliser une image Python officielle comme base
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances système nécessaires pour pdfplumber
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p data_factures/facturesv7 temp_files

# Exposer le port utilisé par Streamlit
EXPOSE 8501

# Définir la commande pour démarrer l'application
CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0"]
