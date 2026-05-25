"""
Twitter/X platform handler.

DOM architecture (2024-2026):
    Timeline / search:
        <article data-testid="tweet">          ← each tweet
          <div data-testid="tweetText">...     ← tweet body text
          <div data-testid="User-Name">...     ← @handle + display name
          <button data-testid="like">          ← heart/like
          <button data-testid="retweet">       ← retweet
          <button data-testid="reply">         ← reply
          <button data-testid="bookmark">      ← bookmark
          <a href="/.../status/...">           ← tweet permalink (time element)

    Tweet detail:
        Same structure, plus replies below.
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


@register_handler("twitter")
class TwitterHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "tweet":         'article[data-testid="tweet"]',
            "tweet_text":    'div[data-testid="tweetText"]',
            "tweet_link":    'a[href*="/status/"]',
            "like_btn":      'button[data-testid="like"]',
            "retweet_btn":   'button[data-testid="retweet"]',
            "reply_btn":     'button[data-testid="reply"]',
            "search_box":    'input[data-testid="SearchBox_Search_Input"], input[aria-label*="Search" i]',
        }

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'a[href*="/login"], div[data-testid="loginButton"]',
            "logged_in":  'a[data-testid="AppTabBar_Home_Link"], article[data-testid="tweet"]',
            "login_url":  "https://x.com/i/flow/login",
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(f"{sel['tweet']}, {sel['tweet_text']}", timeout=10000)
        except Exception:
            return items

        tweets = page.locator(sel["tweet"])
        count = await tweets.count()
        if count == 0:
            # Try just scanning for tweet text
            texts = page.locator(sel["tweet_text"])
            count = await texts.count()
            for i in range(min(count, 30)):
                title = (await texts.nth(i).text_content() or "").strip()
                if not title or len(title) < 10:
                    continue
                matches = self.match_interests(title, profile.interests)
                if matches:
                    best_kw, best_score = matches[0]
                    items.append(ContentItem(
                        title=title[:150], url="",
                        selector=f'div[data-testid="tweetText"]:nth-child({i+1})',
                        relevance_score=best_score, matched_keyword=best_kw, element_index=i,
                    ))
        else:
            for i in range(min(count, 25)):
                tweet = tweets.nth(i)
                text = tweet.locator(sel["tweet_text"]).first
                if await text.count() == 0:
                    continue
                title = (await text.text_content() or "").strip()
                if not title or len(title) < 10:
                    continue

                url = ""
                link = tweet.locator(sel["tweet_link"]).first
                if await link.count() > 0:
                    href = await link.get_attribute("href") or ""
                    url = f"https://x.com{href}" if href.startswith("/") else href

                matches = self.match_interests(title, profile.interests)
                if matches:
                    best_kw, best_score = matches[0]
                    items.append(ContentItem(
                        title=title[:150], url=url,
                        selector=f'article[data-testid="tweet"]:nth-child({i+1})',
                        relevance_score=best_score, matched_keyword=best_kw, element_index=i,
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
                result.error = "Could not open tweet"
                return result
        result.clicked = True
        await asyncio.sleep(random.uniform(1.5, 3.0))

        # Read time (tweets are short — brief scroll)
        reading_time = random.uniform(1.0, 3.0)
        await asyncio.sleep(reading_time)

        # Like
        if random.random() < getattr(profile, "like_probability", 0.25):
            if await self.safe_click(page, sel["like_btn"], timeout=3000):
                result.liked = True

        if item.url:
            await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return result

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://x.com/search?q={kw.replace(' ', '%20')}&f=top"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Twitter] Searching '{kw}' as {profile.display_name}")
