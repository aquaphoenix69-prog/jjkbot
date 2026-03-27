# JJK Battle Nexus Bot

A modular Discord RPG bot inspired by AniGame, rebuilt with a Jujutsu Kaisen theme. Players summon sorcerers, form teams, clear story missions, challenge each other in ranked PvP, and develop Special Grade units into awakened domain users.

## Features

- Slash-command Discord bot using `discord.py`
- Prefix support with `y!help`
- PostgreSQL persistence with automatic schema initialization
- Modular architecture for commands, services, data, embeds, and database logic
- Character collection and gacha banners with pity
- Team management, lock favorites, and material-based upgrades
- Turn-based combat for story mode, boss raids, and PvP
- Daily rewards, stamina regeneration, rank points, and leaderboards
- Rich embed responses plus button-based inventory pagination

## Folder Structure

```text
.
├── .env.example
├── README.md
├── main.py
├── requirements.txt
└── bot
    ├── __init__.py
    ├── bot.py
    ├── commands
    │   ├── __init__.py
    │   ├── battle.py
    │   └── game.py
    ├── config.py
    ├── data
    │   ├── __init__.py
    │   └── characters.py
    ├── db
    │   ├── __init__.py
    │   └── database.py
    ├── models
    │   ├── __init__.py
    │   └── game.py
    ├── services
    │   ├── __init__.py
    │   ├── battle_service.py
    │   └── game_service.py
    └── utils
        ├── __init__.py
        └── embeds.py
```

## Setup

1. Install Python 3.11+ and PostgreSQL.
2. Create a database named `jjk_bot`.
3. Copy `.env.example` to `.env` and fill in:
   - `DISCORD_TOKEN`
   - `DATABASE_URL`
   - `DEV_GUILD_ID` for fast guild-scoped slash-command sync during development
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run the bot:

```bash
python main.py
```

The bot auto-creates tables and seeds the JJK character catalog on startup.

## Slash Commands

- Prefix help: `y!help`
- `/start` create a player profile and starter team
- `/profile` inspect resources, pity, rank, and progression
- `/summon banner:<standard|gojo|sukuna|yuji> amount:<1|10> use_crystals:<true|false>`
- `/inventory` browse collected characters
- `/team slot1:<id> slot2:<id> slot3:<id>` set your active team
- `/lock instance_id:<id>` toggle favorite lock
- `/battle mode:<story|boss>` run PvE
- `/pvp opponent:@user` challenge another player
- `/daily` claim daily rewards and streak bonuses
- `/upgrade instance_id:<id> action:<level|skill|grade|awaken>` improve a character
- `/leaderboard` show the ranked ladder

## Gameplay Notes

- `Coins` and `Cursed Energy Crystals` fund summons and progression.
- `Stamina` regenerates automatically every 12 minutes while offline.
- Special Grade sorcerers can awaken once they reach the right level and grade.
- Pity guarantees a `Special Grade` on the 30th summon if one has not appeared sooner.
- Gojo uses `Infinity`, Sukuna gains `Lifesteal`, and Megumi can trigger `Shikigami Summons`.

## Production Hardening Ideas

- Add Alembic migrations instead of inline schema bootstrapping
- Move balance values into JSON/YAML or admin-editable tables
- Add clan tables, guild-only raid scheduling, and seasonal battle passes
- Store long battle logs externally and paginate them in Discord
- Add Redis for distributed cooldowns if running multiple bot instances
