"""
Platform handler base class — callback architecture for per-platform content interaction.

Each platform (Reddit, Amazon, YouTube, etc.) implements a PlatformHandler subclass.
The handler knows that platform's specific DOM structure (selectors, element hierarchy)
and uses the profile's interests + behavioral parameters to find and interact with
matching content.

Architecture:
    daily_farming.py  ──calls──>  get_handler("reddit").browse(page, profile, ctx)
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              find_content()       interact()           should_engage()
              (scan DOM for       (click/vote/         (profile behavior
               matching posts)     comment)             dice roll)

Callbacks:
    - on_content_found(item): called when a matching post/product is discovered
    - on_interact(item, action): called after each interaction (before/after hooks)
    - on_session_end(result): called when browse session completes
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from loguru import logger

if TYPE_CHECKING:
    from playwright.async_api import Page
    from config.profiles import UserProfile
    from core.context_manager import AccountContext


# ── Data types ──────────────────────────────────────────────────────────────


@dataclass
class ContentItem:
    """A piece of content found on a platform page that matches profile interests."""

    title: str                          # display title / product name
    url: str                            # link to the content
    selector: str                       # CSS selector to locate the element
    relevance_score: float              # 0.0 - 1.0, how well it matches interests
    matched_keyword: str                # which profile interest keyword matched
    element_index: int = 0              # position on page (0 = first match)

    # Internal: DOM reference info for the handler to re-locate
    _meta: dict = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result of interacting with a single ContentItem."""

    clicked: bool = False
    liked: bool = False
    commented: bool = False
    saved: bool = False
    error: str = ""


@dataclass
class BrowseResult:
    """Summary of a complete browse+interact session on one platform."""

    items_found: int = 0
    items_viewed: int = 0
    items_liked: int = 0
    items_commented: int = 0
    search_term_used: str = ""
    session_seconds: float = 0.0


# ── Callback type aliases ──────────────────────────────────────────────────

ContentCallback = Callable[["ContentItem"], None]
ActionResultCallback = Callable[["ContentItem", "ActionResult"], None]


# ── Abstract base handler ──────────────────────────────────────────────────


