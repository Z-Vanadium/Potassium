# Potassium — Multi-Platform Social Account Farming Framework

Browser automation framework for building differentiated user profiles across **17 international platforms**. Each account gets an isolated browser context with unique fingerprint, stealth patches, and human-like behavior. Supports a pluggable per-platform handler architecture for DOM-specific content interaction.

---

## Quick Start

```bash
# Prerequisites: Python 3.12+
pip install uv

# Clone & install
git clone git@github.com:Z-Vanadium/Potassium.git
cd Potassium
uv sync
uv run playwright install chromium

# Run the daily farming script (quick mode: 17 combos)
uv run python daily_farming.py --quick

# Full mode: 6 profiles × 17 platforms = 102 combinations
uv run python daily_farming.py
```

---

## Concepts

| Concept | What it is | In this project |
|---------|-----------|----------------|
| **Browser** | One Chromium process | Shared across all accounts |
| **Context** | Isolated browser session | **One per account** — independent cookies, fingerprint, storage |
| **Page** | A browser tab | Each Context opens its own Pages |
| **Fingerprint** | Device signals sent to websites | Per-account: UA, viewport, WebGL, CPU cores, timezone, locale |
| **Profile** | Complete persona definition | Interests, device, behavior params, activity patterns |
| **Handler** | Per-platform DOM interaction logic | Knows each site's specific HTML structure |

Analogy: Each account = a different person using a different computer in a different city.

---

## Project Structure

```
├── config/
│   ├── settings.py          # 17 platforms, rate limits, browser defaults
│   └── profiles.py          # 6 user profiles (persona definitions)
├── core/
│   ├── stealth.py           # Anti-detection patches (webdriver, plugins, CDP)
│   ├── fingerprint.py       # Per-account device fingerprint
│   ├── human_behavior.py    # Typing, mouse, scroll simulation
│   └── context_manager.py   # BrowserContext factory + session isolation
├── platforms/               # Per-platform DOM handlers (callback architecture)
│   ├── base.py              # Abstract PlatformHandler + callback interface
│   ├── reddit.py            # Reddit: shreddit-post → find → click → vote
│   └── __init__.py          # Registry: get_handler("reddit")
├── daily_farming.py         # Main automation: 6×17 daily farming script
├── main.py                  # Demo: stealth verification + fingerprint check
├── profiles/                # Persistent browser sessions (auto-saved)
└── evidence/                # Screenshots + JSON summary (runtime output)
```

---

## 6 Built-in Profiles

| Profile | Persona | Device | Interests | Behavior |
|---------|---------|--------|-----------|----------|
| `tech_enthusiast` | Tech Enthusiast | Windows / NVIDIA RTX 3060 | AI, Rust, open source, startups | Fast reader, 25% like, weekly posts |
| `food_blogger` | Food Blogger | iPhone | Recipes, baking, coffee, Italian food | Slow reader, 45% like, heavy emoji |
| `traveler` | Travel Enthusiast | MacBook / M3 | Hiking, Japan, Patagonia, nomad life | Normal pace, 35% like |
| `college_student` | College Student | Windows / AMD RX 6600 | GRE, internships, dorm hacks, playlists | Very fast, 40% like, 3-5 sessions/day |
| `retiree` | Retiree | iPad / A12Z | Gardening, yoga, classical music, birding | Reader mode, 15% like, 25% share |
| `teenager` | Teenager | Windows / AMD RX 6500XT | Fortnite, NBA, anime, Valorant, memes | Very fast, 55% like, heavy emoji, 2-4h sessions |

Usage: `from config.profiles import TECH_ENTHUSIAST, RETIREE`

---

## 17 International Platforms

| Category | Platform | Key | Base URL |
|----------|----------|-----|----------|
| Social | Pinterest | `pinterest` | pinterest.com |
| Social | Tumblr | `tumblr` | tumblr.com |
| Social | Reddit | `reddit` | reddit.com |
| Social | Quora | `quora` | quora.com |
| Social | X / Twitter | `twitter` | x.com |
| Social | LinkedIn | `linkedin` | linkedin.com |
| Streaming | Twitch | `twitch` | twitch.tv |
| E-commerce | Amazon | `amazon` | amazon.com |
| E-commerce | eBay | `ebay` | ebay.com |
| E-commerce | AliExpress | `aliexpress` | aliexpress.com |
| E-commerce | Walmart | `walmart` | walmart.com |
| E-commerce | Shopee | `shopee` | shopee.sg |
| Travel | Booking.com | `booking` | booking.com |
| Travel | Expedia | `expedia` | expedia.com |
| Travel | Agoda | `agoda` | agoda.com |
| Streaming | Spotify | `spotify` | open.spotify.com |
| Streaming | YouTube | `youtube` | youtube.com |

---

## Handler Architecture (Callback Pattern)

Each platform can have a dedicated handler that knows its specific DOM structure. The handler finds content matching the profile's interests and interacts with it — clicking, voting, commenting.

### How it works

```python
from platforms import get_handler

handler = get_handler("reddit")  # Returns RedditHandler or None

if handler:
    # Optional: set callbacks
    handler.on_content_found = lambda item: print(f"Found: {item.title}")
    handler.on_interact = lambda item, action: print(f"Liked: {action.liked}")

    # Browse + interact
    result = await handler.browse(page, profile, account_ctx)
    # → Finds posts matching interests, clicks them, upvotes, returns summary
else:
    # Fallback: generic search + scroll
    ...
```

