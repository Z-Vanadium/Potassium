"""
AliExpress platform handler.

DOM architecture (2024-2026):
    Search results:
        <div class="list--gallery--...">          ← product grid
          <div class="product-snippet_...">        ← product card
            <a href="/item/...">product link</a>
            <h3 class="product-snippet_Title_...">title</h3>
            <span class="product-price_...">price</span>

    Product detail:
        <h1 class="product-title">title</h1>
        <span class="product-price">price</span>
        <button class="add-to-cart">Add to Cart</button>
        <span class="add-to-wishlist">Wishlist</span>

    Note: AliExpress uses heavily obfuscated CSS class names (CSS modules).
    Using attribute and structural selectors instead.
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


@register_handler("aliexpress")
class AliExpressHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "product_card":  'div[class*="product"], div[class*="list-item"], div[class*="item-card"]',
            "product_title": "h3, a[href*='/item/']",
            "product_link":  "a[href*='/item/']",
            "product_price": 'span[class*="price"]',
            "add_to_wish":   'span[class*="wishlist"], button[class*="wishlist"]',
            "search_box":    'input[type="search"], input[type="text"]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        # AliExpress lazy-loads — wait for any product content
        try:
            await page.wait_for_selector(f"{sel['product_card']}, {sel['product_link']}", timeout=10000)
        except Exception:
            return items

        cards = page.locator(sel["product_card"])
        count = await cards.count()
        if count == 0:
            cards = page.locator(sel["product_link"])
            count = await cards.count()

        for i in range(min(count, 20)):
            card = cards.nth(i)
            # Title: try h3 first, then the link text
            title_el = card.locator(sel["product_title"]).first
            if await title_el.count() == 0:
                continue
            title = (await title_el.text_content() or "").strip()
            if not title or len(title) < 5:
                continue

            url = ""
            link = card.locator(sel["product_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https:{href}" if href.startswith("//") else href

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:150], url=url,
                    selector=f'a[href*="/item/"]:nth-child({i+1})',
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
                result.error = "Could not open product"
                return result
            result.clicked = True
            await asyncio.sleep(random.uniform(2.0, 4.0))

        # Browse detail
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(150, 400))
            await asyncio.sleep(random.uniform(0.5, 1.5))

        if random.random() < getattr(profile, "follow_probability", 0.06):
            await self.safe_click(page, self._get_selectors()["add_to_wish"], timeout=3000)
            result.saved = True

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return result

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="/login"], div.login-modal, div[class*="SignIn"]',
            "logged_in":  'div[class*="user-account"], div[class*="my-account"]',
            "login_url":  "https://login.aliexpress.com",
        }

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.aliexpress.com/wholesale?SearchText={kw.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[AliExpress] Searching '{kw}' as {profile.display_name}")
