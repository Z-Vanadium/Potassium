"""
YouTube platform handler.

DOM architecture (2024-2026):
    Home / search results:
        <ytd-rich-item-renderer>                ← video card (home page)
        <ytd-video-renderer>                     ← video card (search/channel)
          <a id="video-title" href="/watch?v=...">video title</a>
          <a class="yt-simple-endpoint">channel name</a>
          <span class="inline-metadata-item">views · time ago</span>

    Watch page:
        <div id="above-the-fold">
          <h1 class="style-scope ytd-watch-metadata">video title</h1>
          <div id="owner">channel info</div>
        <div id="below">
          <ytd-comments id="comments">comments section</div>
        <button aria-label="like this video">like button</button>
        <button aria-label="Subscribe">subscribe button</button>

    Strategy:
        Search for profile-relevant content, browse video cards, watch videos,
        simulate engagement (view time, scroll comments, like).
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


@register_handler("youtube")
class YouTubeHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "video_card":    "ytd-video-renderer, ytd-rich-item-renderer",
            "video_title":   "a#video-title, h3 a#video-title",
            "video_link":    "a#video-title",
            "channel_name":  "a.yt-simple-endpoint.style-scope.ytd-channel-name, "
                             "ytd-channel-name a",
            "like_btn":      'button[aria-label*="like this video" i], '
                             'ytd-segmented-like-dislike-button-renderer button:first-child',
            "subscribe_btn": 'button[aria-label*="Subscribe" i], '
                             '#subscribe-button button',
            "comment_input": "#simple-box  yt-formatted-string, #placeholder-area",
            "search_box":    'input#search, input[name="search_query"]',
        }

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="ServiceLogin"], paper-button[aria-label*="Sign in" i]',
            "logged_in":  'button#avatar-btn img, yt-img-shadow#avatar img',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(
                f"{sel['video_card']}, {sel['video_title']}",
                timeout=10000,
            )
        except Exception:
            return items

        videos = page.locator(sel["video_card"])
        count = await videos.count()

        if count == 0:
            # Fallback: just scan video title links
            videos = page.locator(sel["video_title"])
            count = await videos.count()

        for i in range(min(count, 20)):
            video = videos.nth(i)
            title_el = video.locator(sel["video_title"]).first
            if await title_el.count() == 0:
                continue
            title = (await title_el.text_content() or "").strip()
            if not title or len(title) < 5:
                continue

            # Also get channel name for better matching
            channel = ""
            ch_el = video.locator(sel["channel_name"]).first
            if await ch_el.count() > 0:
                channel = (await ch_el.text_content() or "").strip()

            url = ""
            link = video.locator(sel["video_link"]).first
            if await link.count() > 0:
                href = await link.get_attribute("href") or ""
                url = f"https://www.youtube.com{href}" if href.startswith("/") else href

            full_text = f"{title} {channel}"
            matches = self.match_interests(full_text, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=full_text[:150], url=url,
                    selector=f"{sel['video_card']}:nth-child({i+1}) a#video-title",
                    relevance_score=best_score, matched_keyword=best_kw, element_index=i,
                ))

        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items

    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        sel = self._get_selectors()
        result = ActionResult()

        # Open video
        if item.url:
            await page.goto(item.url, wait_until="domcontentloaded", timeout=15000)
            result.clicked = True
        else:
            if not await self.safe_click(page, item.selector, timeout=5000):
                result.error = "Could not open video"
                return result
            result.clicked = True
            await asyncio.sleep(random.uniform(2.0, 4.0))

        # Watch simulation: scroll to comments, pause, scroll back
        watch_time = random.uniform(4.0, 12.0) * getattr(profile, "reading_multiplier", 1.0)
        elapsed = 0.0
        while elapsed < watch_time:
            await page.mouse.wheel(0, random.randint(100, 400))
            await asyncio.sleep(random.uniform(0.5, 2.0))
            elapsed += 1.0

        # Like
        if random.random() < getattr(profile, "like_probability", 0.25):
            if await self.safe_click(page, sel["like_btn"], timeout=3000):
                result.liked = True

        # Subscribe
        if random.random() < getattr(profile, "follow_probability", 0.04):
            await self.safe_click(page, sel["subscribe_btn"], timeout=3000)

        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.5))
        return result

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://www.youtube.com/results?search_query={kw.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[YouTube] Searching '{kw}' as {profile.display_name}")
