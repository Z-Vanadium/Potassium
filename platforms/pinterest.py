"""
Pinterest platform handler.

DOM architecture (2024-2026):
    Home feed / search results:
        <div data-test-id="pin"> or <div data-grid-item="true">
          <img src="..." alt="Pin title">       ← pin image
          <div data-test-id="pin-title"> ...    ← pin title text
          <a href="/pin/...">                   ← pin detail link

    Pin detail (modal / page):
        <div data-test-id="pin-closeup">
          <img src="...">
          <h1>pin title</h1>
          <div data-test-id="pin-description">... ← description
          <button data-test-id="board-save">...  ← save button
          <div data-test-id="reaction-button">   ← reaction/emoji button

Strategy:
    Pinterest is visual — content matching focuses on pin titles and descriptions.
    Anonymous browsing works; interaction is limited to viewing + scrolling.
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


@register_handler("pinterest")
class PinterestHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "pin_card":       'div[data-test-id="pin"], div[data-grid-item="true"]',
            "pin_image":      "img",
            "pin_title":      'div[data-test-id="pin-title"], div[data-test-id="pinRepTitle"]',
            "pin_link":       "a[href*='/pin/']",
            "pin_desc":       'div[data-test-id="pin-description"], div[data-test-id="description"]',
            "save_btn":       'button[data-test-id="board-save"], button[aria-label*="Save" i]',
            "close_modal":    'button[data-test-id="close-modal"], div[data-test-id="backdrop"]',
            "search_box":     'input[name="search"], input[data-test-id="search-input"]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(f"{sel['pin_card']}, {sel['pin_image']}", timeout=10000)
        except Exception:
            return items

        pins = page.locator(sel["pin_card"])
        count = await pins.count()
        if count == 0:
            pins = page.locator(sel["pin_image"])
            count = await pins.count()

        for i in range(min(count, 30)):
            pin = pins.nth(i)
            # Get alt text from image (Pinterest uses alt for title)
            img = pin.locator("img").first if sel["pin_card"] else pin
            if await img.count() == 0:
                continue
            title = (await img.get_attribute("alt") or "").strip()
            if not title or len(title) < 5:
                continue

            # Get link
            url = ""
            link = pin.locator("a[href*='/pin/']").first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://www.pinterest.com{href}" if href.startswith("/") else href

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title, url=url,
                    selector=f"{sel['pin_card']}:nth-child({i+1}) img" if sel["pin_card"] else f"img:nth-child({i+1})",
                    relevance_score=best_score, matched_keyword=best_kw, element_index=i,
                ))

        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items

    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        sel = self._get_selectors()
        result = ActionResult()

        # Click the pin to view detail
        if item.url:
            await page.goto(item.url, wait_until="domcontentloaded", timeout=15000)
        else:
            clicked = await self.safe_click(page, item.selector, timeout=5000)
            if not clicked:
                result.error = "Could not open pin"
                return result
        result.clicked = True
        await asyncio.sleep(random.uniform(1.5, 3.0))

        # Scroll through the pin detail
        reading_time = random.uniform(2.0, 5.0) * getattr(profile, "reading_multiplier", 1.0)
        elapsed = 0.0
        while elapsed < reading_time:
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.3, 1.2))
            elapsed += 0.5

        # Try to save/like the pin if logged in
        if random.random() < getattr(profile, "like_probability", 0.3):
            if await self.safe_click(page, sel["save_btn"], timeout=3000):
                result.liked = True

        # Go back
        if item.url:
            await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return result

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        # Search for a profile interest
        import random as _random
        kw = _random.choice(profile.interests)
        url = f"https://www.pinterest.com/search/pins/?q={kw.replace(' ', '%20')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(_random.uniform(2.0, 4.0))
        logger.info(f"[Pinterest] Searching '{kw}' as {profile.display_name}")
