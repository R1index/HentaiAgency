from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from db.database import db, ensure_user
from services.game import compute_tick

class Girls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="work", description="Toggle working/resting for a girl by name")
    @app_commands.describe(name="Girl name (as listed in /girls or /agency)")
    async def work(self, interaction: discord.Interaction, name: str):
        ensure_user(interaction.user.id)
        compute_tick(interaction.user.id)
        con = db()
        cur = con.cursor()
        cur.execute("SELECT id, is_working FROM user_girls WHERE user_id=? AND name=?", (interaction.user.id, name))
        row = cur.fetchone()
        if not row:
            con.close()
            await interaction.response.send_message("Girl not found.", ephemeral=True)
            return
        new_state = 0 if row["is_working"] else 1
        cur.execute("UPDATE user_girls SET is_working=? WHERE id=?", (new_state, row["id"]))
        con.commit()
        con.close()
        await interaction.response.send_message(f"{name}: {'now working' if new_state else 'now resting'}.", ephemeral=True)

    @app_commands.command(name="upgrade", description="Increase a girl's income by +10% (cost = 5× current income)")
    @app_commands.describe(name="Girl name (as listed in /girls or /agency)")
    async def upgrade(self, interaction: discord.Interaction, name: str):
        ensure_user(interaction.user.id)
        compute_tick(interaction.user.id)
        con = db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=?", (interaction.user.id,))
        user = cur.fetchone()
        cur.execute("SELECT * FROM user_girls WHERE user_id=? AND name=?", (interaction.user.id, name))
        g = cur.fetchone()
        if not g:
            con.close()
            await interaction.response.send_message("Girl not found.", ephemeral=True)
            return
        cost = int(g["income"] * 5)
        if user["money"] < cost:
            con.close()
            await interaction.response.send_message(f"You need {cost} 💵.", ephemeral=True)
            return
        new_income = round(g["income"] * 1.10, 2)
        cur.execute("UPDATE user_girls SET income=? WHERE id=?", (new_income, g["id"]))
        cur.execute("UPDATE users SET money=money-? WHERE user_id=?", (cost, interaction.user.id))
        con.commit()
        con.close()
        await interaction.response.send_message(f"{name}: income {g['income']} → **{new_income}**/s (−{cost} 💵)", ephemeral=True)

    @app_commands.command(name="set_image", description="Set girl's image (URL or attachment)")
    @app_commands.describe(name="Girl name", url="Image URL (if not using an attachment)")
    async def set_image(self, interaction: discord.Interaction, name: str, url: Optional[str] = None, attachment: Optional[discord.Attachment] = None):
        ensure_user(interaction.user.id)
        compute_tick(interaction.user.id)

        final_url = None
        if attachment is not None:
            if not attachment.content_type or not attachment.content_type.startswith("image/"):
                await interaction.response.send_message("Attachment must be an image.", ephemeral=True)
                return
            final_url = attachment.url
        elif url:
            final_url = url

        if not final_url:
            await interaction.response.send_message("Provide either an image attachment or an image URL.", ephemeral=True)
            return

        con = db()
        cur = con.cursor()
        cur.execute("SELECT id FROM user_girls WHERE user_id=? AND name=?", (interaction.user.id, name))
        row = cur.fetchone()
        if not row:
            con.close()
            await interaction.response.send_message("Girl not found.", ephemeral=True)
            return
        cur.execute("UPDATE user_girls SET image_url=? WHERE id=?", (final_url, row["id"]))
        con.commit()
        con.close()
        await interaction.response.send_message(f"Image for **{name}** updated ✅", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Girls(bot))
