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
from platforms import reddit      # noqa: F401
from platforms import pinterest   # noqa: F401
from platforms import tumblr      # noqa: F401
from platforms import quora       # noqa: F401
from platforms import twitter     # noqa: F401
from platforms import linkedin    # noqa: F401
from platforms import twitch      # noqa: F401
from platforms import amazon      # noqa: F401
from platforms import ebay        # noqa: F401
from platforms import aliexpress  # noqa: F401
from platforms import walmart     # noqa: F401
from platforms import shopee      # noqa: F401
from platforms import booking     # noqa: F401
from platforms import expedia     # noqa: F401
from platforms import agoda       # noqa: F401
from platforms import spotify     # noqa: F401
from platforms import youtube     # noqa: F401

__all__ = [
    "PlatformHandler",
    "ContentItem",
    "ActionResult",
    "BrowseResult",
    "get_handler",
    "register_handler",
    "list_handlers",
]
