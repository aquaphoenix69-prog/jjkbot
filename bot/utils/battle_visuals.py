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
    left_focus = _pick_focus_unit(snapshot.left_team)
    right_focus = _pick_focus_unit(snapshot.right_team)

    left_image, right_image = await _download_pair(left_focus.image_url, right_focus.image_url)

    canvas = Image.new("RGB", (960, 540), (30, 14, 18))
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.load_default()
    text_font = ImageFont.load_default()

    for y in range(canvas.height):
        blend = y / max(1, canvas.height - 1)
        color = (
            int(36 + 70 * blend),
            int(16 + 28 * blend),
            int(20 + 12 * blend),
        )
        draw.line([(0, y), (canvas.width, y)], fill=color)

    draw.rounded_rectangle((26, 24, 454, 516), radius=24, fill=(49, 24, 30), outline=(99, 200, 196), width=3)
    draw.rounded_rectangle((506, 24, 934, 516), radius=24, fill=(49, 24, 30), outline=(241, 94, 94), width=3)
    draw.rounded_rectangle((418, 188, 542, 352), radius=16, fill=(24, 10, 12), outline=(255, 224, 145), width=3)
    draw.text((454, 255), "VS", font=title_font, fill=(255, 255, 255), anchor="mm")

    _paste_card(canvas, left_image, (56, 70), left_focus)
    _paste_card(canvas, right_image, (536, 70), right_focus)

    _draw_panel(draw, left_focus, snapshot.left_team, (42, 356, 438, 496), left=True, font=text_font)
    _draw_panel(draw, right_focus, snapshot.right_team, (522, 356, 918, 496), left=False, font=text_font)

    return _to_png_bytes(canvas), "battle_snapshot.png"


async def _download_pair(left_url: str, right_url: str) -> tuple[Image.Image, Image.Image]:
    timeout = aiohttp.ClientTimeout(total=12)
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        return await _download_image(session, left_url), await _download_image(session, right_url)


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


def _paste_card(canvas: Image.Image, image: Image.Image, pos: tuple[int, int], unit: BattleUnitState) -> None:
    card = image.copy().resize((360, 240))
    frame = Image.new("RGB", (372, 252), RARITY_COLORS.get(unit.rarity.lower(), (170, 170, 170)))
    frame.paste(card, (6, 6))
    canvas.paste(frame, pos)


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    focus: BattleUnitState,
    team: list[BattleUnitState],
    bounds: tuple[int, int, int, int],
    *,
    left: bool,
    font: ImageFont.ImageFont,
) -> None:
    x1, y1, x2, y2 = bounds
    draw.rounded_rectangle(bounds, radius=18, fill=(25, 12, 16), outline=(255, 255, 255), width=1)
    anchor = "la" if left else "ra"
    name_x = x1 + 18 if left else x2 - 18
    draw.text((name_x, y1 + 12), f"{focus.name}  Lv.{focus.level}  Evo {focus.evolution_stage}", fill=(255, 255, 255), font=font, anchor=anchor)
    hp_text = f"HP {focus.hp:,}/{focus.max_hp:,}"
    en_text = f"Energy {focus.energy}/{focus.max_energy}"
    draw.text((name_x, y1 + 34), hp_text, fill=(214, 255, 214), font=font, anchor=anchor)
    draw.text((name_x, y1 + 52), en_text, fill=(193, 243, 255), font=font, anchor=anchor)
    _draw_bar(draw, (x1 + 18, y1 + 76, x2 - 18, y1 + 96), focus.hp / max(1, focus.max_hp), (38, 228, 57))
    _draw_bar(draw, (x1 + 18, y1 + 106, x2 - 18, y1 + 126), focus.energy / max(1, focus.max_energy), (103, 230, 255))
    roster_y = y1 + 138
    for unit in team[:3]:
        marker = ">" if unit.name == focus.name else "-"
        status = _status_text(unit)
        label = f"{marker} {unit.name} {unit.hp:,}/{unit.max_hp:,}"
        if status:
            label = f"{label} [{status}]"
        draw.text((name_x, roster_y), label, fill=(230, 230, 230), font=font, anchor=anchor)
        roster_y += 18


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


def _pick_focus_unit(team: list[BattleUnitState]) -> BattleUnitState:
    for unit in team:
        if unit.hp > 0:
            return unit
    return team[0]


def _to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
