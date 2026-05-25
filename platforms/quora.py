"""
Quora platform handler.

DOM architecture (2024-2026):
    Feed / search results:
        <div class="q-box">                  ← question/answer container
          <span class="q-text"> or <div>     ← question text
            <a href="/...">question title</a>
          </span>
          <div class="q-text">...            ← answer preview
          <button class="upvote"> or <span>  ← upvote button

    Question page:
        <h1>question title</h1>
        <div class="q-text">question details</div>
        <div class="answer">...</div>
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


@register_handler("quora")
class QuoraHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "question_card":  'div[class*="q-box"] a[href*="/"], div.qu-box--header',
            "question_link":  'a[href*="/"]',
            "question_text":  "span.q-text, div.q-text, div.q-relative",
            "answer_text":    'div.q-text span, div.q-text',
            "upvote_btn":     'button[aria-label*="Upvote" i], span[aria-label*="Upvote" i]',
            "search_box":     'input[name="q"], input[placeholder*="search" i]',
        }

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'div.modal_signup_dialog, div.q-inlineSignupForm, div[class*="SignupModal"]',
            "logged_in":  'div.UserAvatar, img[alt*="profile" i], a[href*="/profile/"]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector("a[href*='/']", timeout=10000)
        except Exception:
            return items

        # Quora's DOM is dense — scan all text-heavy elements
        text_elements = page.locator(sel["question_text"])
        count = await text_elements.count()

        seen: set[str] = set()
        for i in range(min(count, 40)):
            el = text_elements.nth(i)
            title = (await el.text_content() or "").strip()
            if not title or len(title) < 15:
                continue
            norm = title.lower()[:80]
            if norm in seen:
                continue
            seen.add(norm)

            url = ""
            link = el.locator("a").first
            if await link.count() == 0:
                # Look for parent link
                parent = el.locator("..").locator("a").first
                if await parent.count() > 0:
                    link = parent
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://www.quora.com{href}" if href.startswith("/") else href

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:150], url=url,
                    selector=f"span.q-text:nth-child({i+1})",
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
            result.error = "No URL found"
            return result

        await asyncio.sleep(random.uniform(1.5, 3.0))

        # Scroll reading
        reading_time = random.uniform(3.0, 10.0) * getattr(profile, "reading_multiplier", 1.0)
        elapsed = 0.0
        while elapsed < reading_time:
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 2.0))
            elapsed += 1.0

        # Upvote
        if random.random() < getattr(profile, "like_probability", 0.25):
            if await self.safe_click(page, self._get_selectors()["upvote_btn"], timeout=3000):
                result.liked = True

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return result

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.quora.com/search?q={kw.replace(' ', '%20')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Quora] Searching '{kw}' as {profile.display_name}")
