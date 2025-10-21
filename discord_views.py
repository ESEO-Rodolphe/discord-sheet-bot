# discord_views.py
import discord
from discord.ui import View, Select, Modal, TextInput
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
            max_values=len(options) if len(options) > 0 else 1,
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

        menu_cars = [opt.label for opt in self.options]
        for car in menu_cars:
            if car in current and car not in selected:
                remove_subscription(user_id, car)

        await self.view_ref.safe_reply(interaction, "✅ Vos abonnements ont été mis à jour.")


class CarSelectionView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.user_ephemeral_messages = {}

    async def safe_reply(self, interaction: discord.Interaction, content: str, view: View = None):
        """Répond proprement à une interaction sans spam ni doublons."""
        try:
            if getattr(interaction, "response", None) and interaction.response.is_done():
                await interaction.followup.send(content, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(content, view=view, ephemeral=True)
        except Exception as e:
            print("Erreur safe_reply :", e)

    async def send_ephemeral(self, interaction: discord.Interaction, content: str, view: View = None):
        """Supprime l'ancien message éphémère de l'utilisateur avant d'en envoyer un nouveau."""
        try:
            user_id = interaction.user.id
            old_msg = self.user_ephemeral_messages.get(user_id)
            if old_msg:
                try:
                    await old_msg.delete()
                except Exception:
                    pass
                del self.user_ephemeral_messages[user_id]

            if getattr(interaction, "response", None) and interaction.response.is_done():
                msg = await interaction.followup.send(content, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(content, view=view, ephemeral=True)
                msg = await interaction.original_response()

            self.user_ephemeral_messages[user_id] = msg

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
        await self.send_ephemeral(interaction, "Sélectionnez vos véhicules :", view=view)

    async def show_my_cars(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_cars = get_user_subscriptions(user_id)[:25]

        if not user_cars:
            await self.safe_reply(interaction, "🚗 Vous ne suivez encore aucun véhicule.")
            return

        select_options = [discord.SelectOption(label=car, default=True) for car in user_cars]
        view = View()
        view.add_item(CarSelect(select_options, self))
        await self.send_ephemeral(interaction, "🚗 Vos véhicules :", view=view)
