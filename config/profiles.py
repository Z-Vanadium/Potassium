"""
Pre-defined user profile portraits (用户画像).

Each profile defines a distinct persona with its own device fingerprint,
browsing interests, and behavioral parameters. Profiles are loaded per-account
and applied to isolated BrowserContexts.
"""

from dataclasses import dataclass, field
from typing import Literal


# ── Profile definition ──────────────────────────────────────────────────────

@dataclass
class UserProfile:
    """A complete user persona configuration."""

    # ── Identity ──
    profile_id: str          # unique identifier
    display_name: str        # human-readable label

    # ── Device fingerprint ──
    user_agent: str          # browser UA string
    viewport: tuple[int, int]  # (width, height)
    locale: str              # e.g. "zh-CN", "en-US"
    timezone: str            # IANA timezone, e.g. "Asia/Shanghai"
    webgl_vendor: str        # GPU vendor string
    webgl_renderer: str      # GPU renderer string
    platform: str            # navigator.platform, e.g. "Win32", "MacIntel"
    hardware_concurrency: int  # logical CPU cores
    device_memory: int        # GB
    color_depth: int = 24
    screen_width: int = 1920
    screen_height: int = 1080
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False

    # ── Browsing behavior ──
    interests: list[str] = field(default_factory=list)  # content keywords
    suspend_keywords: list[str] = field(default_factory=list)  # avoid
    typing_speed_min: int = 50   # ms per character
    typing_speed_max: int = 150
    scroll_style: Literal["fast", "normal", "slow", "reader"] = "normal"
    reading_multiplier: float = 1.0  # 1.0 = normal reading speed

    # ── Activity pattern ──
    session_duration_min: int = 5   # minutes
    session_duration_max: int = 20
    sessions_per_day_min: int = 1
    sessions_per_day_max: int = 3

    # ── Social behavior ──
    like_probability: float = 0.3      # likelihood of liking viewed content
    comment_probability: float = 0.05
    follow_probability: float = 0.02
    repost_probability: float = 0.08
    post_frequency: Literal["daily", "weekly", "rare"] = "weekly"

    # ── Language / tone ──
    language: Literal["zh", "en"] = "zh"
    emoji_usage: Literal["none", "light", "moderate", "heavy"] = "light"


# ── Pre-built profiles ──────────────────────────────────────────────────────

TECH_ENTHUSIAST = UserProfile(
    profile_id="tech_enthusiast",
    display_name="Tech Enthusiast",
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    viewport=(1366, 768),
    locale="en-US",
    timezone="America/Los_Angeles",
    webgl_vendor="Google Inc. (NVIDIA)",
    webgl_renderer="ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
    platform="Win32",
    hardware_concurrency=12,
    device_memory=8,
    interests=[
        "AI", "LLM", "open source", "programming", "Python",
        "Rust", "semiconductors", "cloud computing", "robotics",
        "startups", "venture capital", "cybersecurity",
        "TypeScript", "Linux", "GPU", "machine learning",
        "developer tools", "API design", "Kubernetes", "database",
        "compiler", "embedded systems", "neovim", "homelab",
    ],
    suspend_keywords=["celebrity", "gossip", "reality TV", "crypto trading"],
    typing_speed_min=40,
    typing_speed_max=80,       # fast typer (developer)
    scroll_style="fast",
    reading_multiplier=0.6,     # skims
    session_duration_min=10,
    session_duration_max=30,
    sessions_per_day_min=2,
    sessions_per_day_max=3,
    like_probability=0.25,
    comment_probability=0.08,   # likes to comment on tech
    follow_probability=0.03,
    repost_probability=0.10,
    post_frequency="weekly",
    language="en",
    emoji_usage="light",
)

