import os 
import json
import threading
from dotenv import load_dotenv
import gspread
import discord
from discord.ext import tasks, commands
from fastapi import FastAPI
import uvicorn
import recherche  

# ----------------------------
# Charger les variables d'environnement
# ----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "20"))
STATE_FILE = "sheet_state.json"

# ----------------------------
# Récupération des credentials Google depuis la variable d'environnement
# ----------------------------
cred_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not cred_json:
    raise ValueError("La variable d'environnement GOOGLE_CREDENTIALS_JSON est vide !")

try:
    creds_dict = json.loads(cred_json)
except json.JSONDecodeError as e:
    raise ValueError(f"Erreur JSON dans GOOGLE_CREDENTIALS_JSON : {e}")

# Corriger les \n dans la clé privée
if "private_key" in creds_dict:
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ----------------------------
# Setup Discord
# ----------------------------
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Charger le cog recherche
recherche.setup(bot)

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
# Événement on_ready
# ----------------------------
@bot.event
async def on_ready():
    print(f"✅ Connecté comme {bot.user} (id: {bot.user.id})")
    poll_sheet.start()

# ----------------------------
# Boucle de vérification
# ----------------------------
@tasks.loop(seconds=POLL_SECONDS)
async def poll_sheet():
    try:
        ws = get_sheet()
        rows = ws.get_all_values()

        meaningful_rows = [r for r in rows if len(r) > 22 and r[22].strip() != ""]
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

            price = last_row[32] if len(last_row) > 32 else "N/A"
            color = last_row[33] if len(last_row) > 33 else "N/A"

            def stars(value):
                try:
                    val = int(value)
                    return "⭐" * val if val > 0 else "❌"
                except:
                    return "N/A"

            engine = stars(last_row[26] if len(last_row) > 26 else 0)
            brake = stars(last_row[27] if len(last_row) > 27 else 0)
            transmission = stars(last_row[28] if len(last_row) > 28 else 0)
            suspension = stars(last_row[29] if len(last_row) > 29 else 0)

            turbo_val = last_row[30] if len(last_row) > 30 else "FALSE"
            turbo = "✅" if turbo_val.upper() == "TRUE" else "❌"

            msg = (
                f"🚗 **Nouvelle voiture disponible !**\n\n"
                f"📛 **Nom** : {car_name}\n"
                f"💰 **Prix** : {price}\n"
                f"🎨 **Couleur** : {color}\n"
                f"⭐ **VIP** : {vip}\n\n"
                f"🏁 **Niveaux** :\n"
                f"- Moteur : {engine}\n"
                f"- Frein : {brake}\n"
                f"- Transmission : {transmission}\n"
                f"- Suspension : {suspension}\n"
                f"- Turbo : {turbo}"
            )

            await ch.send(msg)

            # ➝ notification aux abonnés (via recherche.py)
            cog = bot.get_cog("Recherche")
            if cog:
                await cog.notify_users(car_name, msg)

            state["last_value"] = car_name
            save_state(state)

    except Exception as e:
        print("Erreur lors du polling :", e)

# ----------------------------
# Serveur FastAPI pour keep-alive (Render/UptimeRobot)
# ----------------------------
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Bot actif"}

@app.head("/")
def head_root():
    return {}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

# Lancer FastAPI en parallèle du bot Discord
threading.Thread(target=run_web, daemon=True).start()

# ----------------------------
# Lancement du bot
# ----------------------------
if __name__ == "__main__":
    bot.run(TOKEN)
