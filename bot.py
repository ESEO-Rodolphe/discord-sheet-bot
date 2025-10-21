import os, json, threading, asyncio
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
from fastapi import FastAPI
import uvicorn

from sheets_api import ws_bdd, get_user_subscriptions_by_car
from discord_views import CarSelectionView, CarSearchModal

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
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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

# ---------------------------- File d'attente de DMs sécurisée ----------------------------
dm_queue = asyncio.Queue()

async def dm_worker():
    """Traite la file d'attente des DMs en série pour éviter le flood."""
    while True:
        user_id, message = await dm_queue.get()
        try:
            user = await bot.fetch_user(user_id)
            await user.send(message)
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"⚠️ Erreur envoi DM à {user_id} : {e}")
        finally:
            dm_queue.task_done()

# ---------------------------- Connexion Google Sheets ----------------------------
def get_sheet_data():
    """Récupère toutes les lignes de la feuille BDD"""
    return ws_bdd.get_all_values()

# ---------------------------- Commandes Discord ----------------------------

@bot.tree.command(name="recherche", description="Rechercher un véhicule et s’abonner.")
async def recherche(interaction: discord.Interaction):
    """Ouvre directement le modal de recherche"""
    view = CarSelectionView()
    modal = CarSearchModal(view)
    await interaction.response.send_modal(modal)
    # le reste (sélecteur) se gère dans le modal
    # message effacé automatiquement par Discord (slash command éphémère)


@bot.tree.command(name="selection", description="Voir ou modifier vos abonnements.")
async def selection(interaction: discord.Interaction):
    """Affiche les abonnements actuels de l’utilisateur (éphémère)."""
    view = CarSelectionView()
    await view.show_my_cars(interaction)  # Envoie un message éphémère
    # visible uniquement par l’utilisateur

@bot.command()
async def help(ctx):
    """Affiche un guide des commandes disponibles."""
    embed = discord.Embed(
        title="📘 Aide du bot",
        description=(
            "**/recherche** → Rechercher un véhicule et s’abonner.\n"
            "**/selection** → Voir ou modifier vos abonnements actuels.\n\n"
        ),
        color=discord.Color.blue()
    )
    try:
        await ctx.author.send(embed=embed)
        await ctx.send(f"{ctx.author.mention}, je t’ai envoyé l’aide en message privé.", delete_after=10)
    except Exception as e:
        print("Erreur envoi aide :", e)
    finally:
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass


# ---------------------------- Boucle de vérification ----------------------------
@tasks.loop(seconds=POLL_SECONDS)
async def poll_sheet():
    try:
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, get_sheet_data)

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
                        return "❌"

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

            subscribers = get_user_subscriptions_by_car(car_name)
            for user_id_str in subscribers:
                try:
                    user_id = int(user_id_str)
                    await dm_queue.put((
                        user_id,
                        f"🔔 Nouvelle voiture dispo : **{car_name}** !\n"
                    ))
                except Exception as e:
                    print(f"Erreur ajout file DM : {e}")

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
    bot.loop.create_task(dm_worker())
    try:
        synced = await bot.tree.sync()
        print(f"📡 {len(synced)} commandes slash synchronisées.")
    except Exception as e:
        print(f"Erreur sync slash commands : {e}")

# ---------------------------- Lancement du bot ----------------------------
if __name__ == "__main__":

    async def main():
        try:
            await bot.start(TOKEN)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print("⚠️ Rate limited by Discord — arrêt du bot pour éviter un blocage IP.")
            else:
                raise e

    asyncio.run(main())
