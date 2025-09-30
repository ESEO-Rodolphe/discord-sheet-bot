Discord Google Sheets Bot

Un bot Discord qui se connecte à une feuille Google Sheets et envoie une alerte lorsqu’une nouvelle voiture est ajoutée.
Hébergé gratuitement sur Render, avec un keep-alive assuré par UptimeRobot.

**- Fonctionnalités**
  - Se connecte à Google Sheets via gspread.
  - Vérifie automatiquement toutes les POLL_SECONDS secondes si une nouvelle entrée est disponible.
  - Envoie une notification formatée sur un salon Discord.
  - Hébergé sur Render avec un serveur FastAPI en parallèle.
  - Gardé actif grâce à un monitor UptimeRobot qui ping régulièrement l’API.

**- Variables d’environnement**
*À définir dans Render (onglet Environment Variables) ou via un fichier .env en local.*

  - **DISCORD_TOKEN**	*Token du bot Discord*
  - **CHANNEL_ID**	*ID du salon Discord où envoyer les alertes*
  - **SPREADSHEET_ID**	*ID de la feuille Google Sheets*
  - **POLL_SECONDS**	*(Optionnel) Intervalle en secondes entre deux vérifications*
  - **GOOGLE_CREDENTIALS_JSON**	*Credentials Google en JSON compact (copié/collé)*

**- Déploiement sur Render**
- Crée un repo GitHub avec ce projet.
- Connecte ton repo à Render → crée un Web Service.
- Dans l’onglet Environment Variables, configure toutes les variables listées plus haut.
- Déploie → ton bot se connecte à Discord et expose un serveur FastAPI sur *https://ton-service.onrender.com*.

**- Keep Alive avec UptimeRobot**
*Render met en veille les services gratuits si personne n’y accède pendant 15 minutes.*
Pour éviter cela :
- Va sur UptimeRobot.
- Crée un nouveau monitor HTTP(s).
- Branche à ton URL : *https://ton-service.onrender.com/*
- Intervalle : 5 minutes (minimum sur le plan gratuit).

**- Outils utilisés**
- discord.py → communication avec Discord.
- gspread → lecture de Google Sheets.
- FastAPI → API de keep-alive pour Render/UptimeRobot.
- Render → hébergement gratuit du bot.
- UptimeRobot → maintien en activité grâce aux pings réguliers.

  **Projet personnel pour GTA RP — librement réutilisable et modifiable.**
