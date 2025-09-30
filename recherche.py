import os
import json
import discord
from discord.ext import commands
from discord.ui import View, Select

PREFS_FILE = "user_preferences.json"

def load_prefs():
    if not os.path.exists(PREFS_FILE):
        return {}
    try:
        with open(PREFS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return {}

def save_prefs(prefs):
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)

user_prefs = load_prefs()

class Recherche(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Commande !recherche
    @commands.command(name="recherche")
    async def recherche(self, ctx):
        options = [
            discord.SelectOption(label="Voiture 1"),
            discord.SelectOption(label="Voiture 2"),
            discord.SelectOption(label="Voiture 3"),
        ]

        select = Select(
            placeholder="Choisis une ou plusieurs voitures...",
            min_values=1,
            max_values=len(options),
            options=options
        )

        async def select_callback(interaction):
            user_id = str(interaction.user.id)
            selected = select.values
            user_prefs[user_id] = selected
            save_prefs(user_prefs)
            await interaction.response.send_message(
                f"✅ Tes préférences ont été enregistrées : {', '.join(selected)}",
                ephemeral=True
            )

        select.callback = select_callback
        view = View()
        view.add_item(select)

        await ctx.send("🚗 Tu recherches une voiture en particulier ?", view=view)

    # Méthode pour notifier les abonnés
    async def notify_users(self, car_name, msg):
        for user_id, prefs in user_prefs.items():
            if car_name in prefs:
                user = await self.bot.fetch_user(int(user_id))
                try:
                    await user.send(f"🔔 Bonne nouvelle ! La voiture **{car_name}** est disponible :\n\n{msg}")
                except Exception as e:
                    print(f"Impossible d’envoyer un DM à {user_id} : {e}")

def setup(bot):
    bot.add_cog(Recherche(bot))
