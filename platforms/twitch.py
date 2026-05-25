"""
Twitch platform handler.

DOM architecture (2024-2026):
    Directory / search:
        <article> or <div data-test-selector="...">  ← stream/channel card
          <a href="/...">                            ← channel link
          <h3>stream title</h3>
          <p data-test-selector="game">game name</p>
          <p data-test-selector="viewer-count">viewers</p>

    Channel page:
        <div class="channel-info-content">
          <h1>channel name</h1>
        <video> or <div class="video-player"> live player

    Strategy:
        Browse game categories and stream titles matching profile interests.
        Anonymous viewing of streams works without login.
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from loguru import logger
from platforms.base import PlatformHandler, ContentItem, ActionResult, register_handler

if TYPE_CHECKING:
    from playwright.async_api import Page
    from config.profiles import UserProfile


@register_handler("twitch")
class TwitchHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "stream_card":   "article, div[data-test-selector]",
            "stream_title":  'h3, a[data-test-selector="title"], p[data-a-target="preview-card-title"]',
            "stream_link":   "a[href*='/videos/'], a[href^='/']",
            "game_name":     'p[data-test-selector="game"], a[data-test-selector="game-link"]',
            "search_box":    'input[type="search"], input[placeholder*="Search" i]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(
                f"{sel['stream_card']}, {sel['stream_title']}, h3",
                timeout=10000,
            )
        except Exception:
            return items

        # Twitch cards — scan titles + game names
        cards = page.locator(sel["stream_card"])
        count = await cards.count()
        if count == 0:
            cards = page.locator("h3, p, a")  # fallback: any text
            count = await cards.count()

        for i in range(min(count, 25)):
            card = cards.nth(i)
            title_text = ""

            # Get stream title
            title_el = card.locator(sel["stream_title"]).first
            if await title_el.count() > 0:
                title_text = (await title_el.text_content() or "").strip()

            # Also get game/category name
            game_el = card.locator(sel["game_name"]).first
            game_text = ""
            if await game_el.count() > 0:
                game_text = (await game_el.text_content() or "").strip()

            full_text = f"{title_text} {game_text}".strip()
            if not full_text or len(full_text) < 5:
                continue

            url = ""
            link = card.locator("a").first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://www.twitch.tv{href}" if href.startswith("/") else href

            matches = self.match_interests(full_text, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=full_text[:150], url=url,
                    selector=f"article:nth-child({i+1}) a",
                    relevance_score=best_score, matched_keyword=best_kw, element_index=i,
                ))

        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items

    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        result = ActionResult()

        if item.url:
            await page.goto(item.url, wait_until="domcontentloaded", timeout=15000)
            result.clicked = True
        else:
            clicked = await self.safe_click(page, item.selector, timeout=5000)
            if not clicked:
                result.error = "Could not open stream"
                return result
            result.clicked = True

        # Watch stream for a while (simulated)
        watch_time = random.uniform(5.0, 15.0) * getattr(profile, "reading_multiplier", 1.0)
        elapsed = 0.0
        while elapsed < watch_time:
            # Just wait — simulating watching
            chunk = min(random.uniform(1.0, 4.0), watch_time - elapsed)
            await asyncio.sleep(chunk)
            elapsed += chunk
            # Occasionally scroll chat if visible
            if random.random() < 0.3:
                await page.mouse.wheel(0, random.randint(50, 200))

        if item.url:
            await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return result

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        kw = random.choice(profile.interests)
        url = f"https://www.twitch.tv/search?term={kw.replace(' ', '%20')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Twitch] Searching '{kw}' as {profile.display_name}")
