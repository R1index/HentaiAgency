import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "PASTE_YOUR_TOKEN_HERE")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

INITIAL_COGS = [
    "cogs.core",
    "cogs.gacha",
    "cogs.girls",
    "cogs.admin",
]

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print("Slash sync error:", e)
    print(f"Logged in as {bot.user}")

async def load_cogs():
    for ext in INITIAL_COGS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded cog: {ext}")
        except Exception as e:
            print(f"Failed to load cog {ext}: {e}")

if __name__ == "__main__":
    async def runner():
        await load_cogs()
        await bot.start(TOKEN)
    import asyncio
    if TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("⚠️ Put your bot token into DISCORD_TOKEN env var or edit token in code.")
    asyncio.run(runner())
