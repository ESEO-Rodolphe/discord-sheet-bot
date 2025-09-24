import os, json, asyncio
from dotenv import load_dotenv
import gspread
import discord
from discord.ext import tasks, commands

# Charger variables du .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CRED_FILE = os.getenv("GOOGLE_CREDENTIALS", "credentials.json")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "20"))
STATE_FILE = "sheet_state.json"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_row": 0}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

def get_sheet():
    gc = gspread.service_account(filename=CRED_FILE)
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet("BDD")   # <-- on lit ta feuille BDD
    return ws

state = load_state()

@bot.event
async def on_ready():
    print(f"✅ Connecté comme {bot.user} (id: {bot.user.id})")
    poll_sheet.start()

@tasks.loop(seconds=POLL_SECONDS)
async def poll_sheet():
    try:
        ws = get_sheet()
        rows = ws.get_all_values()  # récupère toutes les lignes

        # Ne garder que les lignes où colonne W (index 22) n'est pas vide
        meaningful_rows = [r for r in rows if len(r) > 22 and r[22].strip() != ""]

        if not meaningful_rows:
            return

        last_row = meaningful_rows[-1]
        car_name = last_row[22]
        prev_value = state.get("last_value", None)

        # Premier lancement → initialisation sans envoi
        if prev_value is None:
            state["last_value"] = car_name
            save_state(state)
            print(f"Initialisé avec la voiture '{car_name}' (aucun envoi).")
            return

        # Nouvelle voiture détectée
        if car_name != prev_value:
            ch = bot.get_channel(CHANNEL_ID)

            # Récupération des autres infos avec fallback si colonne manquante
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

            # Message Discord
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

            # Met à jour l'état
            state["last_value"] = car_name
            save_state(state)

    except Exception as e:
        print("Erreur:", e)

if __name__ == "__main__":
    bot.run(TOKEN)
