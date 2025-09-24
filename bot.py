import os
import json
from dotenv import load_dotenv
import gspread
import discord
from discord.ext import tasks, commands
import asyncio
from fastapi import FastAPI
import threading
import uvicorn

# ----------------------------
# Charger les variables d'environnement
# ----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "20"))
STATE_FILE = "sheet_state.json"
HTTP_PORT = int(os.getenv("HTTP_PORT", "8000"))  # Port pour UptimeRobot

# ----------------------------
# Récupération des credentials Google depuis la variable d'environnement
# ----------------------------
cred_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not cred_json:
    raise ValueError("La variable d'environnement GOOGLE_CREDENTIALS_JSON est vide !")

creds_dict = json.loads(cred_json)
if "private_key" in creds_dict:
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ----------------------------
# Setup Discord
# ----------------------------
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------------
# Gestion de l'état
# ----------------------------
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"last_value": None}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_value": None}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        print("Erreur lors de la sauvegarde de l'état :", e)

state = load_state()

# ----------------------------
# Connexion Google Sheets
# ----------------------------
def get_sheet():
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet("BDD")
    return ws

# ----------------------------
# Boucle de vérification
# ----------------------------
@tasks.loop(seconds=POLL_SECONDS)
async def poll_sheet():
    try:
        ws = get_sheet()
        rows = ws.get_all_values()
        meaningful_rows = [r for r in rows if len(r) > 22 and r[22].strip() != ""]

        # ===== DEBUG =====
        if meaningful_rows:
            print("DEBUG:", len(rows), "lignes totales,", len(meaningful_rows), 
                  "lignes significatives,", "last_row_name:", meaningful_rows[-1][22])
        else:
            print("DEBUG: aucune ligne significative trouvée")
        # =================

        if not meaningful_rows:
            return

        last_row = meaningful_rows[-1]
        car_name = last_row[22]
        prev_value = state.get("last_value")

        if prev_value is None:
            state["last_value"] = car_name
            save_state(state)
            print(f"Initialisé avec la voiture '{car_name}' (aucun envoi).")
            return

        if car_name != prev_value:
            ch = bot.get_channel(CHANNEL_ID)
            if ch is None:
                print(f"⚠️ Channel Discord avec ID {CHANNEL_ID} non trouvé.")
                return

            vip = last_row[21] if len(last_row) > 21 else "Non VIP"
            if vip.strip() == "" or vip.upper() == "NULL":
                vip = "Non VIP"

            price = last_row[23] if len(last_row) > 23 else "N/A"
            engine = "⭐" * int(last_row[26]) if len(last_row) > 26 and last_row[26].isdigit() else "❌"
            brake = "⭐" * int(last_row[27]) if len(last_row) > 27 and last_row[27].isdigit() else "❌"
            transmission = "⭐" * int(last_row[28]) if len(last_row) > 28 and last_row[28].isdigit() else "❌"
            suspension = "⭐" * int(last_row[29]) if len(last_row) > 29 and last_row[29].isdigit() else "❌"
            turbo_val = last_row[30] if len(last_row) > 30 else "FALSE"
            turbo = "✅" if turbo_val.upper() == "TRUE" else "❌"

            msg = (
                f"🚗 **Nouvelle voiture disponible !**\n\n"
                f"📛 **Nom** : {car_name}\n"
                f"💰 **Prix** : {price}\n"
                f"⭐ **VIP** : {vip}\n\n"
                f"🏁 **Niveaux** :\n"
                f"- Moteur : {engine}\n"
                f"- Frein : {brake}\n"
                f"- Transmission : {transmission}\n"
                f"- Suspension : {suspension}\n"
                f"- Turbo : {turbo}"
            )

            await ch.send(msg)
            state["last_value"] = car_name
            save_state(state)

    except Exception as e:
        print("Erreur lors du polling :", e)

# ----------------------------
# Serveur HTTP minimal pour UptimeRobot
# ----------------------------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

def run_http():
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT)

# ----------------------------
# Lancement
# ----------------------------
if __name__ == "__main__":
    # Lancer le serveur HTTP en thread séparé
    threading.Thread(target=run_http, daemon=True).start()
    # Lancer le bot Discord
    bot.run(TOKEN)
