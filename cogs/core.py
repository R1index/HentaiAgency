import os
import discord
from discord import app_commands
from discord.ext import commands
from db.database import init_db, ensure_user, db
from services.game import compute_tick

def fmt_money(x: float) -> str:
    if x >= 1_000_000:
        return f"{x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{x/1_000:.2f}K"
    return f"{int(x)}"

def rarity_emoji(r: str) -> str:
    mapping = {"N":"⭐", "R":"⭐⭐", "SR":"⭐⭐⭐", "SSR":"⭐⭐⭐⭐", "UR":"⭐⭐⭐⭐⭐"}
    return mapping.get(r, r)

def girl_line(row) -> str:
    st = int(row['stamina'])
    status = f"⚡{st}%" if row['is_working'] else f"🛌 {st}%"
    return (
        f"— **{row['name']}** {rarity_emoji(row['rarity'])} | "
        f"💰{row['income']}/s | 🌟{int(row['popularity'])} | "
        f"❤️{int(row['fans'])} | 🏷️ {row['specialty'] or '-'} | {status}"
    )

class Core(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    @app_commands.command(name="start", description="Create your agency and get a starter girl")
    async def start(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ensure_user(interaction.user.id)
        compute_tick(interaction.user.id)
        con = db()
        cur = con.cursor()
        cur.execute("UPDATE users SET money = money + 1000 WHERE user_id=?", (interaction.user.id,))
        # starter candidate: first N if any
        cur.execute("SELECT name FROM user_girls WHERE user_id=?", (interaction.user.id,))
        have_any = cur.fetchone()
        if not have_any:
            # default starter
            cur.execute("""
                INSERT OR IGNORE INTO user_girls(user_id, name, rarity, income, popularity, fans, stamina, is_working, image_url, specialty)
                VALUES(?,?,?,?,?,0,100,1,?,?)
            """, (interaction.user.id, "Aya", "N", 5, 100, None, "Singer"))
        con.commit()
        con.close()
        await interaction.followup.send("Agency created! You received 1000 💵 and a starter girl. Use /gacha and /agency.", ephemeral=True)

    @app_commands.command(name="agency", description="Show your agency overview")
    async def agency(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id)
        tick = compute_tick(interaction.user.id)
        con = db()
        cur = con.cursor()
        cur.execute("SELECT money FROM users WHERE user_id=?", (interaction.user.id,))
        money = cur.fetchone()["money"]
        cur.execute("SELECT * FROM user_girls WHERE user_id=? ORDER BY rarity DESC, income DESC", (interaction.user.id,))
        girls = cur.fetchall()
        con.close()

        total_fans = sum(int(g["fans"]) for g in girls)
        emb = discord.Embed(title="Your Agency", color=0xFFE17A)
        emb.add_field(name="💵 Money", value=fmt_money(money), inline=True)
        emb.add_field(name="❤️ Total Fans", value=f"{total_fans}", inline=True)
        if tick.get("dt",0)>0:
            emb.set_footer(text=f"+{fmt_money(tick.get('money_gain',0))} in {tick['dt']}s (passive {fmt_money(tick.get('passive_gain',0))})")

        if girls:
            desc = "\n".join([girl_line(g) for g in girls[:10]])
            if len(girls) > 10:
                desc += f"\n… and {len(girls)-10} more"
        else:
            desc = "No girls yet. Try /gacha"

        emb.description = desc
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="girls", description="List your girls (cards with images if set)")
    async def girls(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id)
        compute_tick(interaction.user.id)

        con = db()
        cur = con.cursor()
        cur.execute("SELECT * FROM user_girls WHERE user_id=? ORDER BY rarity DESC, income DESC", (interaction.user.id,))
        rows = cur.fetchall()
        con.close()

        if not rows:
            await interaction.response.send_message("You have no girls yet. Try /gacha", ephemeral=True)
            return

        count = 0
        for r in rows:
            if count >= 5:
                await interaction.followup.send(f"…and {len(rows)-5} more. Use /agency for a compact list.", ephemeral=True)
                break
            em = discord.Embed(title=f"{r['name']} {rarity_emoji(r['rarity'])}", color=0xFF99CC)
            em.add_field(name="Specialty", value=r['specialty'] or "-", inline=True)
            em.add_field(name="Income", value=f"{r['income']}/s", inline=True)
            em.add_field(name="Popularity", value=f"{int(r['popularity'])}", inline=True)
            em.add_field(name="Fans", value=f"{int(r['fans'])}", inline=True)
            st = int(r['stamina'])
            em.add_field(name="Stamina", value=f"{st}% {'(working)' if r['is_working'] else '(resting)'}", inline=True)
            if r['image_url']:
                em.set_image(url=r['image_url'])
            await (interaction.response.send_message if count==0 else interaction.followup.send)(embed=em, ephemeral=True)
            count += 1

async def setup(bot: commands.Bot):
    await bot.add_cog(Core(bot))
