# JJK Battle Nexus Bot

A modular Discord RPG bot inspired by AniGame, rebuilt with a Jujutsu Kaisen theme. Players summon sorcerers, form teams, clear story missions, challenge each other in ranked PvP, and develop Special Grade units into awakened domain users. The repo also includes a Yutafraud web dashboard for profiles, leaderboards, and game settings.

## Features

- Prefix-command Discord bot using `discord.py`
- Yutafraud web dashboard with profile panels, Discord avatars, and leaderboard pages
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
|-- web_main.py
|-- requirements.txt
|-- bot
|   |-- __init__.py
|   |-- bot.py
|   |-- commands
|   |-- config.py
|   |-- data
|   |-- db
|   |-- models
|   |-- services
|   `-- utils
`-- webapp
    |-- __init__.py
    |-- app.py
    |-- static
    `-- templates
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

Run the bot:

```bash
python main.py
```

Run the web dashboard:

```bash
python web_main.py
```

The bot and web app both auto-create tables and seed the JJK character catalog on startup.

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

## Web Dashboard

- `/` shows the Yutafraud homepage with a profile lookup, cat welcome gif, and stat leaderboards
- `/profiles/<discord_id>` shows a player profile panel with avatar, name, currencies, materials, team, collection, and leaderboard snapshot
- `/lookup?user_id=<discord_id>` redirects to a profile page
- `/health` returns a simple health payload

## Gameplay Notes

- `Coins` fund summons and progression.
- `Stamina` regenerates automatically every 12 minutes while offline.
- Special Grade sorcerers can awaken once they reach the right level and grade.
- Gojo uses `Infinity`, Sukuna gains `Lifesteal`, and Megumi can trigger `Shikigami Summons`.

## Production Hardening Ideas

- Add Discord OAuth for authenticated self-serve profile pages
- Add Alembic migrations instead of inline schema bootstrapping
- Store long battle logs externally and paginate them in Discord and on the web
- Add Redis for distributed cooldowns if running multiple bot instances
