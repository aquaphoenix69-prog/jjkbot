# JJK Battle Nexus Bot

A modular Discord RPG bot inspired by AniGame, rebuilt with a Jujutsu Kaisen theme. Players summon sorcerers, form teams, clear story missions, challenge each other in ranked PvP, and develop Special Grade units into awakened domain users.

## Features

- Prefix-command Discord bot using `discord.py`
- PostgreSQL or SQLite persistence with automatic schema initialization
- Modular architecture for commands, services, data, embeds, and database logic
- Character collection and JJK summon rituals
- Team management, lock favorites, and material-based upgrades
- Turn-based combat for story mode, boss raids, and PvP
- Daily rewards, stamina regeneration, rank points, and multi-category leaderboards
- Rich embed responses plus button-based summon and inventory pagination

## Folder Structure

```text
.
|-- .env.example
|-- README.md
|-- main.py
|-- requirements.txt
`-- bot
    |-- __init__.py
    |-- bot.py
    |-- commands
    |-- config.py
    |-- data
    |-- db
    |-- models
    |-- services
    `-- utils
```

## Setup

1. Install Python 3.11+.
2. Set up either PostgreSQL or SQLite.
3. Copy `.env.example` to `.env` and fill in:
   - `DISCORD_TOKEN`
   - `DATABASE_URL`
   - `DEV_GUILD_ID` if you want optional guild-scoped syncing
4. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

The bot auto-creates tables and seeds the JJK character catalog on startup.

## Railway Note

If you deploy on Railway, use a Railway PostgreSQL service for `DATABASE_URL`.
Do not use `sqlite:///...` on Railway, because container storage is ephemeral and your data will be lost on redeploy.
The repo also includes a `.python-version` file to keep Railway/Nixpacks on Python 3.11.

## Prefix Commands

- `y!help`
- `y!start`
- `y!profile`
- `y!summon <normal|rare|epic|legendary> [1|n-x]`
- `y!inventory`
- `y!team <id> <id> <id>`
- `y!lock <instance_id>`
- `y!battle <story|boss>`
- `y!pvp @user`
- `y!daily`
- `y!upgrade <instance_id> <level|skill|grade|awaken>`
- `y!leaderboard [rank|coins|crystals|streak|story|collection]`
- `y!ping`

## Gameplay Notes

- `Coins` fund summons and progression.
- `Stamina` regenerates automatically every 12 minutes while offline.
- Special Grade sorcerers can awaken once they reach the right level and grade.
- Gojo uses `Infinity`, Sukuna gains `Lifesteal`, and Megumi can trigger `Shikigami Summons`.
