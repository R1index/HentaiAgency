# Idle Idol Agency — Modular Discord Bot

A modular, production-ready Discord bot implementing a simple idle/gacha game:
- 5 rarities (N/R/SR/SSR/UR)
- per-girl personal fans that accumulate while working
- passive income from total fans
- stamina (auto drain on work, auto restore on rest)
- JSON-driven girl pool with text specialties and optional images
- duplicate cashback (50%)
- clean slash commands and cogs

## Quick Start

1) Create a Discord application & bot, invite it with `applications.commands` and `bot` scopes.
2) Clone or download this project.
3) Create a `.env` in project root:

```
DISCORD_TOKEN=YOUR_TOKEN_HERE
GIRLS_JSON_PATH=data/girls.json
```

4) Install deps:
```
python -m pip install -U -r requirements.txt
```

5) Run:
```
python -m bot
```

## Commands

- `/start` — create your agency and receive a starter girl
- `/agency` — overview (money, total fans, roster summary)
- `/girls` — interactive roster browser with pagination, toggles, and upgrades
- `/gacha` — scout a new girl (500). Duplicate → 50% cashback
- `/reload_pool` — (admin/owner) reload girls JSON without restart

## Tech

- `discord.py 2.x` (slash commands via app_commands)
- SQLite for persistence
- JSON-driven content in `data/girls.json`
- Modular cogs/services structure
