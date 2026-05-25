"""
Expedia platform handler.

DOM architecture (2024-2026):
    Search results:
        <div data-stid="property-listing"> ← hotel listing card
          <h2 data-stid="content-hotel-title">hotel name</h2>
          <div data-stid="content-hotel-address">address</div>
          <span data-stid="content-hotel-price">price</span>
          <div data-stid="content-hotel-reviews">rating</div>

    Property detail:
        <h1>property name</h1>
        <div>description</div>
        <button data-stid="sticky-button">Save</button>
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


@register_handler("expedia")
class ExpediaHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "property_card":  'div[data-stid="property-listing"]',
            "property_title": 'h2[data-stid="content-hotel-title"], h3[data-stid="content-hotel-title"]',
            "property_link":  "a[href*='/hotel/'], a[href*='/Hotel_Information']",
            "property_price": 'span[data-stid="content-hotel-price"], div[data-stid="price-summary"]',
            "save_btn":       'button[data-stid="sticky-button"], button[aria-label*="Save" i]',
            "search_box":     'input[data-stid="destination-field"], input[placeholder*="destination" i]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(f"{sel['property_card']}, {sel['property_title']}", timeout=10000)
        except Exception:
            return items

        cards = page.locator(sel["property_card"])
        count = await cards.count()
        if count == 0:
            cards = page.locator(sel["property_title"])
            count = await cards.count()

        for i in range(min(count, 15)):
            card = cards.nth(i)
            title_el = card.locator(sel["property_title"]).first if sel["property_card"] else card
            if await title_el.count() == 0:
                continue
            title = (await title_el.text_content() or "").strip()
            if not title or len(title) < 3:
                continue

            url = ""
            link = card.locator(sel["property_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://www.expedia.com{href}" if href.startswith("/") else href

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:150], url=url,
                    selector=f'div[data-stid="property-listing"]:nth-child({i+1})',
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
            if not await self.safe_click(page, item.selector, timeout=5000):
                result.error = "Could not open property"
                return result
            result.clicked = True
            await asyncio.sleep(random.uniform(2.0, 4.0))

        for _ in range(random.randint(3, 5)):
            await page.mouse.wheel(0, random.randint(200, 450))
            await asyncio.sleep(random.uniform(0.5, 2.0))

        if random.random() < getattr(profile, "follow_probability", 0.08):
            await self.safe_click(page, self._get_selectors()["save_btn"], timeout=3000)
            result.saved = True

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.5, 3.0))
        return result

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="/user/signin"], button[data-stid="header-menu-signin"]',
            "logged_in":  'button[data-stid="header-menu-account"], div[data-stid="header-menu-account"]',
            "login_url":  "https://www.expedia.com/user/signin",
        }

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.expedia.com/Hotel-Search?destination={kw.replace(' ', '%20')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Expedia] Searching '{kw}' as {profile.display_name}")
