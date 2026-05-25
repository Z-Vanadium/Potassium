"""
eBay platform handler.

DOM architecture (2024-2026):
    Search results:
        <li class="s-item s-item__pl-on-bottom">   ← product listing
          <div class="s-item__wrapper">
            <div class="s-item__image">...</div>
            <div class="s-item__info">
              <a class="s-item__link"><h3 class="s-item__title">title</h3></a>
              <span class="s-item__price">$XX.XX</span>
              <span class="s-item__seller">seller info</span>
            </div>

    Product detail:
        <h1 class="it-ttl" id="itemTitle">title</h1>
        <span class="vi-price">price</span>
        <a id="binBtn_btn" class="btn">Buy It Now</a>
        <a class="vi-atw">Add to watchlist</a>
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


@register_handler("ebay")
class EbayHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "product_card":  "li.s-item",
            "product_title": "div.s-item__title span, h3.s-item__title",
            "product_link":  "a.s-item__link",
            "product_price": "span.s-item__price",
            "add_to_watch":  'a[href*="watch"], button[title*="Watch" i], a.vi-atw',
            "search_box":    'input[type="text"][name="_nkw"], input#gh-ac',
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

        for i in range(min(count, 24)):
            card = cards.nth(i)
            title_el = card.locator(sel["product_title"]).first
            if await title_el.count() == 0:
                continue
            title = (await title_el.text_content() or "").strip()
            # Filter out eBay boilerplate
            if not title or len(title) < 5 or title.startswith("New listing") or "Shop on eBay" in title:
                continue

            url = ""
            link = card.locator(sel["product_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = href if href.startswith("http") else ""

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:150], url=url,
                    selector=f"li.s-item:nth-child({i+1}) a.s-item__link",
                    relevance_score=best_score, matched_keyword=best_kw, element_index=i,
                ))

        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items

    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        sel = self._get_selectors()
        result = ActionResult()

        if item.url:
            await page.goto(item.url, wait_until="domcontentloaded", timeout=15000)
            result.clicked = True
        else:
            if not await self.safe_click(page, item.selector, timeout=5000):
                result.error = "Could not open listing"
                return result
            result.clicked = True
            await asyncio.sleep(random.uniform(2.0, 4.0))

        # Browse listing
        for _ in range(random.randint(2, 5)):
            await page.mouse.wheel(0, random.randint(150, 350))
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # Watchlist
        if random.random() < getattr(profile, "follow_probability", 0.06):
            await self.safe_click(page, sel["add_to_watch"], timeout=3000)
            result.saved = True

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return result

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="signin.ebay"], a#gh-ug, span#gh-ug',
            "logged_in":  'a#gh-ug, button#gh-ug, span.gh-ebay-signin-status',
            "login_url":  "https://signin.ebay.com",
        }

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.ebay.com/sch/i.html?_nkw={kw.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[eBay] Searching '{kw}' as {profile.display_name}")