class PlatformHandler(ABC):
    """
    Abstract base for all platform-specific handlers.

    Subclass must implement:
        - find_content(page, profile) -> list[ContentItem]
        - interact(page, item, profile) -> ActionResult
        - _get_selectors() -> dict (platform-specific CSS selectors)

    Optional hooks (override to customize):
        - before_browse(page, profile)
        - after_browse(page, profile, result)
        - should_engage(item, profile) -> bool
    """

    # ── Abstract methods (MUST implement) ──────────────────────────────────

    @abstractmethod
    async def find_content(self, page: Page, profile: UserProfile) -> list[ContentItem]:
        """
        Scan the current page for content matching profile interests.

        Must be implemented per-platform because each site has different DOM:
        - Reddit: <shreddit-post> with title in <a slot="title">
        - Amazon: <div data-component-type="s-search-result"> with product title in <h2>
        - YouTube: <ytd-video-renderer> with title in <a id="video-title">
        - etc.

        Returns list of ContentItem sorted by relevance_score descending.
        """
        ...

    @abstractmethod
    async def interact(self, page: Page, item: ContentItem, profile: UserProfile) -> ActionResult:
        """
        Interact with a single piece of content.

        Platform-specific actions:
        - Reddit: click title to open post, optionally upvote
        - Amazon: click to view product details, optionally add to wishlist
        - YouTube: click to play video, optionally like
        """
        ...

    @abstractmethod
    def _get_selectors(self) -> dict[str, str]:
        """
        Return platform-specific CSS selectors.

        Expected keys vary by platform but commonly include:
            "content_container", "title", "link", "vote_up", "comment_input", "search_box"
        """
        ...

    # ── Login detection (override for platforms that require login) ────────

    def _get_login_detectors(self) -> dict[str, str]:
        """
        Return selectors for login detection.

        Keys:
            "login_wall":  selector that appears when NOT logged in (e.g. login form, "Sign in" button)
            "logged_in":   selector that appears when logged in (e.g. avatar, user menu, feed)
            "login_url":   URL of the login page

        Return empty dict if platform works anonymously (default).
        """
        return {}

    async def wait_for_login(self, page: Page, profile: UserProfile) -> bool:
        """
        Detect login wall, wait for manual login, then continue.

        When config.FORCE_LOGIN is True, ALL platforms pause for manual login.
        When False, only platforms with detected login walls pause.

        Detection strategies (tried in order):
            1. Specific selectors (_get_login_detectors): login_wall / logged_in
            2. URL change: navigate to login page, wait for URL to change away
            3. Any sign-in element disappearance

        Returns:
            True if logged in or skipped; False if timeout.
        """
        import asyncio

        from config.settings import FORCE_LOGIN, LOGIN_TIMEOUT_SECONDS, PLATFORMS

        detectors = self._get_login_detectors()
        login_wall = detectors.get("login_wall", "")
        logged_in_sel = detectors.get("logged_in", "")
        login_url = detectors.get("login_url", "")

        # Fallback: use the login URL from platform config
        if not login_url:
            # Try to infer platform key from handler class name
            for key, plat in PLATFORMS.items():
                handler_cls_name = self.__class__.__name__.lower()
                if key in handler_cls_name:
                    login_url = plat.login_url
                    break

        # ── Already logged in? ──
        if logged_in_sel:
            try:
                loc = page.locator(logged_in_sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=2000):
                    logger.info(f"[{self.__class__.__name__}] Already logged in")
                    return True
            except Exception:
                pass

        # ── No detectors → check FORCE_LOGIN ──
        if not detectors or not login_wall:
            if not FORCE_LOGIN:
                return True  # No detectors + not forced → skip
            # FORCE_LOGIN: treat as login-required even without detectors
            needs_login = True
        else:
            # Check if login wall is actually visible
            needs_login = False
            try:
                loc = page.locator(login_wall).first
                if await loc.count() > 0:
                    needs_login = True
            except Exception:
                pass

            if not needs_login and FORCE_LOGIN:
                # Login wall not visible but force mode on — ask anyway
                needs_login = True

        if not needs_login:
            return True

        # ── Wait for manual login ──
        logger.warning("=" * 60)
        logger.warning(f"[{self.__class__.__name__}] Login required!"
                       f"{' (FORCE_LOGIN mode)' if FORCE_LOGIN and not detectors else ''}")
        logger.warning(f"  Profile:  {profile.display_name}")
        logger.warning(f"  URL:      {login_url or page.url}")
        logger.warning("  >>> Please log in manually in the browser window. <<<")
        logger.warning("=" * 60)

        # Navigate to login page
        pre_login_url = page.url
        if login_url:
            try:
                await page.goto(login_url, wait_until="domcontentloaded", timeout=20000)
                pre_login_url = login_url
            except Exception:
                pass

        print(f"\n{'='*60}")
        print(f"  MANUAL LOGIN REQUIRED — {self.__class__.__name__}")
        print(f"  Profile: {profile.display_name}")
        print(f"  Please log in using the opened browser window...")
        print(f"{'='*60}\n", flush=True)

        # ── Poll for login completion ──
        timeout_seconds = LOGIN_TIMEOUT_SECONDS
        poll_interval = 3
        elapsed = 0

        while elapsed < timeout_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            # Strategy 1: specific logged_in selector
            if logged_in_sel:
                try:
                    loc = page.locator(logged_in_sel).first
                    if await loc.count() > 0 and await loc.is_visible(timeout=1000):
                        logger.success(f"[{self.__class__.__name__}] Login detected! Continuing...")
                        print(f"  ✓ Login detected! Resuming...\n", flush=True)
                        await asyncio.sleep(2.0)
                        return True
                except Exception:
                    pass

            # Strategy 2: login wall disappeared
            if login_wall:
                try:
                    loc = page.locator(login_wall).first
                    if await loc.count() == 0:
                        logger.success(f"[{self.__class__.__name__}] Login wall disappeared! Continuing...")
                        await asyncio.sleep(2.0)
                        return True
                except Exception:
                    pass

            # Strategy 3: URL changed away from login page (generic fallback)
            if login_url and login_url != page.url:
                current = page.url
                login_keywords = ("login", "signin", "sign_in", "sign-in", "auth")
                if not any(kw in current.lower() for kw in login_keywords):
                    logger.success(f"[{self.__class__.__name__}] Navigated away from login — continuing...")
                    print(f"  ✓ Login detected! Resuming...\n", flush=True)
                    await asyncio.sleep(2.0)
                    return True

            # Strategy 4: page content changed significantly (DOM growth)
            if not detectors and elapsed > 15:
                try:
                    body = page.locator("body")
                    text = await body.text_content() or ""
                    if len(text) > 500 and not any(
                        kw in text.lower()[:200]
                        for kw in ("sign in", "log in", "username", "password")
                    ):
                        logger.success(f"[{self.__class__.__name__}] Page content looks logged-in — continuing...")
                        print(f"  ✓ Login detected! Resuming...\n", flush=True)
                        await asyncio.sleep(2.0)
                        return True
                except Exception:
                    pass

            if elapsed % 30 == 0 and elapsed > 0:
                remaining = timeout_seconds - elapsed
                logger.info(f"[{self.__class__.__name__}] Waiting for login... "
                            f"({elapsed}s elapsed, {remaining}s remaining)")

        logger.warning(f"[{self.__class__.__name__}] Login timeout ({timeout_seconds}s) — continuing anyway")
        print(f"  ⚠ Login timeout — continuing anyway\n", flush=True)
        return False

    # ── Optional hooks (override to customize) ─────────────────────────────

    async def before_browse(self, page: Page, profile: UserProfile) -> None:
        """Called before find_content. Use for pre-navigation, cookie consent, etc."""
        pass

    async def after_browse(self, page: Page, profile: UserProfile, result: BrowseResult) -> None:
        """Called after all interactions complete. Use for cleanup, logging."""
        pass

    def should_engage(self, item: ContentItem, profile: UserProfile) -> bool:
        """
        Decide whether to interact with a matching content item.

        Default: random dice roll based on profile.like_probability.
        Override to add platform-specific logic (e.g., skip promoted posts).
        """
        threshold = getattr(profile, "like_probability", 0.3)
        # Higher relevance = higher chance
        adjusted = min(threshold + item.relevance_score * 0.3, 0.9)
        return random.random() < adjusted

    # ── Callbacks (set by caller) ──────────────────────────────────────────

    on_content_found: ContentCallback | None = None
    on_interact: ActionResultCallback | None = None

    # ── Main browse flow (orchestrates find → interact) ────────────────────

    async def browse(
        self,
        page: Page,
        profile: UserProfile,
        account_ctx: AccountContext,
        max_interactions: int = 5,
    ) -> BrowseResult:
        """
        Complete browse session: scan page → find matching content → interact.

        This is the main entry point called by daily_farming.py.
        """
        import time

        start = time.time()
        result = BrowseResult()

        # 1. Pre-browse hook
        await self.before_browse(page, profile)

        # 2. Find matching content
        items = await self.find_content(page, profile)
        result.items_found = len(items)

        if not items:
            logger.debug(f"[{self.__class__.__name__}] No matching content found")
            await self.after_browse(page, profile, result)
            result.session_seconds = time.time() - start
            return result

        logger.info(f"[{self.__class__.__name__}] Found {len(items)} matching items for {profile.display_name}")

        # 3. Interact with top matches
        interacted = 0
        for item in items[:max_interactions]:
            if not self.should_engage(item, profile):
                continue

            # Fire callback
            if self.on_content_found:
                self.on_content_found(item)

            action = await self.interact(page, item, profile)
            interacted += 1

            if action.clicked:
                result.items_viewed += 1
            if action.liked:
                result.items_liked += 1
            if action.commented:
                result.items_commented += 1

            # Fire callback
            if self.on_interact:
                self.on_interact(item, action)

            if account_ctx.can_perform("likes") and action.liked:
                account_ctx.record_action("likes")
            if account_ctx.can_perform("comments") and action.commented:
                account_ctx.record_action("comments")

        result.items_viewed = max(result.items_viewed, interacted)
        result.session_seconds = time.time() - start

        # 4. Post-browse hook
        await self.after_browse(page, profile, result)

        return result

    # ── Shared utilities (usable by all subclasses) ─────────────────────────

    @staticmethod
    def match_interests(text: str, interests: list[str]) -> list[tuple[str, float]]:
        """
        Score a piece of text against profile interests.

        Returns list of (keyword, score) for matches, sorted by score desc.
        Score: 1.0 = exact phrase match, 0.6 = all words match, 0.3 = partial match.
        """
        text_lower = text.lower()
        matches: list[tuple[str, float]] = []

        for kw in interests:
            kw_lower = kw.lower()
            if kw_lower in text_lower:
                # Exact phrase match
                matches.append((kw, 1.0))
            else:
                # Check word-by-word
                words = kw_lower.split()
                matched_words = sum(1 for w in words if w in text_lower)
                if matched_words == len(words) and len(words) > 1:
                    matches.append((kw, 0.6))
                elif matched_words >= 1 and len(words) > 1:
                    matches.append((kw, 0.3))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    @staticmethod
    async def safe_click(page: Page, selector: str, timeout: float = 3000) -> bool:
        """Try to click an element; return True on success."""
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0:
                await loc.scroll_into_view_if_needed(timeout=timeout)
                await loc.click(timeout=timeout)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    async def safe_get_text(page: Page, selector: str) -> str:
        """Get text content of an element; return '' on failure."""
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0:
                text = await loc.text_content()
                return (text or "").strip()
        except Exception:
            pass
        return ""


# ── Handler registry ────────────────────────────────────────────────────────

_HANDLERS: dict[str, type[PlatformHandler]] = {}


def register_handler(platform_key: str) -> Callable[[type[PlatformHandler]], type[PlatformHandler]]:
    """Decorator to register a PlatformHandler subclass for a platform key."""
    def decorator(cls: type[PlatformHandler]) -> type[PlatformHandler]:
        _HANDLERS[platform_key] = cls
        logger.debug(f"Registered handler: {cls.__name__} → {platform_key}")
        return cls
    return decorator


def get_handler(platform_key: str) -> PlatformHandler | None:
    """Get the handler for a platform, or None if not implemented."""
    cls = _HANDLERS.get(platform_key)
    if cls is None:
        return None
    return cls()


def list_handlers() -> dict[str, str]:
    """Return {platform_key: handler_class_name} for all registered handlers."""
    return {k: v.__name__ for k, v in _HANDLERS.items()}
