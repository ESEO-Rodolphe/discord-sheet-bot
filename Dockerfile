# Image Python officielle
FROM python:3.11-slim-bullseye

# Dossier de travail dans le container
WORKDIR /app

# Copier et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du projet
COPY bot.py .

# Commande pour démarrer le bot
CMD ["python", "-u", "bot.py"]
