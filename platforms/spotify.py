"""
Spotify platform handler.

DOM architecture (2024-2026, open.spotify.com):
    Home / search results:
        <div data-testid="tracklist-row">       ← track in list
          <div>track number / cover</div>
          <div data-testid="internal-track-link">track name</div>
          <span>artist name</span>
          <button aria-label="Save to Your Library">heart</button>
        <div data-testid="play-button">          ← play

    Playlist / album page:
        <div data-testid="playlist-tracklist">
          ...track rows...

    Search page:
        <input data-testid="search-input">
        <div data-testid="herocard-click-handler"> ← top result card
        <section data-testid="track-list">results

    Note: Spotify requires login for most interactions. Anonymous browsing is limited
    to public playlists and search previews.
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


@register_handler("spotify")
class SpotifyHandler(PlatformHandler):

    def _get_selectors(self) -> dict[str, str]:
        return {
            "track_row":     'div[data-testid="tracklist-row"]',
            "track_name":    'div[data-testid="internal-track-link"], a[data-testid="internal-track-link"]',
            "artist_name":   'span[data-testid="artist-name"], a[data-testid="artist-link"]',
            "play_btn":      'button[data-testid="play-button"], button[aria-label*="Play" i]',
            "save_btn":      'button[aria-label*="Save to Your Library" i], '
                             'button[aria-label*="Add to" i]',
            "search_box":    'input[data-testid="search-input"]',
            "top_card":      'div[data-testid="herocard-click-handler"]',
        }

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        sel = self._get_selectors()
        items: list[ContentItem] = []

        try:
            await page.wait_for_selector(
                f"{sel['track_row']}, {sel['top_card']}, {sel['track_name']}",
                timeout=10000,
            )
        except Exception:
            return items

        # Try track rows first
        tracks = page.locator(sel["track_row"])
        count = await tracks.count()

        if count == 0:
            # Fallback: scan any result cards
            tracks = page.locator(f"{sel['top_card']}, a, h2, h3")
            count = await tracks.count()

        for i in range(min(count, 20)):
            track = tracks.nth(i)
            title = ""

            # Get track name + artist
            name_el = track.locator(sel["track_name"]).first
            artist_el = track.locator(sel["artist_name"]).first

            if await name_el.count() > 0:
                title = (await name_el.text_content() or "").strip()
            if await artist_el.count() > 0:
                artist = (await artist_el.text_content() or "").strip()
                title = f"{title} {artist}".strip()

            if not title:
                title = (await track.text_content() or "").strip()

            if not title or len(title) < 3:
                continue

            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title[:150], url=page.url,
                    selector=f'div[data-testid="tracklist-row"]:nth-child({i+1})',
                    relevance_score=best_score, matched_keyword=best_kw, element_index=i,
                ))

        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items

    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        sel = self._get_selectors()
        result = ActionResult()

        # Click to play/preview the track
        if await self.safe_click(page, item.selector, timeout=3000):
            result.clicked = True
        else:
            # Try play button
            await self.safe_click(page, sel["play_btn"], timeout=3000)
            result.clicked = True

        # Listen for a while (simulated)
        await asyncio.sleep(random.uniform(3.0, 10.0))

        # Save/Like (if logged in)
        if random.random() < getattr(profile, "like_probability", 0.35):
            if await self.safe_click(page, sel["save_btn"], timeout=3000):
                result.liked = True

        return result

    def _get_login_detectors(self) -> dict[str, str]:
        return {
            "login_wall": 'button[data-testid="login-button"], a[href*="/login"]',
            "logged_in":  'button[data-testid="user-widget-link"], '
                          'div[data-testid="user-widget-background"]',
            "login_url":  "https://accounts.spotify.com/login",
        }

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        await self.wait_for_login(page, profile)
        kw = random.choice(profile.interests)
        url = f"https://open.spotify.com/search/{kw.replace(' ', '%20')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Spotify] Searching '{kw}' as {profile.display_name}")
