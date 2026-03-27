import asyncio
import logging

from bot.bot import JJKBot
from webapp.app import app


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    configure_logging()
    bot = JJKBot()
    async with bot:
        await bot.start(bot.settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
