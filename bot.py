import os, json, threading, asyncio
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
from fastapi import FastAPI
import uvicorn

from sheets_api import ws_bdd, get_all_cars, get_user_subscriptions, get_user_subscriptions_by_car
from discord_views import CarSelectionView

# ---------------------------- Charger les variables d'environnement ----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "20"))
STATE_FILE = "sheet_state.json"

# ---------------------------- Intents Discord ----------------------------
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------- Gestion de l'état ----------------------------
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

# ---------------------------- FastAPI Keep-alive ----------------------------
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Bot actif"}

@app.head("/")
def head_root():
    return {}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

threading.Thread(target=run_web, daemon=True).start()

# ---------------------------- Commandes Discord ----------------------------
@bot.command()
async def recherche(ctx):
    """Poste le panneau interactif"""
    view = CarSelectionView(user_id=ctx.author.id)  # injecte user_id
    embed = discord.Embed(
        title="Sélection de voitures",
        description=(
            "💡 Tapez un mot-clé pour rechercher vos voitures.\n"
            "Utilisez le menu pour ajouter ou retirer vos abonnements.\n"
            "Cliquez sur 'Voir mes véhicules' pour gérer vos abonnements."
        )
    )
    await ctx.send(embed=embed, view=view)

# ---------------------------- Connexion Google Sheets ----------------------------
def get_sheet_data():
    """Récupère toutes les lignes de la feuille BDD"""
    return ws_bdd.get_all_values()

# ---------------------------- Boucle de vérification ----------------------------
@tasks.loop(seconds=POLL_SECONDS)
async def poll_sheet():
    try:
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, get_sheet_data)

        # Filtrer les lignes significatives (colonne 23 = car_name)
        meaningful_rows = [r for r in rows if len(r) > 22 and r[22].strip() != ""]
        if not meaningful_rows:
            return

        last_row = meaningful_rows[-1]
        car_name = last_row[22].strip()
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
            else:
                vip = last_row[21] if len(last_row) > 21 else "Non VIP"
                vip = vip if vip.strip() and vip.upper() != "NULL" else "Non VIP"
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

            # DM aux abonnés
            subscribers = get_user_subscriptions_by_car(car_name)
            for user_id in subscribers:
                user = bot.get_user(int(user_id))
                if user:
                    try:
                        await user.send(f"🔔 Bonne nouvelle ! La voiture **{car_name}** est disponible !")
                    except Exception as e:
                        print(f"Impossible d'envoyer DM à {user_id} : {e}")

            # Mise à jour de l'état
            state["last_value"] = car_name
            save_state(state)

    except Exception as e:
        print("Erreur lors du polling :", e)

# ---------------------------- on_ready ----------------------------
@bot.event
async def on_ready():
    print(f"✅ Connecté comme {bot.user} (id: {bot.user.id})")
    if not poll_sheet.is_running():
        poll_sheet.start()

# ---------------------------- Lancement du bot ----------------------------
if __name__ == "__main__":
    bot.run(TOKEN)