FOOD_BLOGGER = UserProfile(
    profile_id="food_blogger",
    display_name="Food Blogger",
    user_agent=(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.4 Mobile/15E148 Safari/604.1"
    ),
    viewport=(390, 844),
    locale="en-US",
    timezone="America/New_York",
    webgl_vendor="Apple Inc.",
    webgl_renderer="Apple GPU",
    platform="iPhone",
    hardware_concurrency=6,
    device_memory=4,
    is_mobile=True,
    has_touch=True,
    device_scale_factor=3.0,
    screen_width=390,
    screen_height=844,
    interests=[
        "recipes", "baking", "coffee", "food photography",
        "Italian cuisine", "Japanese ramen", "sourdough bread",
        "farmers market", "wine tasting", "pastry",
        "vegan cooking", "BBQ", "meal prep", "chocolate",
        "street food", "brunch", "fermentation", "cocktails",
        "cheese making", "herb garden",
    ],
    suspend_keywords=["politics", "military", "coding"],
    typing_speed_min=80,
    typing_speed_max=180,       # slower on mobile
    scroll_style="slow",
    reading_multiplier=1.3,      # reads carefully
    session_duration_min=5,
    session_duration_max=15,
    sessions_per_day_min=2,
    sessions_per_day_max=2,
    like_probability=0.45,       # likes a lot
    comment_probability=0.12,
    follow_probability=0.05,
    repost_probability=0.03,
    post_frequency="daily",
    language="en",
    emoji_usage="heavy",
)

TRAVELER = UserProfile(
    profile_id="traveler",
    display_name="Travel Enthusiast",
    user_agent=(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    viewport=(1440, 900),
    locale="en-US",
    timezone="America/Los_Angeles",
    webgl_vendor="Apple Inc.",
    webgl_renderer="Apple M3",
    platform="MacIntel",
    hardware_concurrency=10,
    device_memory=16,
    screen_width=2560,
    screen_height=1600,
    device_scale_factor=2.0,
    interests=[
        "travel photography", "hiking trails", "national parks",
        "Iceland", "Japan", "Patagonia", "Santorini",
        "backpacking", "digital nomad", "boutique hotels",
        "New Zealand", "Peru", "Morocco", "Croatia",
        "scuba diving", "surfing", "wildlife safari", "road trip",
        "eco lodge", "UNESCO heritage",
    ],
    suspend_keywords=["gaming", "esports", "crypto"],
    typing_speed_min=60,
    typing_speed_max=120,
    scroll_style="normal",
    reading_multiplier=1.0,
    session_duration_min=8,
    session_duration_max=25,
    sessions_per_day_min=1,
    sessions_per_day_max=2,
    like_probability=0.35,
    comment_probability=0.06,
    follow_probability=0.04,
    repost_probability=0.05,
    post_frequency="weekly",
    language="en",
    emoji_usage="moderate",
)

COLLEGE_STUDENT = UserProfile(
    profile_id="college_student",
    display_name="College Student",
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
    ),
    viewport=(1536, 864),
    locale="en-US",
    timezone="America/Chicago",
    webgl_vendor="Google Inc. (AMD)",
    webgl_renderer="ANGLE (AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0)",
    platform="Win32",
    hardware_concurrency=8,
    device_memory=8,
    interests=[
        "GRE prep", "internships", "study abroad", "dorm hacks",
        "college football", "student discounts", "campus life",
        "Spotify playlists", "budget meal prep", "room decor",
        "TOEFL", "scholarships", "part time job", "freshman tips",
        "college application", "mental health", "fitness gym",
        "fashion affordable", "dating advice",
    ],
    suspend_keywords=["real estate", "investing", "parenting"],
    typing_speed_min=50,
    typing_speed_max=100,
    scroll_style="fast",
    reading_multiplier=0.5,     # very fast skimmer
    session_duration_min=15,
    session_duration_max=60,     # student has lots of free time
    sessions_per_day_min=3,
    sessions_per_day_max=5,
    like_probability=0.40,
    comment_probability=0.10,
    follow_probability=0.06,
    repost_probability=0.12,
    post_frequency="daily",
    language="en",
    emoji_usage="heavy",
)


# ── Registry ─────────────────────────────────────────────────────────────────

