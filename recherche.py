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

# -----------------------
# View
# -----------------------
class RechercheView(View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label="Voiture 1"),
            discord.SelectOption(label="Voiture 2"),
            discord.SelectOption(label="Voiture 3"),
        ]

        self.select = Select(
            custom_id="select_voitures",
            placeholder="Choisis une ou plusieurs voitures...",
            min_values=1,
            max_values=len(options),
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        selected = self.select.values  # ✅ méthode officielle
        user_prefs[user_id] = selected

        # ✅ Sauvegarde immédiate
        save_prefs(user_prefs)

        await interaction.response.send_message(
            f"✅ Tes préférences ont été enregistrées : {', '.join(selected)}",
            ephemeral=True
        )

# -----------------------
# Cog
# -----------------------
class Recherche(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="recherche")
    async def recherche(self, ctx):
        # recharge les préférences depuis le JSON à chaque ouverture
        global user_prefs
        user_prefs = load_prefs()

        await ctx.send(
            "🚗 Tu recherches une voiture en particulier ?",
            view=RechercheView()
        )

    async def notify_users(self, car_name):
        global user_prefs
        user_prefs = load_prefs()  # ✅ Toujours lire les prefs sauvegardées

        for user_id, prefs in user_prefs.items():
            if car_name in prefs:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    await user.send(
                        f"🔔 Bonne nouvelle ! La voiture **{car_name}** est disponible !\n\n"
                        f"⚠️ Elle va bientôt être ajoutée au catalogue ! Si tu la veux, ouvre un ticket dans #nous-contacter"
                    )
                except Exception as e:
                    print(f"Impossible d’envoyer un DM à {user_id} : {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Recherche(bot))
