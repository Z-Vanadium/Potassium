"""
Amazon platform handler.

DOM architecture (2024-2026):
    Search results:
        <div data-component-type="s-search-result" data-asin="...">  ← product card
          <h2><a><span>product title</span></a></h2>
          <span class="a-price"><span class="a-offscreen">$XX.XX</span></span>
          <span class="a-icon-alt">X.X out of 5 stars</span>
          <a class="a-link-normal">product image</a>

    Product detail:
        <span id="productTitle">product title</span>
        <span class="a-price">price</span>
        <div id="feature-bullets">features</div>
        <input id="add-to-cart-button"> or <button id="add-to-cart-button">
        <input id="add-to-wishlist"> or <a id="wishlistButton">

    Strategy:
        Search for profile-relevant products, browse results, view detail pages,
        simulate "shopping" behavior (view, scroll, optionally add to wishlist).
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


@register_handler("amazon")
class AmazonHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "product_card":  'div[data-component-type="s-search-result"]',
            "product_title": "h2 a span, h2 span.a-text-normal",
            "product_link":  "h2 a, a.a-link-normal.s-underline-text",
            "product_price": "span.a-price span.a-offscreen, span.a-price",
            "product_rating": "span.a-icon-alt",
            "add_to_cart":   "#add-to-cart-button, input#add-to-cart-button",
            "add_to_wishlist": "#wishListMainButton, a#wishlistButton",
            "search_box":     "#twotabsearchtextbox, input#nav-search-keywords",
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
            if not title or len(title) < 5:
                continue

            url = ""
            link = card.locator(sel["product_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://www.amazon.com{href}" if href.startswith("/") else href

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:150], url=url,
                    selector=f'div[data-component-type="s-search-result"]:nth-child({i+1}) h2 a',
                    relevance_score=best_score, matched_keyword=best_kw, element_index=i,
                ))

        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items

    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        sel = self._get_selectors()
        result = ActionResult()

        # Open product detail
        if item.url:
            await page.goto(item.url, wait_until="domcontentloaded", timeout=15000)
            result.clicked = True
        else:
            clicked = await self.safe_click(page, item.selector, timeout=5000)
            if clicked:
                await asyncio.sleep(random.uniform(2.0, 4.0))
                result.clicked = True
            else:
                result.error = "Could not open product"
                return result

        # Browse product detail (scroll through images, description, reviews)
        reading_time = random.uniform(3.0, 8.0)
        elapsed = 0.0
        while elapsed < reading_time:
            await page.mouse.wheel(0, random.randint(150, 400))
            await asyncio.sleep(random.uniform(0.5, 1.5))
            elapsed += 0.75

        # Optionally add to wishlist (simulates purchase intent)
        if random.random() < getattr(profile, "follow_probability", 0.05):
            await self.safe_click(page, sel["add_to_wishlist"], timeout=3000)
            result.saved = True

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.5))
        return result

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": '#nav-signin-tooltip, a#nav-link-accountList[href*="signin"], '
                          'div[data-csa-c-content-id="nav_ya_signin"]',
            "logged_in":  'a#nav-link-accountList span.nav-line-1, '
                          'span#nav-link-accountList-nav-line-1',
            "login_url":  "https://www.amazon.com/ap/signin",
        }

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.amazon.com/s?k={kw.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Amazon] Searching '{kw}' as {profile.display_name}")
