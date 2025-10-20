import os, random
from typing import Optional, Tuple
import discord
from discord import app_commands
from discord.ext import commands
from db.database import db, ensure_user
from services.gacha import rarity_roll, pick_by_rarity, GACHA_COST, DUP_CASHBACK, rarity_emoji
from models.girl_pool import load_pool

class Gacha(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pool = []
        self.warn = None
        self.reload_pool_data()

    def reload_pool_data(self) -> Tuple[int, Optional[str]]:
        path = os.getenv("GIRLS_JSON_PATH", "data/girls.json")
        pool, warn = load_pool(path)
        self.pool = pool
        self.warn = warn
        if warn:
            print("Pool warning:", warn)
        return len(pool), warn

    @app_commands.command(name="gacha", description="Scout a new girl (500). Duplicate grants 50% cashback.")
    async def gacha(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id)
        con = db()
        cur = con.cursor()
        cur.execute("SELECT money FROM users WHERE user_id=?", (interaction.user.id,))
        money = float(cur.fetchone()["money"])
        if money < GACHA_COST:
            con.close()
            await interaction.response.send_message(f"Not enough funds. Need {GACHA_COST} 💵.", ephemeral=True)
            return

        money -= GACHA_COST
        r = rarity_roll()
        g = pick_by_rarity(self.pool, r)

        cur.execute("SELECT id FROM user_girls WHERE user_id=? AND name=?", (interaction.user.id, g["name"]))
        exists = cur.fetchone()
        if exists:
            cashback = int(GACHA_COST * DUP_CASHBACK)
            money += cashback
            result = f"🎰 Duplicate **{g['name']}** {rarity_emoji(g['rarity'])}. Cashback: +{cashback} 💵"
        else:
            cur.execute("""                INSERT INTO user_girls(user_id, name, rarity, income, popularity, fans, stamina, is_working, image_url, specialty)
                VALUES(?,?,?,?,?,0,100,1,?,?)
            """, (interaction.user.id, g["name"], g["rarity"], g["income"], g["popularity"], g.get("image_url"), g.get("specialty")))
            result = f"🎉 New girl: **{g['name']}** {rarity_emoji(g['rarity'])}!\nIncome {g['income']}/s | Popularity {g['popularity']} | 🏷️ {g.get('specialty','-')}"

        cur.execute("UPDATE users SET money=? WHERE user_id=?", (money, interaction.user.id))
        con.commit()
        con.close()
        await interaction.response.send_message(result, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Gacha(bot))
