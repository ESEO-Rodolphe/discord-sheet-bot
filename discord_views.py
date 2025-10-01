import discord
from discord.ui import View, Select, Button, Modal, TextInput
from sheets_api import search_cars, get_user_subscriptions, add_subscription, remove_subscription

# ---------- Modal pour saisir un mot-clé ----------
class CarSearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Rechercher une voiture")
        self.view_ref = view
        self.keyword_input = TextInput(label="Mot-clé voiture", placeholder="Ex: Jug pour Jugular", required=True)
        self.add_item(self.keyword_input)

    async def on_submit(self, interaction: discord.Interaction):
        keyword = self.keyword_input.value
        await self.view_ref.update_options(interaction, keyword)

# ---------- Menu déroulant multi-sélection ----------
class CarSelect(Select):
    def __init__(self, options, view_ref, user_id):
        super().__init__(
            placeholder="Sélectionnez vos véhicules...",
            min_values=0,
            max_values=len(options),
            options=options
        )
        self.view_ref = view_ref
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        selected = self.values
        current = get_user_subscriptions(self.user_id)

        for car in selected:
            if car not in current:
                add_subscription(self.user_id, car)
                
        menu_cars = [opt.label for opt in self.options] 
        for car in menu_cars:
            if car in current and car not in selected:
                remove_subscription(self.user_id, car)

        await interaction.response.send_message(
            "✅ Vos abonnements ont été mis à jour.", 
            ephemeral=True, 
            delete_after=10
        )

        await self.view_ref.reset_view(interaction)

# ---------- Vue principale ----------
class CarSelectionView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

        # Bouton recherche
        search_btn = Button(label="🔍 Rechercher une voiture", style=discord.ButtonStyle.secondary)
        search_btn.callback = self.open_search_modal
        self.add_item(search_btn)

        # Bouton pour voir ses véhicules
        my_cars_btn = Button(label="🚗 Voir mes véhicules", style=discord.ButtonStyle.primary)
        my_cars_btn.callback = self.show_my_cars
        self.add_item(my_cars_btn)

    async def open_search_modal(self, interaction: discord.Interaction):
        modal = CarSearchModal(self)
        await interaction.response.send_modal(modal)

    async def update_options(self, interaction: discord.Interaction, keyword: str):
        cars = search_cars(keyword)[:25]  # Limite à 25
        user_subs = get_user_subscriptions(self.user_id)

        select_options = [
            discord.SelectOption(label=car, default=car in user_subs)
            for car in cars
        ]

        # Crée une View pour le Select
        view = View()
        view.add_item(CarSelect(select_options, self, self.user_id))

        await interaction.response.send_message("Sélectionnez vos voitures :", view=view, ephemeral=True)

    async def reset_view(self, interaction: discord.Interaction):
        """Réinitialise la vue principale"""
        # Édite le message original si possible
        try:
            await interaction.edit_original_response(view=self)
        except discord.errors.InteractionResponded:
            # Si déjà répondu, envoyer un nouveau message éphémère
            await interaction.followup.send("💡 Menu réinitialisé.", view=self, ephemeral=True)

    async def show_my_cars(self, interaction: discord.Interaction):
        """Affiche les véhicules de l'utilisateur avec possibilité de dé-sélectionner"""
        user_cars = get_user_subscriptions(self.user_id)[:25]  # Limite à 25
        if not user_cars:
            await interaction.response.send_message("🚗 Vous ne suivez encore aucune voiture.", ephemeral=True)
            return

        select_options = [
            discord.SelectOption(label=car, default=True)
            for car in user_cars
        ]

        view = View()
        view.add_item(CarSelect(select_options, self, self.user_id))
        await interaction.response.send_message("🚗 Vos véhicules (déselectionner pour retirer) :", view=view, ephemeral=True)
