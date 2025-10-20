import discord
from discord import app_commands
from discord.ext import commands
from db.database import init_db, ensure_user, db
from services.formatting import format_currency, format_plain, format_rate
from services.balance import format_xp, level_xp_required, xp_to_decimal
from services.gacha import rarity_emoji
from services.game import compute_tick


def girl_line(row) -> str:
    stamina = format_plain(row["stamina"])
    status = "⚡" if row["is_working"] else "🛌"
    level = int(row["level"])
    requirement = level_xp_required(level)
    if isinstance(row, dict):
        xp_value = row.get("xp", 0)
    else:
        keys = row.keys()
        xp_value = row["xp"] if "xp" in keys else 0
    xp = xp_to_decimal(xp_value)
    if requirement is None:
        xp_text = "MAX"
    else:
        xp_text = f"{format_xp(xp)}/{format_xp(requirement)} XP"
    return (
        f"— **{row['name']}** {rarity_emoji(row['rarity'])} | "
        f"⬆️Lv.{int(row['level'])} | "
        f"💰{format_rate(row['income'])} | 🌟{format_plain(row['popularity'])} | "
        f"❤️{format_plain(row['fans'])} | 📈{xp_text} | 🏷️ {row['specialty'] or '-'} | {status}{stamina}%"
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
        cur.execute(
            "SELECT starter_claimed FROM users WHERE user_id=?",
            (interaction.user.id,),
        )
        claimed_row = cur.fetchone()
        already_claimed = bool(claimed_row and claimed_row["starter_claimed"])

        cur.execute("SELECT 1 FROM user_girls WHERE user_id=?", (interaction.user.id,))
        have_any = cur.fetchone() is not None

        if already_claimed or have_any:
            if not already_claimed and have_any:
                cur.execute(
                    "UPDATE users SET starter_claimed=1 WHERE user_id=?",
                    (interaction.user.id,),
                )
                con.commit()
            con.close()
            await interaction.followup.send(
                "You have already started your agency. Use /agency to review your roster.",
                ephemeral=True,
            )
            return

        cur.execute(
            "UPDATE users SET money = money + 1000, starter_claimed = 1 WHERE user_id=?",
            (interaction.user.id,),
        )
        # default starter
        cur.execute(
            """
            INSERT OR IGNORE INTO user_girls(
                user_id,
                name,
                rarity,
                level,
                xp,
                income,
                popularity,
                fans,
                stamina,
                is_working,
                image_url,
                specialty
            )
            VALUES(?,?,?,?,?,?,?,0,100,1,?,?)
            """,
            (interaction.user.id, "Aya", "N", 1, "0", 5, 100, None, "Singer"),
        )

        con.commit()
        con.close()
        await interaction.followup.send(
            "Agency created! You received 1000 💵 and a starter girl. Use /gacha and /agency.",
            ephemeral=True,
        )

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

        total_fans = sum(float(g["fans"]) for g in girls)
        emb = discord.Embed(title="Your Agency", color=0xFFE17A)
        emb.add_field(name="💵 Money", value=format_currency(money), inline=True)
        emb.add_field(name="❤️ Total Fans", value=format_plain(total_fans), inline=True)
        if tick.get("dt", 0) > 0:
            emb.set_footer(
                text=(
                    f"+{format_currency(tick.get('money_gain', 0))} in {tick['dt']}s "
                    f"(passive {format_currency(tick.get('passive_gain', 0))})"
                )
            )

        if girls:
            desc = "\n".join([girl_line(g) for g in girls[:10]])
            if len(girls) > 10:
                desc += f"\n… and {len(girls)-10} more"
        else:
            desc = "No girls yet. Try /gacha"

        emb.description = desc
        await interaction.response.send_message(embed=emb, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Core(bot))
