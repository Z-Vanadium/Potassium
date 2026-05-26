"""
Daily automated account farming — 6 profiles × 17 international platforms = 102 unique personas.

Usage:
    uv run python daily_farming.py              # Full: all 102 combos (~30-60 min)
    uv run python daily_farming.py --quick      # Quick: 1 profile per platform (17 combos, ~8-10 min)

Evidence:
    - Screenshots saved to evidence/screenshots/{profile}/{platform}/
    - Summary JSON written to evidence/summary.json
    - Per-account session state persisted in profiles/

Principle:
    Even without login, platforms track browsing behavior via cookies + IP.
    Each search, page view, and scroll session builds an anonymous user profile.
    Over repeated sessions (with persistent cookies), platforms form complete
    interest tags and behavioral profiles for each "anonymous user".
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote

from loguru import logger

from config.profiles import (
    TECH_ENTHUSIAST, FOOD_BLOGGER, TRAVELER,
    COLLEGE_STUDENT, RETIREE, TEENAGER,
    UserProfile, PROFILE_REGISTRY,
)
from config.settings import PlatformName, PLATFORMS, platform_category
from core.context_manager import ContextManager
from core.human_behavior import think_pause, scroll_like_human
from platforms import get_handler, BrowseResult

# ── Evidence output ──────────────────────────────────────────────────────────

EVIDENCE_DIR = Path(__file__).parent / "evidence"
SCREENSHOT_DIR = EVIDENCE_DIR / "screenshots"
SUMMARY_FILE = EVIDENCE_DIR / "summary.json"

# ── Per-profile search terms (by platform category) ─────────────────────────

PROFILE_SEARCHES: dict[str, dict[str, list[str]]] = {
    "tech_enthusiast": {
        "social": [
            "AI development", "open source projects", "Rust programming",
            "semiconductor news", "Linux kernel", "machine learning tutorial",
            "startup funding", "cybersecurity threats", "cloud architecture",
            "TypeScript vs Rust", "GPU benchmarks", "LLM fine-tuning",
            "developer productivity", "code review best practices",
        ],
        "ecommerce": [
            "mechanical keyboard", "ultrawide monitor", "Raspberry Pi kit",
            "programming books", "standing desk", "noise cancelling headphones",
            "USB-C hub", "NVMe SSD", "ergonomic mouse", "webcam 4K",
            "soldering iron kit", "network switch", "laptop stand",
        ],
        "travel": [
            "Silicon Valley hotel", "Tokyo tech district",
            "Berlin startup scene", "Seoul electronics market",
            "Shenzhen Huaqiangbei", "Bangalore tech park",
        ],
        "streaming": [
            "coding tutorial", "tech podcast", "Linux setup guide",
            "AI explained", "system design interview", "Rust crash course",
            "Neovim setup", "homelab tour", "Kubernetes tutorial",
        ],
    },
    "food_blogger": {
        "social": [
            "sourdough recipe", "coffee brewing", "Italian pasta",
            "food photography tips", "French pastry", "ramen recipe",
            "wine pairing guide", "farmers market haul", "sushi making",
            "chocolate dessert", "Mediterranean diet", "street food tour",
            "homemade pizza", "fermentation guide",
        ],
        "ecommerce": [
            "espresso machine", "dutch oven", "ceramic dinnerware",
            "chef knife set", "pasta maker", "coffee grinder",
            "stand mixer", "cast iron skillet", "baking stone",
            "mortar and pestle", "sous vide cooker", "food scale",
            "mason jars", "tea kettle",
        ],
        "travel": [
            "Barcelona food tour", "Tokyo street food", "Paris patisserie",
            "Bangkok night market", "Rome trattoria", "Mexico City tacos",
        ],
        "streaming": [
            "cooking show", "baking tutorial", "wine tasting",
            "restaurant review", "street food documentary",
            "coffee brewing guide", "MasterChef highlights",
            "pastry chef vlog", "kitchen organization",
        ],
    },
    "traveler": {
        "social": [
            "backpacking tips", "national parks", "hidden gem destinations",
            "solo travel", "van life", "budget travel hacks",
            "UNESCO world heritage", "scuba diving spots",
            "mountain trekking", "safari guide", "island hopping",
            "road trip ideas", "train travel Europe", "eco tourism",
        ],
        "ecommerce": [
            "hiking backpack", "travel adapter", "packing cubes",
            "GoPro accessories", "sleeping bag", "hiking boots",
            "portable charger", "travel towel", "water filter",
            "headlamp", "compression socks", "luggage scale",
            "travel pillow", "dry bag",
        ],
        "travel": [
            "Bali resort", "Swiss Alps hotel", "Kyoto ryokan",
            "Patagonia trek", "Maldives overwater villa", "Machu Picchu tour",
            "Santorini sunset", "New Zealand campervan",
        ],
        "streaming": [
            "travel documentary", "drone footage", "hiking guide",
            "van life vlog", "wildlife documentary", "survival skills",
            "cultural travel show", "adventure film", "nature soundscape",
        ],
    },
    "college_student": {
        "social": [
            "GRE study tips", "internship advice", "dorm room setup",
            "college life vlog", "TOEFL preparation", "student loans",
            "part time job ideas", "study abroad experience",
            "college application essay", "scholarship opportunities",
            "freshman orientation", "college meal plan",
        ],
        "ecommerce": [
            "desk lamp", "noise cancelling headphones", "backpack",
            "planner notebook", "laptop sleeve", "water bottle",
            "power bank", "desk organizer", "sticky notes bulk",
            "highlighters set", "whiteboard calendar", "bed risers",
            "shower caddy", "lap desk",
        ],
        "travel": [
            "student flight deals", "hostel Europe", "spring break ideas",
            "study abroad programs", "cheap weekend trips",
        ],
        "streaming": [
            "study playlist", "focus music", "campus tour",
            "student vlog", "productivity tips", "exam prep video",
            "college day in life", "dorm room tour",
        ],
    },
    "retiree": {
        "social": [
            "gardening tips", "yoga for beginners", "bird watching",
            "classical music", "cruise vacation reviews", "watercolor painting",
            "genealogy research", "book club recommendations",
            "bridge card game", "senior fitness", "volunteer opportunities",
            "knitting patterns", "antique collecting", "butterfly garden",
        ],
        "ecommerce": [
            "gardening tools", "yoga mat", "bird feeder",
            "watercolor paint set", "large print books", "walking shoes",
            "sun hat", "reading glasses", "heating pad",
            "raised garden bed", "comfortable sandals", "puzzle 1000 pieces",
            "tea sampler", "seed starter kit",
        ],
        "travel": [
            "Caribbean cruise", "Tuscany villa", "national park tour",
            "river cruise Europe", "Alaska cruise", "New England fall foliage",
            "Scottish Highlands tour",
        ],
        "streaming": [
            "gardening show", "classical concert", "nature documentary",
            "meditation guide", "BBC period drama", "piano tutorial",
            "travel documentary", "wildlife camera live",
        ],
    },
    "teenager": {
        "social": [
            "Fortnite clips", "NBA highlights", "anime edits",
            "Minecraft build", "Valorant montage", "Apex Legends tips",
            "skateboarding tricks", "memes compilation", "roblox funny moments",
            "TikTok dance challenge", "Among Us gameplay",
            "Demon Slayer review", "Attack on Titan ending",
        ],
        "ecommerce": [
            "gaming mouse", "anime figure", "basketball shoes",
            "RGB keyboard", "gaming headset", "poster wall decor",
            "LED strip lights", "Funko Pop collection", "phone case cool",
            "skateboard deck", "hoodie graphic", "energy drink",
        ],
        "travel": [
            "theme park tickets", "anime convention", "gaming convention",
            "water park", "skate park tour", "Disneyland",
        ],
        "streaming": [
            "gaming music", "NBA highlights", "anime opening songs",
            "Twitch streamer", "Fortnite live", "Minecraft speedrun",
            "skateboarding fails", "rap cypher", "reaction videos",
        ],
    },
}


# ── Types ────────────────────────────────────────────────────────────────────

class FarmResult(TypedDict):
    profile: str
    platform: str
    account_id: str
    url: str
    status: str
    duration_s: float
    screenshot_before: str
    screenshot_after: str
    search_terms: list[str]
    scroll_style: str
    error: str

class DailySummary(TypedDict):
    run_at: str
    total: int
    ok: int
    failed: int
    timeout: int
    blocked: int
    results: list[FarmResult]


# ── Per-platform search URL fallbacks ───────────────────────────────────────

_FALLBACK_SEARCH_URLS: dict[str, str] = {
    "pinterest":  "https://www.pinterest.com/search/pins/?q={q}",
    "tumblr":     "https://www.tumblr.com/search/{q}",
    "twitch":     "https://www.twitch.tv/search?term={q}",
    "reddit":     "https://www.reddit.com/search/?q={q}",
    "quora":      "https://www.quora.com/search?q={q}",
    "twitter":    "https://x.com/search?q={q}",
    "linkedin":   "https://www.linkedin.com/search/results/all/?keywords={q}",
    "amazon":     "https://www.amazon.com/s?k={q}",
    "ebay":       "https://www.ebay.com/sch/i.html?_nkw={q}",
    "aliexpress": "https://www.aliexpress.com/wholesale?SearchText={q}",
    "walmart":    "https://www.walmart.com/search?q={q}",
    "shopee":     "https://shopee.sg/search?keyword={q}",
    "booking":    "https://www.booking.com/searchresults.html?ss={q}",
    "expedia":    "https://www.expedia.com/Hotel-Search?destination={q}",
    "agoda":      "https://www.agoda.com/search?q={q}",
    "spotify":    "https://open.spotify.com/search/{q}",
    "youtube":    "https://www.youtube.com/results?search_query={q}",
}


# ── Core: farm one platform ─────────────────────────────────────────────────

async def farm_one(
    manager: ContextManager,
    profile: UserProfile,
    platform_key: PlatformName,
    search_terms: list[str],
) -> FarmResult:
    """Browse a single platform with a given profile. Captures before/after screenshots."""
    platform = PLATFORMS[platform_key]
    account_id = f"{profile.profile_id}_{platform_key}"
    start = datetime.now(timezone.utc)

    ss_dir = SCREENSHOT_DIR / profile.profile_id / platform_key
    ss_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ss_before = ss_dir / f"{ts}_before.png"
    ss_after = ss_dir / f"{ts}_after.png"

    result: FarmResult = {
        "profile": profile.profile_id,
        "platform": platform_key,
        "account_id": account_id,
        "url": platform.base_url,
        "status": "ok",
        "duration_s": 0,
        "screenshot_before": str(ss_before),
        "screenshot_after": str(ss_after),
        "search_terms": search_terms,
        "scroll_style": profile.scroll_style,
        "error": "",
    }

    try:
        ctx = await manager.create_context(account_id=account_id, platform=platform_key, profile=profile)
        page = await ctx.new_page()

        try:
            handler = get_handler(platform_key)

            if handler is not None:
                # ── Use platform-specific handler (knows the DOM) ──
                logger.info(f"  [{profile.display_name} → {platform.display_name}] Using {handler.__class__.__name__}")
                await page.screenshot(path=str(ss_before), full_page=False)

                # Per-action screenshot counter (mutable for closure)
                _action_seq = [0]

                async def on_action(item, action):
                    _action_seq[0] += 1
                    status_parts: list[str] = []
                    if action.clicked:
                        status_parts.append("viewed")
                    if action.liked:
                        status_parts.append("liked")
                    if action.commented:
                        status_parts.append("commented")
                    status = "_".join(status_parts) if status_parts else "interacted"
                    ss_path = ss_dir / f"{ts}_action{_action_seq[0]}_{status}.png"
                    try:
                        await page.screenshot(path=str(ss_path), full_page=False)
                        logger.debug(f"    Screenshot: {ss_path.name}")
                    except Exception:
                        pass

                handler.on_interact = on_action  # type: ignore[assignment]

                browse_result = await handler.browse(page, profile, ctx, max_interactions=5)
                result["status"] = "ok"
                result["search_terms"] = [f"handler: {browse_result.items_found} found, "
                                          f"{browse_result.items_viewed} viewed, "
                                          f"{browse_result.items_liked} liked"]
                logger.success(
                    f"  ✓ {profile.display_name} on {platform.display_name}: "
                    f"{browse_result.items_found} matched → "
                    f"{browse_result.items_viewed} viewed, "
                    f"{browse_result.items_liked} liked"
                )
            else:
                # ── Generic fallback: search + scroll ──
                logger.info(f"  [{profile.display_name} → {platform.display_name}] Loading {platform.base_url}")
                await page.goto(platform.base_url, wait_until="domcontentloaded", timeout=30_000)
                await think_pause(1.0, 3.0)
                await page.screenshot(path=str(ss_before), full_page=False)

                search_term = random.choice(search_terms)
                logger.info(f"    search: {search_term}")
                await _search(page, platform_key, search_term)
                await think_pause(1.5, 4.0)
                await scroll_like_human(page, random.randint(300, 1200), style=profile.scroll_style)

                result["status"] = "ok"
                logger.success(f"  ✓ {profile.display_name} on {platform.display_name}")

            await page.screenshot(path=str(ss_after), full_page=False)

        except asyncio.TimeoutError:
            result["status"] = "timeout"
            result["error"] = "page load timeout"
            logger.warning(f"  ⚠ {platform.display_name} timed out")
        finally:
            await page.close()

        await ctx.close()

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
        logger.error(f"  ✗ {platform.display_name}: {e}")

    result["duration_s"] = (datetime.now(timezone.utc) - start).total_seconds()
    return result


async def _search(page, platform_key: str, term: str) -> None:
    """Try to find and fill a search box; fall back to direct search URL."""
    selectors = [
        'input[type="search"]', 'input[name="q"]', 'input[name="query"]',
        'input[name="keyword"]', 'input[placeholder*="search" i]',
        'input[aria-label*="search" i]', 'textarea[placeholder*="search" i]',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible(timeout=2000):
                await loc.click()
                await think_pause(0.3, 0.8)
                await loc.fill(term)
                await think_pause(0.3, 0.6)
                await page.keyboard.press("Enter")
                return
        except Exception:
            continue

    tmpl = _FALLBACK_SEARCH_URLS.get(platform_key)
    if tmpl:
        try:
            await page.goto(tmpl.format(q=quote(term)), wait_until="domcontentloaded", timeout=20_000)
        except Exception:
            pass


# ── Summary ─────────────────────────────────────────────────────────────────

def save_summary(results: list[FarmResult]) -> DailySummary:
    ok = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "error")
    timeout = sum(1 for r in results if r["status"] == "timeout")
    blocked = sum(1 for r in results if r["status"] == "blocked")

    summary: DailySummary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "ok": ok,
        "failed": failed,
        "timeout": timeout,
        "blocked": blocked,
        "results": results,
    }
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


# ── Main ────────────────────────────────────────────────────────────────────

async def run_daily_farming(full: bool = True) -> DailySummary:
    profiles: list[UserProfile] = [
        TECH_ENTHUSIAST, FOOD_BLOGGER, TRAVELER,
        COLLEGE_STUDENT, RETIREE, TEENAGER,
    ]
    all_platforms: list[PlatformName] = list(PLATFORMS.keys())

    combos: list[tuple[UserProfile, PlatformName]]
    if full:
        combos = [(p, pk) for p in profiles for pk in all_platforms]
    else:
        _quick_map: dict[PlatformName, str] = {
            "pinterest":  "food_blogger",       "tumblr":     "teenager",
            "twitch":     "teenager",           "reddit":     "tech_enthusiast",
            "quora":      "tech_enthusiast",    "twitter":    "tech_enthusiast",
            "linkedin":   "tech_enthusiast",    "amazon":     "tech_enthusiast",
            "ebay":       "traveler",           "aliexpress": "college_student",
            "walmart":    "college_student",    "shopee":     "teenager",
            "booking":    "traveler",           "expedia":    "traveler",
            "agoda":      "traveler",           "spotify":    "college_student",
            "youtube":    "teenager",
        }
        combos = [(PROFILE_REGISTRY[_quick_map[pk]], pk) for pk in all_platforms]

    total = len(combos)
    logger.info("=" * 70)
    logger.info(f"Daily farming — {total} combinations")
    logger.info(f"Mode: {'Full (6×17)' if full else 'Quick (17)'}")
    logger.info(f"Evidence: {EVIDENCE_DIR.resolve()}")
    logger.info("=" * 70)

    results: list[FarmResult] = []

    async with ContextManager() as manager:
        for i, (profile, pk) in enumerate(combos):
            cat = platform_category(pk)
            terms = PROFILE_SEARCHES.get(profile.profile_id, {}).get(cat, ["trending"])
            logger.info(f"\n[{i + 1}/{total}] {profile.display_name} → {PLATFORMS[pk].display_name}")
            r = await farm_one(manager, profile, pk, terms)
            results.append(r)
            delay = random.uniform(3.0, 8.0) if full else random.uniform(1.0, 3.0)
            await asyncio.sleep(delay)

    summary = save_summary(results)
    logger.info(f"\n{'=' * 70}")
    logger.info(f"Complete: {summary['ok']}/{summary['total']} OK  |  "
                f"timeout={summary['timeout']}  fail={summary['failed']}  blocked={summary['blocked']}")
    logger.info(f"Report: {SUMMARY_FILE}")
    logger.info(f"Screenshots: {SCREENSHOT_DIR}")
    _print_per_platform(results)
    return summary


def _print_per_platform(results: list[FarmResult]) -> None:
    by: dict[str, dict[str, int]] = defaultdict(lambda: {"ok": 0, "fail": 0})
    for r in results:
        k = "ok" if r["status"] == "ok" else "fail"
        by[r["platform"]][k] += 1
    logger.info("\nBy platform:")
    for pk in PLATFORMS:
        s = by.get(pk, {"ok": 0, "fail": 0})
        total = s["ok"] + s["fail"]
        if total == 0:
            continue
        pct = s["ok"] / total * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        logger.info(f"  {PLATFORMS[pk].display_name:15s} {bar} {pct:.0f}% ({s['ok']}/{total})")


def main() -> None:
    quick = "--quick" in sys.argv
    logger.info(f"Mode: {'quick' if quick else 'full'}")
    asyncio.run(run_daily_farming(full=not quick))


if __name__ == "__main__":
    main()
