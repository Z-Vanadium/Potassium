"""
Browser context isolation manager.

Each social media account gets its own isolated Playwright BrowserContext
with independent:
- Cookies & localStorage (persistent storage state)
- Device fingerprint (UA, viewport, locale, timezone, WebGL)
- Stealth patches
- Rate limit tracking
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from config.profiles import UserProfile
from config.settings import (
    BROWSER_DEFAULTS,
    PROFILES_DIR,
    PROXY_SERVER,
    PROXY_BYPASS,
    PlatformConfig,
)
from core.fingerprint import Fingerprint
from core.human_behavior import init_mouse_tracker
from core.stealth import apply_stealth

if TYPE_CHECKING:
    from config.settings import PlatformName


# ── Account context wrapper ─────────────────────────────────────────────────


@dataclass
class ActionStats:
    """Per-session action counters (reset on each launch)."""

    posts: int = 0
    likes: int = 0
    comments: int = 0
    follows: int = 0
    last_action_time: float = 0.0


@dataclass
class AccountContext:
    """
    An isolated browsing session for one account.

    Owns its BrowserContext, fingerprint, profile, and rate-limiter.
    Lifecycle: create → use → close()
    """

    account_id: str
    platform: PlatformConfig
    profile: UserProfile
    fingerprint: Fingerprint
    context: BrowserContext

    # Internal
    _stats: ActionStats = field(default_factory=ActionStats)
    _created_at: float = field(default_factory=time.time)
    _closed: bool = False

    @property
    def storage_path(self) -> Path:
        """Path to the persistent storage state file."""
        return PROFILES_DIR / f"{self.account_id}_{self.platform.name}.json"

    @property
    def stats(self) -> ActionStats:
        return self._stats

    async def new_page(self) -> Page:
        """Create a new page within this isolated context."""
        page = await self.context.new_page()
        await init_mouse_tracker(page)
        return page

    def record_action(self, action_type: str) -> None:
        """Record an action for rate-limit tracking."""
        now = time.time()
        setattr(self._stats, action_type, getattr(self._stats, action_type) + 1)
        self._stats.last_action_time = now

    def can_perform(self, action_type: str) -> bool:
        """Check whether an action is within daily limits."""
        limit_key = f"daily_{action_type}_limit"
        limit = getattr(self.platform, limit_key, None)
        if limit is None:
            return True
        current = getattr(self._stats, action_type, 0)
        return current < limit

    async def save_storage(self) -> None:
        """Persist cookies + localStorage to disk."""
        try:
            state = await self.context.storage_state()
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            logger.info(f"Saved storage state → {self.storage_path}")
        except Exception as e:
            logger.warning(f"Could not save storage state: {e}")

    async def close(self) -> None:
        """Close the browser context and persist state. Idempotent."""
        if self._closed:
            return
        self._closed = True
        await self.save_storage()
        elapsed = time.time() - self._created_at
        logger.info(
            f"[{self.account_id}] Session ended ({elapsed:.0f}s). "
            f"Likes: {self._stats.likes}, Comments: {self._stats.comments}, "
            f"Follows: {self._stats.follows}"
        )
        try:
            await self.context.close()
        except Exception as e:
            logger.debug(f"Context already closed: {e}")


# ── Context factory ─────────────────────────────────────────────────────────


class ContextManager:
    """
    Factory for creating isolated BrowserContexts per account.

    Usage:
        async with ContextManager() as manager:
            ctx = await manager.create_context(
                account_id="tech_zhihu_01",
                platform="zhihu",
                profile=UserProfile(...),
            )
            page = await ctx.new_page()
            await page.goto("https://zhihu.com")
            ...
            await ctx.close()
    """

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._active_contexts: dict[str, AccountContext] = {}
        self._pending_sec_ch_headers: dict[str, str] = {}

    async def __aenter__(self) -> ContextManager:
        self._playwright = await async_playwright().start()
        self._browser = await self._launch_browser()
        return self

    async def __aexit__(self, *args: object) -> None:
        # Close all active contexts
        for ctx in list(self._active_contexts.values()):
            await ctx.close()
        self._active_contexts.clear()

        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.debug(f"Browser already closed: {e}")
        if self._playwright:
            await self._playwright.stop()

    async def _launch_browser(self) -> Browser:
        """Launch Chromium with stealth-friendly args."""
        assert self._playwright is not None, "Playwright not started"

        launch_options: dict[str, object] = {
            "headless": BROWSER_DEFAULTS.headless,
            "args": list(BROWSER_DEFAULTS.launch_args),
        }

        if PROXY_SERVER:
            launch_options["proxy"] = {
                "server": PROXY_SERVER,
                "bypass": PROXY_BYPASS,
            }

        browser = await self._playwright.chromium.launch(**launch_options)  # pyright: ignore[reportArgumentType]
        logger.info("Browser launched")
        return browser

    async def create_context(
        self,
        account_id: str,
        platform: PlatformName,
        profile: UserProfile,
    ) -> AccountContext:
        """
        Create an isolated BrowserContext for one account.

        Args:
            account_id: Unique ID for this account (e.g. "tech_zhihu_01").
            platform: Target platform key ("zhihu", "weibo", etc.).
            profile: UserProfile defining fingerprint & behavior.

        Returns:
            A ready-to-use AccountContext.
        """
        from config.settings import PLATFORMS as _PLATFORMS
        platform_config = _PLATFORMS[platform]
        fingerprint = Fingerprint.from_profile(profile)

        # Build context options
        context_options = self._build_context_options(fingerprint, account_id, platform)

        logger.info(
            f"Creating context [{account_id}] on {platform_config.display_name} "
            f"as {profile.display_name}"
        )
        assert self._browser is not None
        context = await self._browser.new_context(**context_options)  # pyright: ignore[reportArgumentType]

        # Apply stealth patches
        await apply_stealth(context)

        # Create wrapper
        acct_ctx = AccountContext(
            account_id=account_id,
            platform=platform_config,
            profile=profile,
            fingerprint=fingerprint,
            context=context,
        )

        self._active_contexts[account_id] = acct_ctx
        return acct_ctx

    def _build_context_options(
        self,
        fp: Fingerprint,
        account_id: str,
        platform: PlatformName,
    ) -> dict[str, object]:
        """Build Playwright BrowserContext options from a fingerprint."""
        storage_path = PROFILES_DIR / f"{account_id}_{platform}.json"

        options: dict[str, object] = {
            "user_agent": fp.user_agent,
            "viewport": fp.viewport,
            "locale": fp.locale,
            "timezone_id": fp.timezone_id,
            "color_scheme": "light",
            "device_scale_factor": fp.device_scale_factor,
            "is_mobile": fp.is_mobile,
            "has_touch": fp.has_touch,
            "screen": fp.screen,
            "bypass_csp": False,
            "extra_http_headers": {
                "Accept-Language": fp.accept_language,
            },
        }

        # Restore previous session if exists
        if storage_path.exists():
            try:
                saved_state = json.loads(storage_path.read_text(encoding="utf-8"))
                options["storage_state"] = saved_state
                logger.info(f"Restored session from {storage_path}")
            except (json.JSONDecodeError, KeyError):
                logger.warning(f"Corrupted storage state, starting fresh: {storage_path}")

        # Proxy (if configured)
        if PROXY_SERVER:
            options["proxy"] = {
                "server": PROXY_SERVER,
                "bypass": PROXY_BYPASS,
            }

        # CDP override for platform-specific fingerprint patches
        options["geolocation"] = (
            {"latitude": fp.latitude, "longitude": fp.longitude}
            if fp.latitude is not None
            else None
        )

        # Inject Sec-CH-UA headers via CDP after context creation
        self._pending_sec_ch_headers = {
            "Sec-CH-UA": fp.sec_ch_ua,
            "Sec-CH-UA-Mobile": fp.sec_ch_ua_mobile,
            "Sec-CH-UA-Platform": fp.sec_ch_ua_platform,
        }

        return options

    async def get_context(self, account_id: str) -> AccountContext | None:
        """Get an active context by account ID."""
        return self._active_contexts.get(account_id)
