from __future__ import annotations

import io

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from bot.models.game import BattleSnapshot, BattleUnitState


RARITY_COLORS = {
    "normal": (160, 160, 160),
    "rare": (74, 163, 255),
    "epic": (185, 107, 255),
    "legendary": (255, 194, 61),
}


async def render_battle_snapshot(snapshot: BattleSnapshot) -> tuple[bytes, str]:
    units = snapshot.left_team[:3] + snapshot.right_team[:3]
    images = await _download_images([unit.image_url for unit in units])

    canvas = Image.new("RGB", (1080, 620), (30, 14, 18))
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.load_default()
    text_font = ImageFont.load_default()

    for y in range(canvas.height):
        blend = y / max(1, canvas.height - 1)
        color = (
            int(32 + 72 * blend),
            int(12 + 26 * blend),
            int(16 + 18 * blend),
        )
        draw.line([(0, y), (canvas.width, y)], fill=color)

    draw.rounded_rectangle((28, 22, 1052, 288), radius=28, fill=(49, 24, 30), outline=(99, 200, 196), width=3)
    draw.rounded_rectangle((28, 330, 1052, 596), radius=28, fill=(49, 24, 30), outline=(241, 94, 94), width=3)
    draw.rounded_rectangle((462, 275, 618, 345), radius=16, fill=(24, 10, 12), outline=(255, 224, 145), width=3)
    draw.text((540, 309), "VS", font=title_font, fill=(255, 255, 255), anchor="mm")
    draw.text((56, 34), "Allies", font=title_font, fill=(220, 255, 246))
    draw.text((56, 342), "Enemies", font=title_font, fill=(255, 224, 224))

    for index, unit in enumerate(snapshot.left_team[:3]):
        card_x = 54 + index * 326
        _paste_card(canvas, images[index], (card_x, 72), unit, highlight=unit.name == snapshot.actor_name)
        _draw_unit_details(
            draw,
            unit,
            (card_x, 198, card_x + 292, 266),
            font=text_font,
            highlight=unit.name == snapshot.actor_name,
        )

    offset = len(snapshot.left_team[:3])
    for index, unit in enumerate(snapshot.right_team[:3]):
        card_x = 54 + index * 326
        _paste_card(canvas, images[offset + index], (card_x, 380), unit, highlight=unit.name == snapshot.target_name)
        _draw_unit_details(
            draw,
            unit,
            (card_x, 506, card_x + 292, 574),
            font=text_font,
            highlight=unit.name == snapshot.target_name,
        )

    return _to_png_bytes(canvas), "battle_snapshot.png"


async def _download_images(urls: list[str]) -> list[Image.Image]:
    timeout = aiohttp.ClientTimeout(total=12)
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        return [await _download_image(session, url) for url in urls]


async def _download_image(session: aiohttp.ClientSession, url: str) -> Image.Image:
    if not url:
        return _placeholder()
    try:
        async with session.get(url, allow_redirects=True) as response:
            if response.status != 200:
                return _placeholder()
            raw = await response.read()
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        return _placeholder()


def _placeholder() -> Image.Image:
    image = Image.new("RGB", (320, 420), (54, 44, 46))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 20, 300, 400), radius=24, fill=(78, 61, 67), outline=(190, 170, 175), width=3)
    draw.text((160, 210), "NO\nIMAGE", fill=(255, 255, 255), anchor="mm", align="center")
    return image


def _paste_card(
    canvas: Image.Image,
    image: Image.Image,
    pos: tuple[int, int],
    unit: BattleUnitState,
    *,
    highlight: bool,
) -> None:
    card = image.copy().resize((280, 118))
    border = (255, 238, 158) if highlight else RARITY_COLORS.get(unit.rarity.lower(), (170, 170, 170))
    frame = Image.new("RGB", (292, 130), border)
    frame.paste(card, (6, 6))
    canvas.paste(frame, pos)


def _draw_unit_details(
    draw: ImageDraw.ImageDraw,
    unit: BattleUnitState,
    bounds: tuple[int, int, int, int],
    *,
    font: ImageFont.ImageFont,
    highlight: bool,
) -> None:
    x1, y1, x2, y2 = bounds
    outline = (255, 233, 160) if highlight else (255, 255, 255)
    draw.rounded_rectangle(bounds, radius=14, fill=(25, 12, 16), outline=outline, width=2)
    draw.text((x1 + 12, y1 + 8), f"{unit.name}  Lv.{unit.level}  Evo {unit.evolution_stage}", fill=(255, 255, 255), font=font)
    draw.text((x2 - 12, y1 + 8), f"{unit.hp:,}/{unit.max_hp:,} HP", fill=(214, 255, 214), font=font, anchor="ra")
    draw.text((x2 - 12, y1 + 24), f"{unit.energy}/{unit.max_energy} EN", fill=(193, 243, 255), font=font, anchor="ra")
    status = _status_text(unit)
    if status:
        draw.text((x1 + 12, y1 + 24), status, fill=(255, 215, 170), font=font)
    _draw_bar(draw, (x1 + 12, y1 + 42, x2 - 12, y1 + 54), unit.hp / max(1, unit.max_hp), (38, 228, 57))
    _draw_bar(draw, (x1 + 12, y1 + 58, x2 - 12, y2 - 10), unit.energy / max(1, unit.max_energy), (103, 230, 255))


def _draw_bar(draw: ImageDraw.ImageDraw, bounds: tuple[int, int, int, int], ratio: float, color: tuple[int, int, int]) -> None:
    x1, y1, x2, y2 = bounds
    draw.rounded_rectangle(bounds, radius=8, fill=(56, 40, 45), outline=(255, 255, 255), width=1)
    ratio = max(0.0, min(1.0, ratio))
    width = max(0, int((x2 - x1 - 2) * ratio))
    if width:
        draw.rounded_rectangle((x1 + 1, y1 + 1, x1 + 1 + width, y2 - 1), radius=7, fill=color)


def _status_text(unit: BattleUnitState) -> str:
    active = [name for name, turns in unit.status.items() if turns > 0]
    return ", ".join(active)


def _to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
