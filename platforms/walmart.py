"""
Walmart platform handler.

DOM architecture (2024-2026):
    Search results:
        <div data-testid="product-card"> or <div data-item-id="...">
          <span data-testid="product-title"> or <span class="...">title</span>
          <div data-testid="product-price">price</div>
          <a>product link</a>

    Product detail:
        <h1 itemprop="name">product title</h1>
        <span itemprop="price">price</span>
        <button data-testid="add-to-cart">Add to cart</button>
        <button data-testid="add-to-list">Add to list</button>
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


@register_handler("walmart")
class WalmartHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "product_card":  'div[data-testid="product-card"], div[data-item-id]',
            "product_title": 'span[data-testid="product-title"], span[class*="product-title"]',
            "product_link":  "a[link-identifier]",
            "product_price": 'div[data-testid="product-price"], span[itemprop="price"]',
            "add_to_list":   'button[data-testid="add-to-list"], button[aria-label*="Add to list" i]',
            "search_box":    'input[data-testid="search-input"], input[type="search"]',
        }

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="/account/login"], button[data-testid="header-sign-in"]',
            "logged_in":  'span[data-testid="header-greeting"], a[data-testid="header-account-link"]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(sel["product_card"], timeout=10000)
        except Exception:
            return items

        cards = page.locator(sel["product_card"])
        count = await cards.count()

        for i in range(min(count, 20)):
            card = cards.nth(i)
            title_el = card.locator(sel["product_title"]).first
            if await title_el.count() == 0:
                # Fallback: any text content
                title_el = card.locator("span, p, div").first
                if await title_el.count() == 0:
                    continue
            title = (await title_el.text_content() or "").strip()
            if not title or len(title) < 5:
                continue

            url = ""
            link = card.locator(sel["product_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://www.walmart.com{href}" if href.startswith("/") else href

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:150], url=url,
                    selector=f'div[data-testid="product-card"]:nth-child({i+1}) a',
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

        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(150, 350))
            await asyncio.sleep(random.uniform(0.5, 1.5))

        if random.random() < getattr(profile, "follow_probability", 0.05):
            await self.safe_click(page, self._get_selectors()["add_to_list"], timeout=3000)
            result.saved = True

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return result

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.walmart.com/search?q={kw.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Walmart] Searching '{kw}' as {profile.display_name}")
