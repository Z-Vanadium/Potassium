"""
Entry point — demonstrates the framework end-to-end.

Usage:
    uv run main.py

What it does:
    1. Launches a shared Chromium browser
    2. Creates isolated contexts for 2 accounts on different platforms
    3. Applies unique fingerprints & stealth patches per account
    4. Demonstrates human-like browsing behavior
    5. Persists sessions for resumption
"""

import asyncio
from pathlib import Path
from typing import TypedDict

from loguru import logger

from config.profiles import TECH_ENTHUSIAST, COLLEGE_STUDENT, UserProfile
from config.settings import PlatformName
from core.context_manager import ContextManager
from core.human_behavior import random_scroll_behavior
from core.stealth import verify_stealth

# ── Config: which accounts to demo ──────────────────────────────────────────


class DemoAccount(TypedDict):
    account_id: str
    platform: PlatformName
    profile: UserProfile


# In production, this would come from accounts/*.json config files
DEMO_ACCOUNTS: list[DemoAccount] = [
    {
        "account_id": "tech_zhihu_01",
        "platform": "zhihu",
        "profile": TECH_ENTHUSIAST,
    },
    {
        "account_id": "student_bilibili_01",
        "platform": "bilibili",
        "profile": COLLEGE_STUDENT,
    },
]


async def demo_context_isolation() -> None:
    """
    Create two isolated contexts with different fingerprints on different
    platforms, run basic diagnostics, and verify stealth.
    """
    logger.info("=" * 60)
    logger.info("Framework Demo: Account Isolation + Anti-Fingerprinting")
    logger.info("=" * 60)

    async with ContextManager() as manager:
        contexts = []

        for cfg in DEMO_ACCOUNTS:
            ctx = await manager.create_context(
                account_id=cfg["account_id"],
                platform=cfg["platform"],
                profile=cfg["profile"],
            )
            contexts.append(ctx)

        # ── Verify isolation ──
        for ctx in contexts:
            page = await ctx.new_page()

            # Check fingerprint uniqueness
            fp_info = await page.evaluate("""
                () => ({
                    userAgent: navigator.userAgent.substring(0, 80),
                    platform: navigator.platform,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    deviceMemory: navigator.deviceMemory,
                    language: navigator.language,
                    webdriver: navigator.webdriver,
                    plugins: navigator.plugins.length,
                    chrome: typeof window.chrome !== 'undefined',
                })
            """)

            logger.info(
                f"\n  [{ctx.account_id}] Fingerprint:"
                f"\n    UA:       {fp_info['userAgent']}..."
                f"\n    Platform: {fp_info['platform']}"
                f"\n    CPU:      {fp_info['hardwareConcurrency']} cores"
                f"\n    Memory:   {fp_info['deviceMemory']} GB"
                f"\n    Locale:   {fp_info['language']}"
                f"\n    Plugins:  {fp_info['plugins']}"
                f"\n    Chrome:   {fp_info['chrome']}"
                f"\n    WebDriver:{fp_info['webdriver']}"
            )

            # Verify stealth efficacy
            stealth_status = await verify_stealth(page)
            passed = sum(1 for v in stealth_status.values() if v)
            total = len(stealth_status)
            logger.info(f"    Stealth:  {passed}/{total} checks passed")
            for check, ok in stealth_status.items():
                logger.info(f"      {check}: {'PASS' if ok else 'FAIL'}")

            await page.close()

        # ── Simulate browsing on one account ──
        logger.info("\n" + "-" * 40)
        logger.info("Simulating human-like browsing...")

        ctx = contexts[0]  # tech_zhihu_01
        page = await ctx.new_page()

        try:
            # Navigate to platform home
            await page.goto(ctx.platform.base_url, wait_until="domcontentloaded", timeout=15000)
            logger.info(f"Loaded {ctx.platform.display_name}")

            # Wait to appear human
            await asyncio.sleep(2.0)

            # Simulate feed browsing
            logger.info("Performing scroll session...")
            await random_scroll_behavior(page, style=ctx.profile.scroll_style)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout loading {ctx.platform.display_name} — skipping browse demo")
        except Exception as e:
            logger.warning(f"Browse demo interrupted: {e} — framework core is functional")

        finally:
            await page.close()

        # ── Save all sessions & close ──
        logger.info("\n" + "-" * 40)
        logger.info("Persisting sessions...")

        for ctx in contexts:
            await ctx.close()
            logger.info(f"Session saved: {ctx.storage_path}")

        logger.info("\n✓ Demo complete. Profiles saved to profiles/ directory.")


# ── CLI ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the framework demo."""
    # Check if storage states exist from previous sessions
    storage_files = list(Path("profiles").glob("*.json"))
    if storage_files:
        logger.info(f"Found {len(storage_files)} existing session(s) in profiles/")

    asyncio.run(demo_context_isolation())


if __name__ == "__main__":
    main()
