import discord
from discord.ui import View, Select, Button, Modal, TextInput
from sheets_api import search_cars, get_user_subscriptions, add_subscription, remove_subscription

# ---------- Modal pour saisir un mot-clé ----------
class CarSearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Rechercher une voiture")
        self.view_ref = view
        self.keyword_input = TextInput(label="Mot-clé voiture", placeholder="Ex: BMW", required=True)
        self.add_item(self.keyword_input)

    async def on_submit(self, interaction: discord.Interaction):
        keyword = self.keyword_input.value
        await self.view_ref.update_options(interaction, keyword)

# ---------- Menu déroulant multi-sélection ----------
class CarSelect(Select):
    def __init__(self, options, view_ref):
        super().__init__(
            placeholder="Sélectionnez vos voitures...",
            min_values=0,
            max_values=len(options),
            options=options
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        selected = self.values
        current = get_user_subscriptions(user_id)

        # Ajouter nouvelles sélections
        for car in selected:
            if car not in current:
                add_subscription(user_id, car)

        # Supprimer décochées
        for car in current:
            if car not in selected:
                remove_subscription(user_id, car)

        await interaction.response.defer(ephemeral=True)
        await self.view_ref.refresh_menu(interaction)
        await interaction.followup.send("✅ Vos abonnements ont été mis à jour.", ephemeral=True)

# ---------- Vue principale avec bouton recherche et pagination ----------
class CarSelectionView(View):
    def __init__(self):
        super().__init__(timeout=None)  # View persistante
        self.current_options = []
        self.current_keyword = ""
        self.page = 0
        self.pages = []

        # Bouton pour ouvrir le Modal de recherche
        search_btn = Button(label="🔍 Rechercher une voiture", style=discord.ButtonStyle.secondary)
        search_btn.callback = self.open_search_modal
        self.add_item(search_btn)

    async def open_search_modal(self, interaction: discord.Interaction):
        modal = CarSearchModal(self)
        await interaction.response.send_modal(modal)

    async def update_options(self, interaction: discord.Interaction, keyword: str):
        self.current_keyword = keyword
        cars = search_cars(keyword)
        self.pages = [cars[i:i + 25] for i in range(0, len(cars), 25)]
        self.page = 0
        await self.refresh_menu(interaction)

    async def refresh_menu(self, interaction: discord.Interaction):
        self.clear_items()

        # Remettre le bouton recherche en haut
        search_btn = Button(label="🔍 Rechercher une voiture", style=discord.ButtonStyle.secondary)
        search_btn.callback = self.open_search_modal
        self.add_item(search_btn)

        if not self.pages or len(self.pages) == 0:
            await interaction.response.send_message("Aucune voiture trouvée.", ephemeral=True)
            return

        # Menu déroulant pour la page courante
        options_page = self.pages[self.page]
        user_id = interaction.user.id
        user_subs = get_user_subscriptions(user_id)

        select_options = [
            discord.SelectOption(label=car, default=car in user_subs)
            for car in options_page
        ]
        self.add_item(CarSelect(select_options, self))

        # Pagination si nécessaire
        if len(self.pages) > 1:
            prev_btn = Button(label="⬅️ Page précédente", style=discord.ButtonStyle.primary)
            next_btn = Button(label="➡️ Page suivante", style=discord.ButtonStyle.primary)
            prev_btn.callback = self.prev_page
            next_btn.callback = self.next_page
            self.add_item(prev_btn)
            self.add_item(next_btn)

        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        if self.page < len(self.pages) - 1:
            self.page += 1
            await self.refresh_menu(interaction)
        else:
            await interaction.response.send_message("➡️ Dernière page.", ephemeral=True)

    async def prev_page(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            await self.refresh_menu(interaction)
        else:
            await interaction.response.send_message("⬅️ Première page.", ephemeral=True)
