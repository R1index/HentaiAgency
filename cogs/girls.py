from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from db.database import db, ensure_user
from services.formatting import format_currency, format_plain, format_rate
from services.gacha import rarity_emoji
from services.game import compute_tick
from services.balance import format_xp, level_xp_required, xp_to_decimal
from models.girl_pool import load_pool
from services.image_paths import allowed_roots, is_within_allowed


def _window_bounds(total: int, index: int, limit: int) -> tuple[int, int]:
    if total <= limit:
        return 0, total
    half = limit // 2
    start = max(0, index - half)
    end = start + limit
    if end > total:
        end = total
        start = end - limit
    return start, end


class GirlSelect(discord.ui.Select):
    def __init__(self, view: "GirlsPaginator") -> None:
        self.paginator = view
        options = view.build_options()
        super().__init__(
            placeholder=view.select_placeholder(),
            options=options,
            min_values=1,
            max_values=1,
            row=0,
        )

    def refresh(self) -> None:
        self.placeholder = self.paginator.select_placeholder()
        self.options = self.paginator.build_options()

    async def callback(self, interaction: discord.Interaction) -> None:  # type: ignore[override]
        index = int(self.values[0])
        self.paginator.page = index
        await self.paginator.send_page(interaction)


class GirlsPaginator(discord.ui.View):
    def __init__(
        self,
        user_id: int,
        rows: Sequence[object],
        money: float,
        pool_lookup: Optional[dict[str, dict[str, object]]] = None,
    ) -> None:
        super().__init__(timeout=180)
        self.user_id = user_id
        self.pool_lookup: dict[str, dict[str, object]] = pool_lookup or {}
        self.rows = [self._hydrate_row(dict(r)) for r in rows]
        self.money = float(money)
        self.page = 0
        self.message: Optional[discord.Message] = None
        self.select_menu = GirlSelect(self)
        self.add_item(self.select_menu)
        self.update_components()

    def _resolve_reference(self, ref: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not ref:
            return None, None
        ref_str = str(ref).strip()
        if not ref_str:
            return None, None
        lower = ref_str.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            return ref_str, None
        candidate = Path(ref_str).expanduser()
        roots = allowed_roots()
        if candidate.is_absolute():
            resolved = candidate.resolve()
            if is_within_allowed(resolved, roots) and resolved.exists():
                return None, str(resolved)
            return None, None

        for root in roots:
            attempt = (root / candidate).resolve()
            if not is_within_allowed(attempt, roots):
                continue
            if attempt.exists():
                return None, str(attempt)

        return None, None

    def _hydrate_row(self, row: dict) -> dict:
        ref = row.get("image_url")
        if ref:
            image_url, image_path = self._resolve_reference(ref)
        else:
            image_url, image_path = None, None

        if not image_url and not image_path:
            fallback = self.pool_lookup.get(row.get("name")) if self.pool_lookup else None
            if fallback:
                pool_ref = fallback.get("image_url") or fallback.get("image_path")
                image_url, image_path = self._resolve_reference(pool_ref)

        row["image_url"] = image_url
        row["image_path"] = image_path
        return row

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot manage someone else's roster.", ephemeral=True)
            return False
        return True

    def current(self) -> dict:
        return self.rows[self.page]

    def select_placeholder(self) -> str:
        current = self.current()
        return f"{self.page + 1}/{len(self.rows)} • {current['name']}"

    def build_options(self) -> List[discord.SelectOption]:
        start, end = _window_bounds(len(self.rows), self.page, 25)
        options: List[discord.SelectOption] = []
        for idx in range(start, end):
            row = self.rows[idx]
            options.append(
                discord.SelectOption(
                    label=row["name"],
                    value=str(idx),
                    description=f"Lv.{int(row['level'])} • {format_rate(row['income'])}",
                    default=idx == self.page,
                )
            )
        return options

    def update_components(self) -> None:
        if not self.rows:
            for child in self.children:
                child.disabled = True
            return
        self.select_menu.refresh()
        total = len(self.rows)
        self.go_previous.disabled = total <= 1
        self.go_next.disabled = total <= 1
        current = self.current()
        working = bool(current["is_working"])
        self.toggle_work.label = "Send to Rest" if working else "Start Working"
        self.toggle_work.style = (
            discord.ButtonStyle.danger if working else discord.ButtonStyle.success
        )
        self.toggle_work.emoji = "🛌" if working else "💼"

    def roster_preview(self) -> str:
        start, end = _window_bounds(len(self.rows), self.page, 10)
        lines = []
        for idx in range(start, end):
            row = self.rows[idx]
            marker = "➤" if idx == self.page else "•"
            lines.append(
                f"{marker} {idx + 1}. {row['name']} Lv.{int(row['level'])} — {format_rate(row['income'])}"
            )
        return "\n".join(lines)

    def make_embed(self) -> Tuple[discord.Embed, List[discord.File]]:
        current = self.current()
        embed = discord.Embed(
            title=f"{current['name']} {rarity_emoji(current['rarity'])}",
            color=0xFF99CC,
            description=self.roster_preview(),
        )
        embed.add_field(name="💼 Balance", value=format_currency(self.money), inline=True)
        current_level = int(current["level"])
        embed.add_field(name="⬆️ Level", value=str(current_level), inline=True)
        embed.add_field(name="💰 Income", value=format_rate(current["income"]), inline=True)
        embed.add_field(name="🌟 Popularity", value=format_plain(current["popularity"]), inline=True)
        embed.add_field(name="❤️ Fans", value=format_plain(current["fans"]), inline=True)
        stamina = format_plain(current["stamina"])
        status = "Working" if current["is_working"] else "Resting"
        embed.add_field(name="⚡ Stamina", value=f"{stamina}% • {status}", inline=True)
        xp = xp_to_decimal(current.get("xp", 0))
        requirement = level_xp_required(current_level)
        if requirement is None:
            xp_text = "MAX"
        else:
            xp_text = f"{format_xp(xp)}/{format_xp(requirement)}"
        embed.add_field(name="📈 Experience", value=xp_text, inline=True)
        embed.add_field(name="🗂️ Specialty", value=current["specialty"] or "-", inline=True)
        embed.set_footer(text=f"Page {self.page + 1}/{len(self.rows)}")
        attachments: List[discord.File] = []
        image_url = current.get("image_url")
        image_path = current.get("image_path")
        if image_url:
            embed.set_image(url=image_url)
        elif image_path:
            path = Path(image_path)
            if path.exists() and path.is_file():
                safe_name = path.name.replace(" ", "_")
                filename = f"girl_{current['id']}_{safe_name}"
                file = discord.File(path, filename=filename)
                attachments.append(file)
                embed.set_image(url=f"attachment://{filename}")
        return embed, attachments

    async def send_page(self, interaction: discord.Interaction) -> None:
        self.update_components()
        embed, attachments = self.make_embed()
        await interaction.response.edit_message(embed=embed, view=self, attachments=attachments)

    def reload_state(self) -> None:
        if not self.rows:
            return
        current_id = self.current()["id"]
        con = db()
        cur = con.cursor()
        cur.execute("SELECT money FROM users WHERE user_id=?", (self.user_id,))
        row = cur.fetchone()
        self.money = float(row["money"]) if row else 0.0
        cur.execute(
            "SELECT * FROM user_girls WHERE user_id=? ORDER BY rarity DESC, income DESC, name ASC",
            (self.user_id,),
        )
        self.rows = [self._hydrate_row(dict(r)) for r in cur.fetchall()]
        con.close()
        if not self.rows:
            self.page = 0
            self.update_components()
            return
        for idx, row in enumerate(self.rows):
            if row["id"] == current_id:
                self.page = idx
                break
        else:
            self.page = min(self.page, len(self.rows) - 1)
        self.update_components()

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, row=1)
    async def go_previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not self.rows:
            await interaction.response.send_message("No girls available.", ephemeral=True)
            return
        self.page = (self.page - 1) % len(self.rows)
        await self.send_page(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, row=1)
    async def go_next(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not self.rows:
            await interaction.response.send_message("No girls available.", ephemeral=True)
            return
        self.page = (self.page + 1) % len(self.rows)
        await self.send_page(interaction)

    @discord.ui.button(label="Toggle", style=discord.ButtonStyle.primary, row=2)
    async def toggle_work(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer(thinking=False)
        compute_tick(self.user_id)
        current = self.current()
        con = db()
        cur = con.cursor()
        cur.execute(
            "SELECT id, is_working FROM user_girls WHERE id=? AND user_id=?",
            (current["id"], self.user_id),
        )
        row = cur.fetchone()
        if not row:
            con.close()
            self.reload_state()
            if self.rows:
                embed, attachments = self.make_embed()
                await interaction.edit_original_response(embed=embed, view=self, attachments=attachments)
            else:
                await interaction.edit_original_response(
                    content="Your roster is empty now.", view=None
                )
            await interaction.followup.send("Girl not found anymore.", ephemeral=True)
            return
        new_state = 0 if row["is_working"] else 1
        cur.execute("UPDATE user_girls SET is_working=? WHERE id=?", (new_state, row["id"]))
        con.commit()
        con.close()
        self.reload_state()
        embed, attachments = self.make_embed()
        await interaction.edit_original_response(embed=embed, view=self, attachments=attachments)
        state_text = "now resting" if new_state == 0 else "now working"
        await interaction.followup.send(f"{current['name']} is {state_text}.", ephemeral=True)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Girls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="girls", description="Browse and manage your girls with an interactive roster")
    async def girls(self, interaction: discord.Interaction) -> None:
        ensure_user(interaction.user.id)
        compute_tick(interaction.user.id)
        con = db()
        cur = con.cursor()
        cur.execute("SELECT money FROM users WHERE user_id=?", (interaction.user.id,))
        user_row = cur.fetchone()
        cur.execute(
            "SELECT * FROM user_girls WHERE user_id=? ORDER BY rarity DESC, income DESC, name ASC",
            (interaction.user.id,),
        )
        rows_data = cur.fetchall()
        pool_path = os.getenv("GIRLS_JSON_PATH", "data/girls.json")
        pool_entries, _pool_warn = load_pool(pool_path)
        pool_lookup: dict[str, dict[str, object]] = {entry["name"]: entry for entry in pool_entries}
        rows = [dict(r) for r in rows_data]
        updates: list[tuple[str, int]] = []
        for row in rows:
            if row.get("image_url"):
                continue
            fallback = pool_lookup.get(row.get("name"))
            if not fallback:
                continue
            ref = fallback.get("image_url") or fallback.get("image_path")
            if not ref:
                continue
            row["image_url"] = ref
            updates.append((str(ref), row["id"]))
        if updates:
            cur.executemany("UPDATE user_girls SET image_url=? WHERE id=?", updates)
            con.commit()
        con.close()
        if not rows:
            await interaction.response.send_message("You have no girls yet. Try /gacha", ephemeral=True)
            return
        money = float(user_row["money"]) if user_row else 0.0
        view = GirlsPaginator(interaction.user.id, rows, money, pool_lookup)
        embed, attachments = view.make_embed()
        kwargs = {"embed": embed, "view": view}
        if attachments:
            kwargs["files"] = attachments
        await interaction.response.send_message(**kwargs)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(Girls(bot))
