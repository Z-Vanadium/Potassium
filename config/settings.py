"""
Project-wide configuration for the social media account farming framework.

All rate limits, platform definitions, and global behavior parameters
are centralized here.
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
    "weibo", "xiaohongshu", "douyin", "bilibili", "zhihu",
    "twitter", "linkedin",
]


@dataclass(frozen=True)
class PlatformConfig:
    name: PlatformName
    display_name: str
    base_url: str
    login_url: str
    locale: str = "zh-CN"
    # Actions that count toward daily limits
    daily_post_limit: int = 5
    daily_like_limit: int = 20
    daily_comment_limit: int = 10
    daily_follow_limit: int = 5
    # Cooldown between actions (seconds)
    action_cooldown_min: float = 60.0
    action_cooldown_max: float = 180.0


PLATFORMS: dict[PlatformName, PlatformConfig] = {
    "weibo":        PlatformConfig("weibo",        "微博",         "https://weibo.com",        "https://weibo.com/login.php"),
    "xiaohongshu":  PlatformConfig("xiaohongshu",  "小红书",        "https://www.xiaohongshu.com", "https://www.xiaohongshu.com"),
    "douyin":       PlatformConfig("douyin",       "抖音",         "https://www.douyin.com",   "https://www.douyin.com"),
    "bilibili":     PlatformConfig("bilibili",     "B站",          "https://www.bilibili.com", "https://passport.bilibili.com/login"),
    "zhihu":        PlatformConfig("zhihu",        "知乎",         "https://www.zhihu.com",    "https://www.zhihu.com/signin"),
    "twitter":      PlatformConfig("twitter",      "X/Twitter",    "https://x.com",             "https://x.com/i/flow/login", locale="en-US"),
    "linkedin":     PlatformConfig("linkedin",     "LinkedIn",     "https://www.linkedin.com", "https://www.linkedin.com/login", locale="en-US"),
}


# ── Browser defaults ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BrowserDefaults:
    """Default browser launch arguments shared across all accounts."""

    headless: bool = False  # headful for stealth (headless=too detectable)
    viewport_width: int = 1280
    viewport_height: int = 720

    # Stealth launch args — must NOT include "--disable-blink-features=AutomationControlled"
    # because we handle that via stealth.py CDP patches instead.
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

# Maximum actions per day across ALL accounts
GLOBAL_DAILY_ACTION_CAP: int = 200

# Active hours window (0-23) – actions only within this range
ACTIVE_HOURS_START: int = 8
ACTIVE_HOURS_END: int = 23


# ── Proxy support (optional) ────────────────────────────────────────────────

PROXY_SERVER: str | None = None   # e.g. "http://user:pass@host:port"
PROXY_BYPASS: str = "<local>"


# ── Logging ─────────────────────────────────────────────────────────────────

LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
