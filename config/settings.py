"""
Project-wide configuration for the social media account farming framework.

All rate limits, platform definitions, and global behavior parameters
are centralized here.

Platforms: 17 international platforms across social, e-commerce, travel, and streaming.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ── Project root ────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT_DIR / "profiles"
ACCOUNTS_DIR = ROOT_DIR / "accounts"
DATA_DIR = ROOT_DIR / "data"

# Ensure directories exist
for _dir in (PROFILES_DIR, ACCOUNTS_DIR, DATA_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# ── Platform definitions ────────────────────────────────────────────────────

PlatformName = Literal[
    # Social / Content
    "pinterest", "tumblr", "reddit", "quora", "twitch",
    "twitter", "linkedin",
    # E-commerce
    "amazon", "ebay", "aliexpress", "walmart", "shopee",
    # Travel
    "booking", "expedia", "agoda",
    # Streaming
    "spotify", "youtube",
]


@dataclass(frozen=True)
class PlatformConfig:
    name: PlatformName
    display_name: str
    base_url: str
    login_url: str
    locale: str = "en-US"
    # Actions that count toward daily limits
    daily_post_limit: int = 5
    daily_like_limit: int = 20
    daily_comment_limit: int = 10
    daily_follow_limit: int = 5
    # Cooldown between actions (seconds)
    action_cooldown_min: float = 60.0
    action_cooldown_max: float = 180.0


PLATFORMS: dict[PlatformName, PlatformConfig] = {
    # ── Social / Content ──
    "pinterest":    PlatformConfig("pinterest",    "Pinterest",    "https://www.pinterest.com",    "https://www.pinterest.com/login",
                                   daily_like_limit=40, daily_comment_limit=5, daily_follow_limit=15,
                                   action_cooldown_min=15.0, action_cooldown_max=45.0),
    "tumblr":       PlatformConfig("tumblr",       "Tumblr",       "https://www.tumblr.com",       "https://www.tumblr.com/login",
                                   daily_like_limit=35, daily_comment_limit=8, daily_follow_limit=10),
    "twitch":       PlatformConfig("twitch",       "Twitch",       "https://www.twitch.tv",        "https://www.twitch.tv/login",
                                   daily_like_limit=30, daily_comment_limit=8, daily_follow_limit=10,
                                   action_cooldown_min=30.0, action_cooldown_max=90.0),
    "reddit":       PlatformConfig("reddit",       "Reddit",       "https://www.reddit.com",       "https://www.reddit.com/login",
                                   daily_like_limit=30, daily_comment_limit=8, daily_follow_limit=5),
    "quora":        PlatformConfig("quora",        "Quora",        "https://www.quora.com",        "https://www.quora.com/login",
                                   daily_like_limit=20, daily_comment_limit=5, daily_follow_limit=5),
    "twitter":      PlatformConfig("twitter",      "X / Twitter",  "https://x.com",                "https://x.com/i/flow/login"),
    "linkedin":     PlatformConfig("linkedin",     "LinkedIn",     "https://www.linkedin.com",     "https://www.linkedin.com/login"),

    # ── E-commerce ──
    "amazon":       PlatformConfig("amazon",       "Amazon",       "https://www.amazon.com",       "https://www.amazon.com/ap/signin",
                                   daily_like_limit=50, daily_comment_limit=4, daily_follow_limit=15,
                                   action_cooldown_min=15.0, action_cooldown_max=45.0),
    "ebay":         PlatformConfig("ebay",         "eBay",         "https://www.ebay.com",         "https://signin.ebay.com",
                                   daily_like_limit=40, daily_comment_limit=3, daily_follow_limit=10,
                                   action_cooldown_min=20.0, action_cooldown_max=60.0),
    "aliexpress":   PlatformConfig("aliexpress",   "AliExpress",   "https://www.aliexpress.com",   "https://login.aliexpress.com",
                                   daily_like_limit=50, daily_comment_limit=3, daily_follow_limit=15,
                                   action_cooldown_min=12.0, action_cooldown_max=40.0),
    "walmart":      PlatformConfig("walmart",      "Walmart",      "https://www.walmart.com",      "https://www.walmart.com/account/login",
                                   daily_like_limit=40, daily_comment_limit=3, daily_follow_limit=10,
                                   action_cooldown_min=20.0, action_cooldown_max=60.0),
    "shopee":       PlatformConfig("shopee",       "Shopee",       "https://shopee.sg",            "https://shopee.sg/buyer/login",
                                   daily_like_limit=45, daily_comment_limit=3, daily_follow_limit=10,
                                   action_cooldown_min=12.0, action_cooldown_max=40.0),

    # ── Travel ──
    "booking":      PlatformConfig("booking",      "Booking.com",  "https://www.booking.com",      "https://account.booking.com/sign-in",
                                   daily_like_limit=30, daily_comment_limit=3, daily_follow_limit=5,
                                   action_cooldown_min=20.0, action_cooldown_max=90.0),
    "expedia":      PlatformConfig("expedia",      "Expedia",      "https://www.expedia.com",      "https://www.expedia.com/user/signin",
                                   daily_like_limit=30, daily_comment_limit=3, daily_follow_limit=5,
                                   action_cooldown_min=20.0, action_cooldown_max=90.0),
    "agoda":        PlatformConfig("agoda",        "Agoda",        "https://www.agoda.com",        "https://www.agoda.com/account/signin.html",
                                   daily_like_limit=25, daily_comment_limit=2, daily_follow_limit=5,
                                   action_cooldown_min=25.0, action_cooldown_max=120.0),

    # ── Streaming ──
    "spotify":      PlatformConfig("spotify",      "Spotify",      "https://open.spotify.com",     "https://accounts.spotify.com/login",
                                   daily_post_limit=3, daily_like_limit=50, daily_comment_limit=0, daily_follow_limit=10,
                                   action_cooldown_min=10.0, action_cooldown_max=30.0),
    "youtube":      PlatformConfig("youtube",      "YouTube",      "https://www.youtube.com",      "https://www.youtube.com/account",
                                   daily_post_limit=2, daily_like_limit=40, daily_comment_limit=8, daily_follow_limit=5,
                                   action_cooldown_min=30.0, action_cooldown_max=120.0),
}


# ── Platform categories (for search term selection) ─────────────────────────

def platform_category(name: PlatformName) -> str:
    """Return the category of a platform: 'social' | 'ecommerce' | 'travel' | 'streaming'."""
    _map: dict[str, str] = {
        "pinterest": "social", "tumblr": "social", "twitch": "streaming",
        "reddit": "social", "quora": "social", "twitter": "social",
        "linkedin": "social",
        "amazon": "ecommerce", "ebay": "ecommerce", "aliexpress": "ecommerce",
        "walmart": "ecommerce", "shopee": "ecommerce",
        "booking": "travel", "expedia": "travel", "agoda": "travel",
        "spotify": "streaming", "youtube": "streaming",
    }
    return _map.get(name, "social")


# ── Browser defaults ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BrowserDefaults:
    """Default browser launch arguments shared across all accounts."""

    headless: bool = False  # headful for stealth (headless=too detectable)
    viewport_width: int = 1280
    viewport_height: int = 720

    launch_args: list[str] = field(default_factory=lambda: [
        "--no-sandbox",
        "--disable-infobars",
        "--disable-dev-shm-usage",
        "--disable-setuid-sandbox",
        "--disable-accelerated-2d-canvas",
        "--disable-gpu",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
    ])

    # Timeout defaults (milliseconds)
    default_timeout: int = 30_000
    navigation_timeout: int = 60_000


BROWSER_DEFAULTS = BrowserDefaults()


# ── Action rate limits (global) ─────────────────────────────────────────────

GLOBAL_DAILY_ACTION_CAP: int = 500

ACTIVE_HOURS_START: int = 8
ACTIVE_HOURS_END: int = 23


# ── Proxy support (optional) ────────────────────────────────────────────────

PROXY_SERVER: str | None = None   # e.g. "http://user:pass@host:port"
PROXY_BYPASS: str = "<local>"


# ── Logging ─────────────────────────────────────────────────────────────────

LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
