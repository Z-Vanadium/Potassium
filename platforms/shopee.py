"""
Shopee platform handler.

DOM architecture (2024-2026):
    Search results (desktop SG site):
        <div class="row shopee-search-item-result__items">
          <div class="col-xs-2-4 shopee-search-item-result__item">
            <a href="/product/...">
              <div class="...name...">product name</div>
              <span class="...price...">$XX.XX</span>
            </a>

    Product detail:
        <div class="product-briefing">
          <h1>product title</h1>
          <div class="product-price">price</div>
        <button class="btn-add-to-cart">Add to Cart</button>
        <div class="product-detail">description</div>
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


@register_handler("shopee")
class ShopeeHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "product_card":  'div[class*="shopee-search-item-result__item"], div[class*="col-xs-2-4"]',
            "product_title": 'div[class*="name"], a[class*="name"], div[data-testid="product-name"]',
            "product_link":  "a[href*='/product/'], a[href*='-i.']",
            "product_price": 'span[class*="price"], div[class*="price"]',
            "add_to_cart":   'button[class*="btn-add-to-cart"], button[class*="add-to-cart"]',
            "search_box":    'input[type="search"], input.shopee-searchbar-input__input',
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
                continue
            title = (await title_el.text_content() or "").strip()
            if not title or len(title) < 5:
                continue

            url = ""
            link = card.locator(sel["product_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://shopee.sg{href}" if href.startswith("/") else href

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:150], url=url,
                    selector=f'div[class*="col-xs-2-4"]:nth-child({i+1}) a',
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
            await asyncio.sleep(random.uniform(0.5, 1.2))

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return result

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="/buyer/login"], div.shopee-popup__overlay',
            "logged_in":  'div[class*="navbar__username"], div.shopee-header-user',
            "login_url":  "https://shopee.sg/buyer/login",
        }

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://shopee.sg/search?keyword={kw.replace(' ', '%20')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Shopee] Searching '{kw}' as {profile.display_name}")
