"""
Platform handler registry.

Each platform handler is a subclass of PlatformHandler that knows
that platform's specific DOM structure and click patterns.

To add a new platform:
    1. Create platforms/{platform_key}.py
    2. Subclass PlatformHandler
    3. Decorate with @register_handler("platform_key")
    4. Import it here to trigger registration
"""

from platforms.base import (
    PlatformHandler,
    ContentItem,
    ActionResult,
    BrowseResult,
    get_handler,
    register_handler,
    list_handlers,
)

# Import handlers to trigger @register_handler decorators
from platforms import reddit  # noqa: F401

__all__ = [
    "PlatformHandler",
    "ContentItem",
    "ActionResult",
    "BrowseResult",
    "get_handler",
    "register_handler",
    "list_handlers",
]
