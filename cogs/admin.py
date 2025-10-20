import discord
from discord import app_commands
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def owner_or_admin(self, inter: discord.Interaction) -> bool:
        app_owner_id = inter.client.application.owner.id if inter.client.application and inter.client.application.owner else None
        is_owner = (app_owner_id == inter.user.id)
        is_admin = any(r.permissions.administrator for r in getattr(inter.user, "roles", [])) if isinstance(inter.user, discord.Member) else False
        return is_owner or is_admin

    @app_commands.command(name="reload_pool", description="Reload girls JSON (owner/admin only)")
    async def reload_pool(self, interaction: discord.Interaction):
        if not self.owner_or_admin(interaction):
            await interaction.response.send_message("Insufficient permissions.", ephemeral=True)
            return
        gacha_cog = interaction.client.get_cog("Gacha")
        if not gacha_cog:
            await interaction.response.send_message("Gacha cog is not loaded.", ephemeral=True)
            return
        count, warn = gacha_cog.reload_pool_data()
        msg = f"Pool reloaded: {count} entries."
        if warn:
            msg += f"\n⚠️ {warn}"
        await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
