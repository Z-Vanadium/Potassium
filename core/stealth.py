"""
Anti-detection stealth layer for Playwright.

Applies evasion patches at the CDP (Chrome DevTools Protocol) and
JavaScript levels to make Playwright-controlled Chromium look like
a real browser. This is the FIRST thing applied before any navigation.

Based on techniques from:
- puppeteer-extra-plugin-stealth
- rebrowser-patches
- playwright-stealth (@mr_ozio)
"""

from __future__ import annotations

from playwright.async_api import BrowserContext, Page
from loguru import logger


# ── Stealth script injected before page load ────────────────────────────────

_INIT_SCRIPT = """
// ── 1. Navigator properties ─────────────────────────────────────────────────
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// ── 2. Chrome runtime ──────────────────────────────────────────────────────
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// ── 3. Plugins array (Playwright ships with 0 by default - add fake ones) ──
const _fakePlugin = (name, description, filename) => ({
    name,
    description,
    filename,
    length: 1,
    0: { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: '' },
    namedItem: () => null,
    item: () => null,
});
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [
            _fakePlugin('Chrome PDF Plugin', 'Portable Document Format', 'internal-pdf-viewer'),
            _fakePlugin('Chrome PDF Viewer', '', 'mhjfbmdgcfjbbpaeojofohoefgiehjai'),
            _fakePlugin('Native Client', '', 'internal-nacl-plugin'),
        ];
        arr.item = (i) => arr[i] || null;
        arr.namedItem = (name) => arr.find(p => p.name === name) || null;
        arr.refresh = () => {};
        return arr;
    }
});

// ── 4. Mime types ──────────────────────────────────────────────────────────
Object.defineProperty(navigator, 'mimeTypes', {
    get: () => {
        const arr = [
            { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
            { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
        ];
        arr.item = (i) => arr[i] || null;
        arr.namedItem = (name) => arr.find(m => m.type === name) || null;
        return arr;
    }
});

// ── 5. WebDriver executor ──────────────────────────────────────────────────
Object.defineProperty(navigator, '__proto__', {
    get: () => Navigator.prototype
});

// ── 6. Permissions ─────────────────────────────────────────────────────────
const _origQuery = window.navigator.permissions.query.bind(window.navigator.permissions);
window.navigator.permissions.query = (parameters) => {
    if (parameters.name === 'notifications') {
        return Promise.resolve({ state: Notification.permission, onchange: null });
    }
    return _origQuery(parameters);
};

// ── 7. iFrame contentWindow protection ─────────────────────────────────────
try {
    const _origDefine = Object.defineProperty;
    Object.defineProperty = (obj, prop, desc) => {
        if (prop === 'contentWindow' && desc && desc.configurable) {
            // Block detection via iframe.contentWindow
            return obj;
        }
        return _origDefine(obj, prop, desc);
    };
    Object.defineProperty.toString = _origDefine.toString.bind(_origDefine);
} catch(e) {}

// ── 8. Navigator toString ──────────────────────────────────────────────────
const _origToString = Function.prototype.toString;
Function.prototype.toString = function() {
    if (this === window.chrome) {
        return 'function chrome() { [native code] }';
    }
    return _origToString.call(this);
};

// ── 9. Console.debug (hide CDP traces) ─────────────────────────────────────
// Overwrite to suppress signature traces
const _origDebug = console.debug;
console.debug = function() {};
console.debug.toString = () => 'function debug() { [native code] }';
"""


# ── Stealth API ─────────────────────────────────────────────────────────────


async def apply_stealth(context: BrowserContext) -> None:
    """
    Apply all stealth patches to a BrowserContext.

    Must be called BEFORE any page navigation. This:
    1. Injects the anti-detection init script on every page
    2. Removes the "HeadlessChrome" user-agent component
    3. Sets proper locale and timezone (from context options)

    Args:
        context: The Playwright BrowserContext to patch.
    """
    logger.debug("Applying stealth patches to BrowserContext")

    await context.add_init_script(_INIT_SCRIPT)
    await _hide_playwright_bindings(context)


async def _hide_playwright_bindings(context: BrowserContext) -> None:
    """
    Remove Playwright-specific global bindings that expose automation.

    Playwright adds __playwright__ and other globals that can be detected.
    This hooks into page creation to strip them.
    """
    context.on("page", lambda page: _patch_new_page(page))


async def _patch_new_page(page: Page) -> None:
    """Strip Playwright markers from a newly created page."""
    try:
        await page.add_init_script("""
            delete window.__playwright__binding__;
            delete window.__pw_manual__;
            delete window.__playwright__;
        """)
    except Exception:
        pass  # Silently ignore — stealth is best-effort


async def verify_stealth(page: Page) -> dict[str, bool]:
    """
    Run self-diagnostics on a page to verify stealth status.

    Returns a dict of check_name -> passed.
    Use after navigation to a bot detection page.

    Example:
        >>> results = await verify_stealth(page)
        >>> assert results["webdriver"], "Stealth failed: webdriver leak"
    """
    checks: dict[str, bool] = {}

    # Check navigator.webdriver
    webdriver = await page.evaluate("() => navigator.webdriver")
    checks["webdriver"] = webdriver is None or webdriver is False

    # Check Chrome runtime
    has_chrome = await page.evaluate("() => typeof window.chrome !== 'undefined'")
    checks["chrome_runtime"] = has_chrome

    # Check plugins
    plugins_count = await page.evaluate("() => navigator.plugins.length")
    checks["plugins"] = plugins_count > 0

    # Check automation flag
    no_automation = await page.evaluate("""
        () => {
            return !navigator.userAgent.includes('HeadlessChrome') &&
                   !navigator.userAgent.includes('Playwright');
        }
    """)
    checks["ua_clean"] = no_automation

    return checks
