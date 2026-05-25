"""
Per-account fingerprint management.

Generates and applies unique browser fingerprints for each isolated
BrowserContext. This prevents platforms from correlating accounts
via device-level signals (Canvas, WebGL, AudioContext, etc.).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from config.profiles import UserProfile


@dataclass
class Fingerprint:
    """A complete browser fingerprint configuration."""

    user_agent: str
    viewport: dict[str, int]
    locale: str
    timezone_id: str
    webgl_vendor: str
    webgl_renderer: str
    platform: str
    hardware_concurrency: int
    device_memory: int
    color_depth: int
    screen: dict[str, int]
    device_scale_factor: float
    is_mobile: bool
    has_touch: bool

    # Geoloaction (null = disabled)
    latitude: float | None = None
    longitude: float | None = None

    # Extra HTTP headers to inject
    accept_language: str = "zh-CN,zh;q=0.9,en;q=0.8"
    sec_ch_ua: str = (
        '"Chromium";v="135", "Not-A.Brand";v="24", "Google Chrome";v="135"'
    )
    sec_ch_ua_platform: str = '"Windows"'
    sec_ch_ua_mobile: str = "?0"

    @classmethod
    def from_profile(cls, profile: UserProfile) -> Fingerprint:
        """Build a Fingerprint from a UserProfile definition."""
        return cls(
            user_agent=profile.user_agent,
            viewport={"width": profile.viewport[0], "height": profile.viewport[1]},
            locale=profile.locale,
            timezone_id=profile.timezone,
            webgl_vendor=profile.webgl_vendor,
            webgl_renderer=profile.webgl_renderer,
            platform=profile.platform,
            hardware_concurrency=profile.hardware_concurrency,
            device_memory=profile.device_memory,
            color_depth=profile.color_depth,
            screen={"width": profile.screen_width, "height": profile.screen_height},
            device_scale_factor=profile.device_scale_factor,
            is_mobile=profile.is_mobile,
            has_touch=profile.has_touch,
            accept_language=_build_accept_language(profile.locale),
            sec_ch_ua_platform=_platform_to_sec_ch(profile.platform),
            sec_ch_ua_mobile="?1" if profile.is_mobile else "?0",
        )


# ── Helpers ─────────────────────────────────────────────────────────────────


def _build_accept_language(locale: str) -> str:
    """Build Accept-Language header from locale."""
    primary = locale.replace("_", "-").split("-")[0]
    if primary == "zh":
        return "zh-CN,zh;q=0.9,en;q=0.7"
    return "en-US,en;q=0.9"


def _platform_to_sec_ch(platform: str) -> str:
    """Map navigator.platform to Sec-CH-UA-Platform."""
    mapping = {
        "Win32": '"Windows"',
        "MacIntel": '"macOS"',
        "iPhone": '"iOS"',
        "Linux x86_64": '"Linux"',
    }
    return mapping.get(platform, f'"{platform}"')


# ── Fingerprint generator (randomized) ──────────────────────────────────────


_WEBGL_VENDORS = [
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)"),
    ("Apple Inc.", "Apple M2"),
    ("Apple Inc.", "Apple M3"),
    ("Apple Inc.", "Apple GPU"),
]

_UAS_WINDOWS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]

_UAS_MAC = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
]


def generate_random_fingerprint() -> Fingerprint:
    """Generate a randomized desktop fingerprint."""
    is_mac = random.random() < 0.3
    vendor, renderer = random.choice(_WEBGL_VENDORS)
    ua = random.choice(_UAS_MAC if is_mac else _UAS_WINDOWS)

    return Fingerprint(
        user_agent=ua,
        viewport={"width": random.choice([1366, 1440, 1536, 1920]),
                   "height": random.choice([768, 900, 864, 1080])},
        locale=random.choice(["zh-CN", "zh-CN", "zh-CN", "en-US"]),  # biased toward Chinese
        timezone_id=random.choice(["Asia/Shanghai", "Asia/Shanghai", "Asia/Shanghai",
                                    "Asia/Tokyo", "America/Los_Angeles"]),
        webgl_vendor=vendor,
        webgl_renderer=renderer,
        platform="MacIntel" if is_mac else "Win32",
        hardware_concurrency=random.choice([4, 8, 12, 16]),
        device_memory=random.choice([4, 8, 8, 16]),
        color_depth=24,
        screen={"width": random.choice([1920, 2560]),
                 "height": random.choice([1080, 1440, 1600])},
        device_scale_factor=random.choice([1.0, 1.25, 1.5, 2.0]),
        is_mobile=False,
        has_touch=False,
        accept_language="zh-CN,zh;q=0.9,en;q=0.7",
        sec_ch_ua='"Chromium";v="135", "Not-A.Brand";v="24", "Google Chrome";v="135"',
        sec_ch_ua_platform='"Windows"' if not is_mac else '"macOS"',
        sec_ch_ua_mobile="?0",
    )