RETIREE = UserProfile(
    profile_id="retiree",
    display_name="Retiree",
    user_agent=(
        "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.5 Mobile/15E148 Safari/604.1"
    ),
    viewport=(1024, 768),
    locale="en-US",
    timezone="America/New_York",
    webgl_vendor="Apple Inc.",
    webgl_renderer="Apple A12Z GPU",
    platform="iPad",
    hardware_concurrency=4,
    device_memory=3,
    is_mobile=True,
    has_touch=True,
    device_scale_factor=2.0,
    screen_width=1024,
    screen_height=768,
    color_depth=24,
    interests=[
        "gardening", "yoga for seniors", "wellness", "bird watching",
        "classical music", "bridge card game", "cruise vacations",
        "grandchildren", "home cooking", "meditation",
        "watercolor painting", "genealogy",
        "knitting", "antique collecting", "book club",
        "butterfly garden", "walking trails", "volunteer work",
        "piano", "tea culture", "pottery",
        "wildlife photography", "crossword puzzles",
    ],
    suspend_keywords=["gaming", "esports", "anime", "hip hop"],
    typing_speed_min=120,       # slow typer
    typing_speed_max=300,
    scroll_style="reader",       # reads carefully
    reading_multiplier=1.8,      # reads slowly, re-reads
    session_duration_min=20,
    session_duration_max=90,     # plenty of free time
    sessions_per_day_min=1,
    sessions_per_day_max=2,
    like_probability=0.15,       # rarely likes
    comment_probability=0.02,    # almost never comments
    follow_probability=0.01,
    repost_probability=0.25,     # shares articles with family
    post_frequency="rare",
    language="en",
    emoji_usage="none",
)

TEENAGER = UserProfile(
    profile_id="teenager",
    display_name="Teenager",
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    viewport=(1366, 768),
    locale="en-US",
    timezone="America/Chicago",
    webgl_vendor="Google Inc. (AMD)",
    webgl_renderer="ANGLE (AMD Radeon RX 6500 XT Direct3D11 vs_5_0 ps_5_0)",
    platform="Win32",
    hardware_concurrency=6,
    device_memory=8,
    screen_width=1366,
    screen_height=768,
    device_scale_factor=1.0,
    is_mobile=False,
    has_touch=False,
    color_depth=24,
    interests=[
        "Fortnite", "Minecraft", "Valorant", "Apex Legends",
        "Naruto", "Demon Slayer", "Attack on Titan",
        "NBA", "LeBron James", "Stephen Curry", "March Madness",
        "Twitch streamers", "Discord", "memes", "skateboarding",
        "Roblox", "Among Us", "One Piece", "Jujutsu Kaisen",
        "Call of Duty", "Genshin Impact", "TikTok trends",
        "sneakers", "graphic tees", "energy drinks",
    ],
    suspend_keywords=["wellness", "real estate", "dating apps", "stocks", "parenting"],
    typing_speed_min=30,         # fast typer (gamer reflexes)
    typing_speed_max=80,
    scroll_style="fast",          # scrolls fast
    reading_multiplier=0.4,       # skims quickly
    session_duration_min=30,
    session_duration_max=120,     # hours after school
    sessions_per_day_min=2,
    sessions_per_day_max=4,
    like_probability=0.55,        # likes everything cool
    comment_probability=0.12,     # active in comments
    follow_probability=0.08,      # follows creators
    repost_probability=0.05,
    post_frequency="rare",        # mostly consumes
    language="en",
    emoji_usage="heavy",          # 💀🔥💯👊🎮
)


# ── Registry ─────────────────────────────────────────────────────────────────

PROFILE_REGISTRY: dict[str, UserProfile] = {
    "tech_enthusiast": TECH_ENTHUSIAST,
    "food_blogger":    FOOD_BLOGGER,
    "traveler":        TRAVELER,
    "college_student": COLLEGE_STUDENT,
    "retiree":         RETIREE,
    "teenager":        TEENAGER,
}
