import os, json, threading, asyncio
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
from fastapi import FastAPI
import uvicorn

from sheets_api import get_all_cars, get_user_subscriptions
from discord_views import CarSelectionView, CarSearchModal

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "20"))
STATE_FILE = "sheet_state.json"

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- FastAPI Keep-alive ----------------
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

# ---------------- Commandes ----------------
@bot.command()
async def recherche(ctx):
    """Poste le panneau interactif"""
    view = CarSelectionView()
    embed = discord.Embed(title="Sélection de voitures", description="Tapez un mot-clé pour rechercher vos voitures.\nUtilisez le menu pour ajouter ou retirer vos abonnements.\nUtilisez ⬅️ et ➡️ pour naviguer entre les pages.")
    msg = await ctx.send(embed=embed, view=view)
    await ctx.send("💡 Cliquez sur le champ de recherche pour filtrer vos voitures.")

@bot.command()
async def mesvoitures(ctx):
    """Affiche la liste des voitures suivies par l'utilisateur"""
    user_id = ctx.author.id
    cars = get_user_subscriptions(user_id)
    if not cars:
        await ctx.send("🚗 Vous ne suivez encore aucune voiture.")
    else:
        await ctx.send("🚗 Vos abonnements :\n" + "\n".join(cars))

# ----------------------------
# Boucle de vérification
# ----------------------------
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
            # Envoyer le message au channel public (inchangé)
            ch = bot.get_channel(CHANNEL_ID)
            if ch is None:
                print(f"⚠️ Channel Discord avec ID {CHANNEL_ID} non trouvé.")
            else:
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

            # ---------------- Envoi DM aux abonnés ----------------
            subscribers = get_user_subscriptions_by_car(car_name)  # fonction à créer
            for user_id in subscribers:
                user = bot.get_user(int(user_id))
                if user:
                    try:
                        await user.send(f"🔔 Bonne nouvelle ! La voiture **{car_name}** est disponible !")
                    except Exception as e:
                        print(f"Impossible d'envoyer DM à {user_id} : {e}")

            # Mettre à jour l'état
            state["last_value"] = car_name
            save_state(state)

    except Exception as e:
        print("Erreur lors du polling :", e)

if __name__ == "__main__":
    bot.run(TOKEN)
