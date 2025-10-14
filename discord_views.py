import discord
from discord.ui import View, Select, Button, Modal, TextInput
from sheets_api import search_cars, get_user_subscriptions, add_subscription, remove_subscription

class CarSearchModal(Modal):
    def __init__(self, view_ref):
        super().__init__(title="Rechercher un véhicule")
        self.view_ref = view_ref
        self.keyword_input = TextInput(label="Mot-clé véhicule", placeholder="Ex: Jug pour Jugular", required=True)
        self.add_item(self.keyword_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.view_ref.update_options(interaction, self.keyword_input.value)

class CarSelect(Select):
    def __init__(self, options, view_ref):
        super().__init__(
            placeholder="Sélectionnez vos véhicules...",
            min_values=0,
            max_values=len(options) if len(options) > 0 else 1,  # éviter 0 explicite
            options=options
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        selected = self.values
        current = get_user_subscriptions(user_id)

        for car in selected:
            if car not in current:
                add_subscription(user_id, car)

        for car in current:
            if car not in selected:
                remove_subscription(user_id, car)

        try:
            await interaction.response.send_message("✅ Vos abonnements ont été mis à jour.", ephemeral=True, delete_after=8)
        except discord.errors.InteractionResponded:
            await interaction.followup.send("✅ Vos abonnements ont été mis à jour.", ephemeral=True, delete_after=8)

class CarSelectionView(View):
    def __init__(self):
        super().__init__(timeout=None)
        # Bouton recherche
        search_btn = Button(label="🔍 Rechercher un véhicule", style=discord.ButtonStyle.secondary)
        search_btn.callback = self.open_search_modal
        self.add_item(search_btn)

        # Bouton voir mes véhicules
        my_cars_btn = Button(label="🚗 Voir mes véhicules", style=discord.ButtonStyle.primary)
        my_cars_btn.callback = self.show_my_cars
        self.add_item(my_cars_btn)

    async def open_search_modal(self, interaction: discord.Interaction):
        modal = CarSearchModal(self)
        await interaction.response.send_modal(modal)

    async def send_ephemeral(self, interaction: discord.Interaction, content: str, view: View = None):
        try:
            if hasattr(self, "user_ephemeral_messages") and interaction.user.id in self.user_ephemeral_messages:
                msg = self.user_ephemeral_messages[interaction.user.id]
                try:
                    await msg.edit(content=content, view=view)
                    return
                except Exception:
                    del self.user_ephemeral_messages[interaction.user.id]

            await interaction.response.send_message(content, view=view, ephemeral=True)
            msg = await interaction.original_response()

            if not hasattr(self, "user_ephemeral_messages"):
                self.user_ephemeral_messages = {}
            self.user_ephemeral_messages[interaction.user.id] = msg

        except discord.errors.InteractionResponded:
            msg = await interaction.followup.send(content, view=view, ephemeral=True)
            if not hasattr(self, "user_ephemeral_messages"):
                self.user_ephemeral_messages = {}
            self.user_ephemeral_messages[interaction.user.id] = msg
        except Exception as e:
            print("Erreur send_ephemeral :", e)

    async def update_options(self, interaction: discord.Interaction, keyword: str):
        user_id = interaction.user.id
        cars = search_cars(keyword)[:25]
        user_subs = get_user_subscriptions(user_id)

        select_options = [
            discord.SelectOption(label=car, default=(car in user_subs))
            for car in cars
        ]

        view = View()
        view.add_item(CarSelect(select_options, self))
        await self.send_ephemeral(interaction, "Sélectionnez vos véhicules :", view=view, delete_after=120)

    async def show_my_cars(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_cars = get_user_subscriptions(user_id)[:25]

        if not user_cars:
            try:
                await interaction.response.send_message("🚗 Vous ne suivez encore aucun véhicule.", ephemeral=True, delete_after=15)
            except discord.errors.InteractionResponded:
                await interaction.followup.send("🚗 Vous ne suivez encore aucun véhicule.", ephemeral=True, delete_after=15)
            return

        select_options = [
            discord.SelectOption(label=car, default=True)
            for car in user_cars
        ]

        view = View()
        view.add_item(CarSelect(select_options, self))
        await self.send_ephemeral(interaction, "🚗 Vos véhicules :", view=view, delete_after=120)
        
