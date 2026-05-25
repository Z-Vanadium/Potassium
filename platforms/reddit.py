"""
Reddit platform handler.

DOM architecture (Reddit new/shreddit design, ca. 2024-2026):
    Feed page (reddit.com or reddit.com/r/...):
        <shreddit-feed>
          <shreddit-post>           ← each post
            <a slot="title">...     ← post title (clickable link)
            <button upvote="">      ← upvote button
            <button downvote="">    ← downvote button
            <a href="/r/...">       ← subreddit link
            <faceplate-tracker>     ← metadata (author, time, comment count)

    Post detail page:
        <shreddit-post>             ← full post view
          <h1 slot="title">...      ← post title
          <div slot="text-body">... ← post body text
        <shreddit-composer>         ← comment input (if logged in)
        <shreddit-comment-tree>     ← comments section

Strategy:
    1. Navigate to reddit.com (anonymous works for browsing)
    2. Scan feed for posts whose titles match profile interests
    3. Click into top matches
    4. Scroll through post content (simulated reading)
    5. Optionally upvote (platform tracks anonymous votes via cookies)
    6. Go back to feed, repeat for next match
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from loguru import logger

from platforms.base import (
    PlatformHandler,
    ContentItem,
    ActionResult,
    BrowseResult,
    register_handler,
)

if TYPE_CHECKING:
    from playwright.async_api import Page
    from config.profiles import UserProfile
    from core.context_manager import AccountContext


@register_handler("reddit")
class RedditHandler(PlatformHandler):
    """
    Reddit-specific handler.

    Callbacks:
        on_content_found(item)  — called when a matching post is discovered
        on_interact(item, action) — called after clicking/voting on a post
    """

    # ── CSS selectors for Reddit's current DOM ─────────────────────────────

    def _get_selectors(self) -> dict[str, str]:
        return {
            # Feed page
            "post_container":  "shreddit-post",
            "post_title":      "a[slot='title']",
            "post_link":       "a[slot='title']",
            "upvote_btn":      "button[upvote]",
            "downvote_btn":    "button[downvote]",
            "comment_link":    "a[href*='/comments/']",
            "subreddit_link":  "a[href*='/r/']",

            # Post detail page
            "post_body":       "div[slot='text-body']",
            "comment_input":   "shreddit-composer div[contenteditable], "
                               "div[contenteditable='true'][aria-label*='comment' i], "
                               "textarea[placeholder*='comment' i]",

            # Feed container
            "feed_container":  "shreddit-feed",

            # Fallback: old selectors for old.reddit.com
            "old_post":        "div.thing[data-fullname]",
            "old_title":       "a.title",
            "old_upvote":      "div.arrow.up",
        }

    # ── Find content matching profile interests ────────────────────────────

    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        """
        Scan Reddit feed for posts matching profile interests.

        Steps:
            1. Wait for feed to load (shreddit-feed or posts)
            2. Extract all post titles
            3. Score each against profile.interests
            4. Return sorted by relevance

        Fallback: if new Reddit design not detected, try old.reddit.com selectors.
        """
        sel = self._get_selectors()
        items: list[ContentItem] = []

        # Wait for posts to appear
        try:
            await page.wait_for_selector(f"{sel['post_container']}, {sel['old_post']}", timeout=10000)
        except Exception:
            logger.debug("[Reddit] No posts found on page (maybe login wall?)")
            return items

        # Try new design selectors first
        post_elements = page.locator(sel["post_container"])
        post_count = await post_elements.count()

        if post_count == 0:
            # Fallback to old Reddit
            post_elements = page.locator(sel["old_post"])
            post_count = await post_elements.count()
            title_sel = sel["old_title"]
            link_sel = sel["old_title"]
            is_old = True
        else:
            title_sel = sel["post_title"]
            link_sel = sel["post_link"]
            is_old = False

        # Extract titles from visible posts
        for i in range(min(post_count, 30)):  # top 30 posts
            post_el = post_elements.nth(i)

            # Get title text
            title_loc = post_el.locator(title_sel).first
            if await title_loc.count() == 0:
                continue

            title = (await title_loc.text_content() or "").strip()
            if not title or len(title) < 5:
                continue

            # Get post URL
            url = ""
            link_loc = post_el.locator(link_sel).first
            if await link_loc.count() > 0:
                href = await link_loc.get_attribute("href")
                if href:
                    url = f"https://www.reddit.com{href}" if href.startswith("/") else href

            # Score against profile interests
            matches = self.match_interests(title, profile.interests)
            if matches:
                best_kw, best_score = matches[0]
                items.append(ContentItem(
                    title=title,
                    url=url,
                    selector=f"{sel['post_container']}:nth-child({i + 1}) {title_sel}"
                    if not is_old
                    else f"{sel['old_post']}:nth-child({i + 1}) {sel['old_title']}",
                    relevance_score=best_score,
                    matched_keyword=best_kw,
                    element_index=i,
                    _meta={"is_old_reddit": is_old, "post_index": i},
                ))

        # Sort by relevance
        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items

    # ── Interact with a single post ────────────────────────────────────────

    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        """
        Click into a Reddit post and optionally upvote.

        Flow:
            1. Click the post title to open the detail page
            2. Wait for post content to load
            3. Scroll through the post body (simulated reading)
            4. Dice roll: upvote based on profile.like_probability
            5. Navigate back to the feed
        """
        sel = self._get_selectors()
        result = ActionResult()

        # Step 1: Click the post title
        if item.url:
            # Navigate directly — more reliable than clicking
            current_url = page.url
            await page.goto(item.url, wait_until="domcontentloaded", timeout=15000)
            result.clicked = True
        else:
            # Fallback: try clicking the selector
            clicked = await self.safe_click(page, item.selector, timeout=5000)
            if clicked:
                await asyncio.sleep(random.uniform(1.5, 3.0))
                result.clicked = True

        if not result.clicked:
            result.error = "Could not open post"
            return result

        # Step 2: Wait for post content
        try:
            await page.wait_for_selector(
                f"{sel['post_body']}, {sel['upvote_btn']}, h1",
                timeout=8000,
            )
        except Exception:
            pass  # Some posts may not have body text

        # Step 3: Simulated reading (scroll through post)
        reading_time = random.uniform(2.0, 6.0) * getattr(profile, "reading_multiplier", 1.0)
        scroll_style = getattr(profile, "scroll_style", "normal")

        # Scroll through the post
        scroll_amounts = {"fast": 300, "normal": 150, "slow": 60, "reader": 30}
        step = scroll_amounts.get(scroll_style, 150)
        elapsed = 0.0
        while elapsed < reading_time:
            await page.mouse.wheel(0, step + random.randint(-20, 50))
            await asyncio.sleep(random.uniform(0.3, 1.5))
            elapsed += 0.5 + random.uniform(0, 0.5)

        # Step 4: Dice roll — upvote?
        if random.random() < getattr(profile, "like_probability", 0.3):
            if await self.safe_click(page, sel["upvote_btn"], timeout=3000):
                result.liked = True
                logger.debug(f"[Reddit] Upvoted: {item.title[:60]}...")

        # Step 5: Optionally comment (very low probability)
        if random.random() < getattr(profile, "comment_probability", 0.05) * 0.5:
            cmt_input = page.locator(sel["comment_input"]).first
            if await cmt_input.count() > 0:
                try:
                    await cmt_input.click()
                    from core.human_behavior import type_like_human
                    comment_text = _generate_comment(item, profile)
                    await type_like_human(page, comment_text)
                    result.commented = True
                    logger.debug(f"[Reddit] Commented on: {item.title[:60]}...")
                except Exception:
                    pass

        # Step 6: Navigate back to feed
        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        await asyncio.sleep(random.uniform(1.0, 2.5))

        return result

    # ── Hook overrides ─────────────────────────────────────────────────────

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        """Navigate to Reddit front page or a relevant subreddit."""
        subreddit = _pick_subreddit(profile)
        url = f"https://www.reddit.com/{subreddit}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        logger.info(f"[Reddit] Browsing {subreddit} as {profile.display_name}")

    def should_engage(self, item: ContentItem, profile: UserProfile) -> bool:
        """Higher bar for Reddit — only engage with high-relevance matches."""
        base = getattr(profile, "like_probability", 0.3)
        # Must have at least 0.5 relevance OR beat the adjusted threshold
        if item.relevance_score < 0.5:
            return False
        adjusted = base + item.relevance_score * 0.4
        return random.random() < min(adjusted, 0.85)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _pick_subreddit(profile: UserProfile) -> str:
    """Map profile interests to a relevant subreddit for initial navigation."""
    interest_map: dict[str, str] = {
        # Tech
        "python":      "r/Python",       "rust":        "r/rust",
        "programming": "r/programming",   "ai":          "r/artificial",
        "open source": "r/opensource",    "startups":    "r/startups",
        "linux":       "r/linux",         "cybersecurity": "r/cybersecurity",
        # Food
        "recipe":      "r/recipes",       "baking":      "r/Baking",
        "coffee":      "r/Coffee",        "pasta":       "r/pasta",
        "sourdough":   "r/Sourdough",     "wine":        "r/wine",
        # Travel
        "travel":      "r/travel",        "hiking":      "r/hiking",
        "backpacking": "r/backpacking",   "japan":       "r/JapanTravel",
        "iceland":     "r/VisitingIceland",
        # Student
        "gre":         "r/GRE",           "college":     "r/college",
        "internship":  "r/internships",   "study":       "r/GetStudying",
        # Retiree
        "gardening":   "r/gardening",     "yoga":        "r/yoga",
        "classical":   "r/classicalmusic","bird":        "r/birding",
        # Teenager
        "fortnite":    "r/FortNiteBR",    "minecraft":   "r/Minecraft",
        "nba":         "r/nba",           "anime":       "r/anime",
        "gaming":      "r/gaming",        "valorant":    "r/VALORANT",
    }

    interests_lower = [kw.lower() for kw in profile.interests]
    for kw in interests_lower:
        for key, sub in interest_map.items():
            if key in kw or kw in key:
                return sub

    # Default: r/popular for broad browsing
    return "r/popular"


def _generate_comment(item: ContentItem, profile: UserProfile) -> str:
    """Generate a short, profile-appropriate comment."""
    emoji_map = {"none": "", "light": " :)", "moderate": " 👍", "heavy": " 😂🔥💯"}

    templates: dict[str, list[str]] = {
        "en": [
            "Interesting take on this!",
            "Thanks for sharing, really helpful.",
            "This is exactly what I was looking for.",
            "Great post, saved for later.",
            "Love this content, keep it up!",
        ],
    }
    lang = getattr(profile, "language", "en")
    emoji = emoji_map.get(getattr(profile, "emoji_usage", "light"), "")
    templates_list = templates.get(lang, templates["en"])
    comment = random.choice(templates_list)
    return comment + emoji
