import os, random
from pathlib import Path
from typing import List, Optional, Tuple
import discord
from discord import app_commands
from discord.ext import commands
from db.database import db, ensure_user
from services.formatting import format_currency, format_plain, format_rate
from services.gacha import rarity_roll, pick_by_rarity, GACHA_COST, DUP_CASHBACK, rarity_emoji
from models.girl_pool import load_pool

class Gacha(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pool = []
        self.warn = None
        self.reload_pool_data()

    @staticmethod
    def build_image(girl: dict) -> tuple[Optional[str], List[discord.File]]:
        attachments: List[discord.File] = []
        image_url = girl.get("image_url")
        image_path = girl.get("image_path")
        # If image_url already remote, just return
        if image_url:
            return image_url, attachments
        if not image_path:
            return None, attachments
        path = Path(str(image_path)).expanduser()
        if not path.is_absolute():
            path = Path(os.getenv("GIRLS_IMAGE_ROOT", "")) / path
        if not path.exists() or not path.is_file():
            return None, attachments
        base_name = "".join(ch if ch.isalnum() else "_" for ch in girl["name"].lower()) or "girl"
        filename = f"gacha_{base_name}_{path.name.replace(' ', '_')}"
        attachments.append(discord.File(path, filename=filename))
        return f"attachment://{filename}", attachments

    def reload_pool_data(self) -> Tuple[int, Optional[str]]:
        path = os.getenv("GIRLS_JSON_PATH", "data/girls.json")
        pool, warn = load_pool(path)
        self.pool = pool
        self.warn = warn
        if warn:
            print("Pool warning:", warn)
        return len(pool), warn

    @app_commands.command(
        name="gacha",
        description=f"Scout a new girl ({GACHA_COST}). Duplicate grants {int(DUP_CASHBACK * 100)}% cashback.",
    )
    async def gacha(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id)
        con = db()
        cur = con.cursor()
        cur.execute("SELECT money FROM users WHERE user_id=?", (interaction.user.id,))
        money = float(cur.fetchone()["money"])
        if money < GACHA_COST:
            con.close()
            await interaction.response.send_message(
                f"Not enough funds. Need {format_currency(GACHA_COST)}.", ephemeral=True
            )
            return

        money -= GACHA_COST
        r = rarity_roll()
        if not self.pool:
            con.close()
            await interaction.response.send_message(
                "The scouting pool is empty. Please ask an admin to reload the roster.",
                ephemeral=True,
            )
            return
        g = pick_by_rarity(self.pool, r)

        cur.execute("SELECT id FROM user_girls WHERE user_id=? AND name=?", (interaction.user.id, g["name"]))
        exists = cur.fetchone()
        image_reference = g.get("image_url") or g.get("image_path")
        if exists:
            cashback = int(round(GACHA_COST * DUP_CASHBACK))
            money += cashback
            if image_reference:
                cur.execute(
                    "UPDATE user_girls SET image_url=? WHERE user_id=? AND name=?",
                    (str(image_reference), interaction.user.id, g["name"]),
                )
            description = (
                f"🎰 Duplicate **{g['name']}** {rarity_emoji(g['rarity'])}. "
                f"Cashback: +{format_currency(cashback)}"
            )
        else:
            cur.execute("""
                INSERT INTO user_girls(user_id, name, rarity, level, income, popularity, fans, stamina, is_working, image_url, specialty)
                VALUES(?,?,?,?,?,?,0,100,1,?,?)
            """, (
                interaction.user.id,
                g["name"],
                g["rarity"],
                1,
                g["income"],
                g["popularity"],
                image_reference,
                g.get("specialty"),
            ))
            description = (
                f"🎉 New girl: **{g['name']}** {rarity_emoji(g['rarity'])}!\n"
                f"💰 {format_rate(g['income'])} | 🌟{format_plain(g['popularity'])} | 🏷️ {g.get('specialty','-')}"
            )

        cur.execute("UPDATE users SET money=? WHERE user_id=?", (money, interaction.user.id))
        con.commit()
        con.close()
        embed = discord.Embed(
            title=f"{g['name']} {rarity_emoji(g['rarity'])}",
            description=description,
            color=discord.Color.from_str("#FF99CC"),
        )
        embed.add_field(name="💰 Income", value=format_rate(g["income"]), inline=True)
        embed.add_field(name="🌟 Popularity", value=format_plain(g["popularity"]), inline=True)
        embed.add_field(name="🏷️ Specialty", value=g.get("specialty") or "-", inline=True)
        embed.add_field(name="💵 Balance", value=format_currency(money), inline=True)
        image_url, attachments = self.build_image(g)
        if image_url:
            embed.set_image(url=image_url)
        kwargs = {"embed": embed, "ephemeral": True}
        if attachments:
            kwargs["files"] = list(attachments)
        await interaction.response.send_message(**kwargs)

async def setup(bot: commands.Bot):
    await bot.add_cog(Gacha(bot))