### Built-in handler: Reddit

```
RedditHandler (platforms/reddit.py)
│
├── before_browse()     → Navigate to r/Python, r/Baking, etc. based on profile interests
├── find_content()      → Scan <shreddit-post> elements, extract titles, score vs profile.interests
├── should_engage()     → relevance ≥ 0.5 required; then probability = like_probability + score × 0.4
└── interact()          → Click title → load post → scroll (profile.reading_multiplier)
                           → dice-roll upvote (profile.like_probability)
                           → dice-roll comment (profile.comment_probability)
                           → navigate back to feed
```

### Adding a new handler

```python
# platforms/amazon.py
from platforms.base import PlatformHandler, register_handler

@register_handler("amazon")
class AmazonHandler(PlatformHandler):
    def _get_selectors(self):
        return {"product_card": "[data-component-type='s-search-result']",
                "product_title": "h2 a span"}

    async def find_content(self, page, profile):
        ...  # Scan product cards, match titles against profile.interests

    async def interact(self, page, item, profile):
        ...  # Click product → view details → optionally add to wishlist
```

Then import in `platforms/__init__.py`: `from platforms import amazon`. The `@register_handler` decorator auto-registers it.

---

## Abstract Handler Interface

```python
class PlatformHandler(ABC):
    # ── Must implement ──
    async def find_content(self, page, profile) -> list[ContentItem]: ...
    async def interact(self, page, item, profile) -> ActionResult: ...
    def _get_selectors(self) -> dict[str, str]: ...

    # ── Optional hooks ──
    async def before_browse(self, page, profile): ...
    async def after_browse(self, page, profile, result): ...
    def should_engage(self, item, profile) -> bool: ...

    # ── Callbacks (set by caller) ──
    on_content_found: ContentCallback | None
    on_interact: ActionResultCallback | None

    # ── Orchestrator ──
    async def browse(self, page, profile, ctx, max_interactions=5) -> BrowseResult: ...

    # ── Shared utilities ──
    @staticmethod match_interests(text, interests) -> list[tuple[str, float]]
    @staticmethod safe_click(page, selector) -> bool
    @staticmethod safe_get_text(page, selector) -> str
```

---

## Core Modules

### Stealth (`core/stealth.py`)

Applied automatically before any navigation. Patches:
- `navigator.webdriver` → `undefined`
- `window.chrome` → present with native-looking runtime
- `navigator.plugins` → 3 fake plugins (Chrome PDF, etc.)
- `navigator.mimeTypes` → normal browser MIME types
- iFrame contentWindow detection → blocked
- CDP `Runtime.enable` traces → hidden

### Human Behavior (`core/human_behavior.py`)

| Function | Purpose |
|----------|---------|
| `human_delay(min, max)` | Gamma-distributed random pause |
| `type_like_human(page, text)` | Natural typing with typos + correction |
| `move_mouse_to(page, x, y)` | Bezier-curve mouse movement |
| `click_like_human(page, selector)` | Move mouse → random position within element → click |
| `scroll_like_human(page, px, style)` | Style-based scrolling with pauses and re-reads |
| `random_scroll_behavior(page, style)` | Multi-viewport casual browsing session |

### Session Isolation (`core/context_manager.py`)

```python
async with ContextManager() as manager:
    ctx = await manager.create_context(
        account_id="tech_reddit_01",
        platform="reddit",
        profile=TECH_ENTHUSIAST,
    )
    page = await ctx.new_page()
    # ... browse, interact ...
    await ctx.close()  # auto-saves cookies to profiles/
```

Each `AccountContext` tracks: action counters, rate limits, session duration.

---

## Configuration

### Rate limits (`config/settings.py`)

```python
GLOBAL_DAILY_ACTION_CAP = 500   # across all accounts
ACTIVE_HOURS_START = 8          # 8 AM
ACTIVE_HOURS_END = 23           # 11 PM

# Per-platform (example):
PlatformConfig(daily_like_limit=30, daily_comment_limit=8, ...)
```

### Proxy

```python
PROXY_SERVER = "http://user:pass@proxy.example.com:8080"
```

### Adding a platform

1. Add to `PlatformName` Literal in `config/settings.py`
2. Add `PlatformConfig` entry in `PLATFORMS` dict
3. Add to `platform_category()` map
4. (Optional) Create `platforms/{key}.py` handler

---

## Evidence

Each run generates:
- `evidence/screenshots/{profile}/{platform}/` — before/after PNGs per session
- `evidence/summary.json` — per-combo results with status, duration, search terms

---

## FAQ

**How does it prove browsing was recorded?** Even without login, platforms track page views, search queries, scroll depth, and dwell time via cookies. The framework saves these cookies in `profiles/`, so repeated sessions create persistent anonymous profiles.

**Does headless mode work?** It works but reduces stealth efficacy. Default is `headless=False` (visible browser window).

**How do I log in?** Run the framework once with `headless=False`, manually log in, then close. The framework auto-saves the session. Next run restores it.

**Will my accounts get banned?** Risk exists. Mitigations: use headful mode, respect daily limits, spread actions across hours, use different fingerprints per account, and don't run 24/7. This project is for educational purposes only.
