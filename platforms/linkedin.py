"""
LinkedIn platform handler.

DOM architecture (2024-2026):
    Feed:
        <article data-activity-urn="...">       ← each feed post
          <div class="feed-shared-update-v2__description"> ← post text
          <span class="feed-shared-actor__name"> ← author name
          <button aria-label="Like"> or <button aria-label="React Like">
          <button aria-label="Comment">
          <button aria-label="Share">

    Search results:
        <li class="reusable-search__result-container">
          <a href="/...">result title</a>

    Note: Heavy login wall — anonymous browsing is limited to public content.
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


@register_handler("linkedin")
class LinkedInHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "feed_post":     "article[data-activity-urn]",
            "post_text":     'div.feed-shared-update-v2__description, '
                             'div[class*="update-components-text"] span, '
                             'span[class*="break-words"]',
            "post_link":     'a[href*="/feed/update/"]',
            "like_btn":      'button[aria-label*="Like" i], button[aria-label*="React" i]',
            "comment_btn":   'button[aria-label*="Comment" i]',
            "search_box":    'input[aria-label*="Search" i], input.search-global-typeahead__input',
            "result_link":   'a[data-test-app-aware-link]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(
                f"{sel['feed_post']}, {sel['post_text']}, {sel['result_link']}",
                timeout=10000,
            )
        except Exception:
            pass  # Probably login wall

        # Try feed posts first
        posts = page.locator(sel["feed_post"])
        count = await posts.count()

        if count == 0:
            # Fallback: scan any text on page for interests
            text_els = page.locator("span, p, h3")
            t_count = await text_els.count()
            for j in range(min(t_count, 50)):
                try:
                    title = (await text_els.nth(j).text_content() or "").strip()
                    if len(title) < 20:
                        continue
                    matches = self.match_interests(title, profile.interests)
                    if matches:
                        best_kw, best_score = matches[0]
                        items.append(ContentItem(
                            title=title[:150], url="",
                            selector="span", relevance_score=best_score,
                            matched_keyword=best_kw, element_index=0,
                        ))
                except Exception:
                    continue
        else:
            for i in range(min(count, 15)):
                post = posts.nth(i)
                text = post.locator(sel["post_text"]).first
                if await text.count() == 0:
                    continue
                title = (await text.text_content() or "").strip()
                if not title or len(title) < 15:
                    continue

                url = ""
                link = post.locator(sel["post_link"]).first
                if await link.count() > 0:
                    href = await link.get_attribute("href") or ""
                    url = f"https://www.linkedin.com{href}" if href.startswith("/") else href

                matches = self.match_interests(title, profile.interests)
                if matches:
                    best_kw, best_score = matches[0]
                    items.append(ContentItem(
                        title=title[:150], url=url,
                        selector=f"article[data-activity-urn]:nth-child({i+1})",
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

        await asyncio.sleep(random.uniform(2.0, 5.0))

        # Scroll through post
        for _ in range(random.randint(1, 3)):
            await page.mouse.wheel(0, random.randint(150, 400))
            await asyncio.sleep(random.uniform(0.5, 1.5))

        if random.random() < getattr(profile, "like_probability", 0.25):
            if await self.safe_click(page, sel["like_btn"], timeout=3000):
                result.liked = True

        if item.url:
            await page.go_back(wait_until="domcontentloaded", timeout=10000)
        return result

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="/login"], form.login__form, div.authentication-outlet',
            "logged_in":  'div.global-nav__me, div[data-control-name="identity_welcome_message"]',
            "login_url":  "https://www.linkedin.com/login",
        }

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.linkedin.com/search/results/content/?keywords={kw.replace(' ', '%20')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[LinkedIn] Searching '{kw}' as {profile.display_name}")
