"""
Human-like behavior simulation helpers.

Generates natural delays, mouse movements, typing patterns, and
scrolling behavior. Every interaction should look like a real
human, not a script.
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from playwright.async_api import Page


# ── Timing helpers ──────────────────────────────────────────────────────────


def human_delay(min_s: float = 0.5, max_s: float = 3.0) -> float:
    """
    Generate a random human-like delay duration.

    Uses a gamma-like distribution so most delays cluster near the
    lower end, with occasional longer pauses.
    """
    raw = random.betavariate(alpha=2, beta=5)
    return min_s + raw * (max_s - min_s)


async def think_pause(min_s: float = 0.8, max_s: float = 4.0) -> None:
    """Simulate a human thinking before an action."""
    delay = human_delay(min_s, max_s)
    logger.debug(f"Thinking for {delay:.1f}s")
    await asyncio.sleep(delay)


async def action_cooldown(min_s: float = 60.0, max_s: float = 180.0) -> None:
    """Wait between major actions to avoid rate limiting."""
    delay = human_delay(min_s, max_s)
    logger.info(f"Cooldown for {delay:.1f}s")
    await asyncio.sleep(delay)


# ── Typing simulation ───────────────────────────────────────────────────────


async def type_like_human(
    page: Page,
    text: str,
    min_delay_ms: int = 50,
    max_delay_ms: int = 150,
) -> None:
    """
    Type text one character at a time with random delays.

    Simulates natural typing: varying speed, occasional pauses
    at punctuation/space boundaries, and rare typos.

    Args:
        page: The Playwright page.
        text: The text to type.
        min_delay_ms: Minimum delay between keystrokes (ms).
        max_delay_ms: Maximum delay between keystrokes (ms).
    """
    for i, char in enumerate(text):
        # Natural pause at word boundaries
        if char == " " and random.random() < 0.3:
            await asyncio.sleep(random.uniform(0.08, 0.25))

        # Longer pauses at punctuation
        if char in "，。！？、,.!?":
            await asyncio.sleep(random.uniform(0.1, 0.35))

        # Occasionally hesitate mid-word
        if random.random() < 0.02:
            await asyncio.sleep(random.uniform(0.15, 0.5))

        await page.keyboard.type(char, delay=random.randint(min_delay_ms, max_delay_ms))

        # Rare typo + delete (2% chance per character in certain positions)
        if i > 0 and i < len(text) - 1 and random.random() < 0.015:
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            await page.keyboard.type(wrong_char, delay=random.randint(20, 60))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.05, 0.15))
            # Re-type correct char
            await page.keyboard.type(char, delay=random.randint(min_delay_ms, max_delay_ms))

    logger.debug(f"Typed {len(text)} chars in human-like mode")


# ── Mouse movement simulation ───────────────────────────────────────────────


async def move_mouse_to(
    page: Page,
    target_x: float,
    target_y: float,
    steps: int | None = None,
) -> None:
    """
    Move the mouse to a target position using a bezier-like path.

    This avoids instant teleportation which bots use.
    """
    current = await page.evaluate("() => ({ x: window.mouseX || 0, y: window.mouseY || 0 })")
    start_x, start_y = current["x"], current["y"]

    if steps is None:
        steps = random.randint(15, 40)

    # Generate a curved path with random overshoot
    for i in range(steps + 1):
        t = i / steps
        # Ease-in-out curve
        eased = t * t * (3 - 2 * t)

        # Add random wobble
        wobble_x = random.uniform(-3, 3) * (1 - abs(2 * t - 1))  # less wobble at ends
        wobble_y = random.uniform(-3, 3) * (1 - abs(2 * t - 1))

        x = start_x + (target_x - start_x) * eased + wobble_x
        y = start_y + (target_y - start_y) * eased + wobble_y

        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.002, 0.008))

    # Set current position for next move
    await page.evaluate(
        f"() => {{ window.mouseX = {target_x}; window.mouseY = {target_y}; }}"
    )


async def click_like_human(
    page: Page,
    selector: str,
    double_click: bool = False,
) -> None:
    """Click an element with human-like mouse movement."""
    locator = page.locator(selector)
    box = await locator.bounding_box()
    if not box:
        logger.warning(f"Element not found: {selector}")
        return

    # Click at a random position within the element
    target_x = box["x"] + random.uniform(0, box["width"])
    target_y = box["y"] + random.uniform(0, box["height"])

    await move_mouse_to(page, target_x, target_y)
    await asyncio.sleep(random.uniform(0.05, 0.2))

    if double_click:
        await page.mouse.dblclick(target_x, target_y)
    else:
        await page.mouse.click(target_x, target_y)

    logger.debug(f"Clicked '{selector}' at ({target_x:.0f}, {target_y:.0f})")


# ── Scrolling simulation ────────────────────────────────────────────────────


async def scroll_like_human(
    page: Page,
    total_scroll: int = 1000,
    style: str = "normal",
) -> None:
    """
    Scroll vertically with natural pauses and speed variations.

    Args:
        page: The page.
        total_scroll: Total pixels to scroll.
        style: "fast" (skimming), "normal", "slow" (reading), "reader" (very slow).
    """
    style_config = {
        "fast":   {"step_min": 80,  "step_max": 200, "pause_min": 0.5, "pause_max": 2.0},
        "normal": {"step_min": 40,  "step_max": 100, "pause_min": 1.0, "pause_max": 4.0},
        "slow":   {"step_min": 20,  "step_max": 60,  "pause_min": 2.0, "pause_max": 6.0},
        "reader": {"step_min": 10,  "step_max": 40,  "pause_min": 3.0, "pause_max": 10.0},
    }
    cfg = style_config.get(style, style_config["normal"])

    scrolled = 0
    while scrolled < total_scroll:
        step = random.randint(int(cfg["step_min"]), int(cfg["step_max"]))
        remaining = total_scroll - scrolled
        step = min(step, remaining)

        await page.mouse.wheel(0, step)
        scrolled += step

        pause = human_delay(cfg["pause_min"], cfg["pause_max"])
        await asyncio.sleep(pause)

        # Occasionally scroll back up a little (re-reading)
        if random.random() < 0.08:
            back = random.randint(20, 80)
            await page.mouse.wheel(0, -back)
            await asyncio.sleep(0.5)

    logger.debug(f"Scrolled {scrolled}px in '{style}' mode")


async def random_scroll_behavior(page: Page, style: str = "normal") -> None:
    """
    Perform a random browsing scroll session.

    Scrolls 3-8 viewport heights with pauses, simulating a user
    casually browsing a feed.
    """
    viewport = page.viewport_size or {"height": 720}
    viewport_height = viewport["height"]

    scroll_segments = random.randint(3, 8)
    for _ in range(scroll_segments):
        scroll_amount = random.randint(viewport_height // 2, viewport_height * 2)
        await scroll_like_human(page, scroll_amount, style=style)

        # Standstill — reading content
        read_time = human_delay(1.5, 8.0)
        await asyncio.sleep(read_time)


# ── Entry/init ──────────────────────────────────────────────────────────────


async def init_mouse_tracker(page: Page) -> None:
    """Initialize mouse position tracking on a page."""
    await page.evaluate("""
        window.mouseX = 0;
        window.mouseY = 0;
        document.addEventListener('mousemove', (e) => {
            window.mouseX = e.clientX;
            window.mouseY = e.clientY;
        });
    """)
