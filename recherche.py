import discord
from discord.ext import commands
from discord.ui import View, Select
import gspread
import json
from bot import creds_dict, SPREADSHEET_ID

USER_ID_COL = 35  # AI
PREFS_COL   = 36  # AJ
CAR_COL     = 3   # C
CAR_START_ROW = 2

# -----------------------
# Google Sheets
# -----------------------
def get_sheet():
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh.worksheet("BDD")

def get_available_cars():
    ws = get_sheet()
    try:
        cars = ws.col_values(CAR_COL)[CAR_START_ROW - 1:]  # Ignorer l'entête
        cars = list(filter(None, cars))
        return sorted(list(set(cars)))  # unique + tri alphabétique
    except Exception as e:
        print("Erreur get_available_cars:", e)
        return ["Voiture 1", "Voiture 2", "Voiture 3"]

# -----------------------
# View
# -----------------------
class RechercheView(View):
    def __init__(self, save_callback):
        super().__init__(timeout=None)
        self.save_callback = save_callback
        options = [discord.SelectOption(label=car) for car in get_available_cars()]
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
        selected = self.select.values
        await self.save_callback(user_id, selected)
        await interaction.response.send_message(
            f"✅ Tes préférences ont été enregistrées : {', '.join(selected)}",
            ephemeral=True
        )

# -----------------------
# Cog
# -----------------------
class Recherche(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ws = get_sheet()
        self.user_prefs = {}  # stocke en mémoire
        self.load_prefs_from_sheet()
        self.view = RechercheView(self.save_pref)

    def load_prefs_from_sheet(self):
        try:
            user_ids = self.ws.col_values(USER_ID_COL)
            prefs_col = self.ws.col_values(PREFS_COL)
            for uid, val in zip(user_ids, prefs_col):
                if uid.strip() and val.strip():
                    try:
                        self.user_prefs[uid] = json.loads(val)
                    except:
                        self.user_prefs[uid] = []
        except Exception as e:
            print("Erreur load_prefs:", e)

    async def save_pref(self, user_id, selected):
        try:
            self.user_prefs[user_id] = selected
            user_ids = self.ws.col_values(USER_ID_COL)
            if str(user_id) in user_ids:
                row = user_ids.index(str(user_id)) + 1
                self.ws.update_cell(row, PREFS_COL, json.dumps(selected))
            else:
                new_row = [""] * (USER_ID_COL - 1) + [str(user_id)] + [json.dumps(selected)]
                self.ws.append_row(new_row)
        except Exception as e:
            print("Erreur save_pref:", e)

    @commands.command(name="recherche")
    async def recherche(self, ctx):
        await ctx.send(
            "🚗 Tu recherches une voiture en particulier ?",
            view=self.view
        )

    async def notify_users(self, car_name):
        for user_id, selected in self.user_prefs.items():
            if car_name in selected:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    await user.send(
                        f"🔔 Bonne nouvelle ! La voiture **{car_name}** est disponible !"
                    )
                except Exception as e:
                    print(f"Impossible d’envoyer un DM à {user_id} : {e}")

async def setup(bot):
    await bot.add_cog(Recherche(bot))
