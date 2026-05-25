"""
Tumblr platform handler.

DOM architecture (2024-2026):
    Dashboard / blog feed:
        <article class="...">                ← each post
          <header>...</header>
          <div class="post-content">         ← text/images/video
          <footer>
            <button class="like">            ← heart/like button
            <button class="reblog">          ← reblog button
            <a class="post-link">            ← permalink

Strategy:
    Tumblr is text+visual heavy. Content matching on post body text.
    Anonymous browsing works for public blogs.
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


@register_handler("tumblr")
class TumblrHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "post":          "article",
            "post_content":  "div.post-content, div.body-text, div.reblog-content",
            "post_text":     "div.post-content p, div.body-text p",
            "like_btn":      'button[aria-label*="Like" i], .like_button, button.like',
            "reblog_btn":    'button[aria-label*="Reblog" i], .reblog_button',
            "post_link":     "a.post-link, a[href*='/post/']",
            "tags":          "a.post-tag, .tag-link",
            "search_box":    'input[name="q"], input[placeholder*="search" i]',
        }

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="/login"], div[class*="logged_out"], button[class*="signup"]',
            "logged_in":  'a[aria-label="Account" i], button[aria-label*="Account" i], div[class*="avatar"]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(sel["post"], timeout=10000)
        except Exception:
            return items

        posts = page.locator(sel["post"])
        count = await posts.count()

        for i in range(min(count, 25)):
            post = posts.nth(i)
            # Extract all text from post content
            text_parts = []
            for text_sel in [sel["post_text"], sel["post_content"], "p", "h2"]:
                try:
                    texts = post.locator(text_sel)
                    t_count = await texts.count()
                    for j in range(min(t_count, 5)):
                        t = await texts.nth(j).text_content()
                        if t:
                            text_parts.append(t.strip())
                except Exception:
                    pass

            title = " ".join(text_parts)[:200]
            if not title or len(title) < 10:
                # Try article text directly
                title = (await post.text_content() or "")[:200].strip()
            if not title or len(title) < 10:
                continue

            url = ""
            link = post.locator(sel["post_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = href if href.startswith("http") else f"https://www.tumblr.com{href}"

            # Also check tags
            tags = post.locator(sel["tags"])
            tag_count = await tags.count()
            tag_texts = []
            for j in range(min(tag_count, 10)):
                t = await tags.nth(j).text_content()
                if t:
                    tag_texts.append(t.strip().lstrip("#"))
            full_text = title + " " + " ".join(tag_texts)

            matches = self.match_interests(full_text, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:120], url=url,
                    selector=f"article:nth-child({i+1})",
                    relevance_score=min(best_score * 1.1, 1.0),  # tags boost
                    matched_keyword=best_kw, element_index=i,
                ))

        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items

    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        sel = self._get_selectors()
        result = ActionResult()

        if item.url:
            await page.goto(item.url, wait_until="domcontentloaded", timeout=15000)
        else:
            clicked = await self.safe_click(page, item.selector, timeout=5000)
            if not clicked:
                result.error = "Could not open post"
                return result
        result.clicked = True
        await asyncio.sleep(random.uniform(2.0, 4.0))

        # Scroll through the post
        reading_time = random.uniform(3.0, 8.0) * getattr(profile, "reading_multiplier", 1.0)
        elapsed = 0.0
        while elapsed < reading_time:
            await page.mouse.wheel(0, random.randint(80, 250))
            await asyncio.sleep(random.uniform(0.3, 1.5))
            elapsed += 0.5

        # Like
        if random.random() < getattr(profile, "like_probability", 0.3):
            if await self.safe_click(page, sel["like_btn"], timeout=3000):
                result.liked = True

        if item.url:
            await page.go_back(wait_until="domcontentloaded", timeout=10000)
        return result

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.tumblr.com/search/{kw.replace(' ', '%20')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Tumblr] Searching '{kw}' as {profile.display_name}")
