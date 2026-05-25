"""
Booking.com platform handler.

DOM architecture (2024-2026):
    Search results:
        <div data-testid="property-card">         ← hotel/property card
          <div data-testid="title">hotel name</div>
          <div data-testid="address">location</div>
          <div data-testid="review-score">rating</div>
          <span data-testid="price">price</span>
          <a data-testid="property-card-desktop-single-image">link</a>

    Property detail:
        <h2>property name</h2>
        <div data-testid="review-score-right">rating</div>
        <div data-testid="property-description">description</div>
        <button data-testid="add-to-trip">Save to trip</button>
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


@register_handler("booking")
class BookingHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "property_card":  'div[data-testid="property-card"]',
            "property_title": 'div[data-testid="title"]',
            "property_link":  'a[data-testid="property-card-desktop-single-image"], '
                              'a[data-testid="title-link"]',
            "property_price": 'span[data-testid="price-and-discounted-price"]',
            "review_score":   'div[data-testid="review-score"]',
            "save_btn":       'button[data-testid="add-to-trip"], button[aria-label*="Save" i]',
            "search_box":     'input[name="ss"], input[data-testid="destination-container"] input',
        }

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[data-testid="header-sign-in"], a[href*="/sign-in"]',
            "logged_in":  'div[data-testid="header-profile"], button[data-testid="header-account-menu"]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(sel["property_card"], timeout=10000)
        except Exception:
            return items

        cards = page.locator(sel["property_card"])
        count = await cards.count()

        for i in range(min(count, 20)):
            card = cards.nth(i)
            title_el = card.locator(sel["property_title"]).first
            if await title_el.count() == 0:
                continue
            title = (await title_el.text_content() or "").strip()
            if not title or len(title) < 3:
                continue

            url = ""
            link = card.locator(sel["property_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://www.booking.com{href}" if href.startswith("/") else href

            # Also get location for better matching
            address = ""
            addr_el = card.locator('div[data-testid="address"]').first
            if await addr_el.count() > 0:
                address = (await addr_el.text_content() or "").strip()

            full_text = f"{title} {address}"
            matches = self.match_interests(full_text, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=full_text[:150], url=url,
                    selector=f'div[data-testid="property-card"]:nth-child({i+1})',
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
                result.error = "Could not open property"
                return result
            result.clicked = True
            await asyncio.sleep(random.uniform(2.0, 4.0))

        # Browse property details (scroll through photos, description, reviews)
        for _ in range(random.randint(3, 6)):
            await page.mouse.wheel(0, random.randint(200, 450))
            await asyncio.sleep(random.uniform(0.5, 2.0))

        # Save/bookmark
        if random.random() < getattr(profile, "follow_probability", 0.08):
            await self.safe_click(page, sel["save_btn"], timeout=3000)
            result.saved = True

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.5, 3.0))
        return result

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.booking.com/searchresults.html?ss={kw.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Booking] Searching '{kw}' as {profile.display_name}")
