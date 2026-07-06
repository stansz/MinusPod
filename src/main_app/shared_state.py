"""Shared mutable state for main_app sub-modules.

Provides module-level containers that multiple main_app modules need to share
(e.g. log-dedup sets that were a single object in the original monolith,
episode lookup caching for fork HEAD-proxy paths).
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Hashable

from main_app.cache import TTLCache


class _BoundedSet:
    """Thread-safe set with a fixed upper bound. Evicts the oldest entry
    when the capacity would be exceeded.

    Used for log-dedup sets so a long-running worker cannot grow the set
    unboundedly (one entry per distinct episode permanently-failed).
    """

    def __init__(self, maxsize: int) -> None:
        self._maxsize = maxsize
        self._order: OrderedDict[Hashable, None] = OrderedDict()
        self._lock = threading.Lock()

    def __contains__(self, key: Hashable) -> bool:
        with self._lock:
            return key in self._order

    def add(self, key: Hashable) -> None:
        with self._lock:
            if key in self._order:
                self._order.move_to_end(key)
                return
            self._order[key] = None
            while len(self._order) > self._maxsize:
                self._order.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._order)


# Track episodes already warned about permanent failure (avoid log spam on
# repeated requests). Shared across routes.py and processing.py so the dedup
# works across both code paths. Bounded so a worker that serves a very large
# library cannot grow the set unboundedly.
permanently_failed_warned = _BoundedSet(maxsize=10_000)

# In-memory cache for _lookup_episode results to avoid re-fetching upstream
# RSS on every HEAD request. Uses a thread-safe TTLCache so concurrent
# requests under gunicorn's gthread workers cannot corrupt dict state.
# Key: "slug:episode_id". Value: (episode_dict, podcast_name).
# TTL is 15 minutes (900s), matching the background RSS refresh interval.
episode_lookup_cache = TTLCache(ttl_seconds=900)


def invalidate_episode_lookup_cache(slug: str = None, episode_id: str = None) -> None:
    """Invalidate cached episode lookups.

    Called after RSS refresh so a feed that changed upstream URLs does
    not serve stale enclosures from the cache for the TTL window.
    """
    if slug is None and episode_id is None:
        episode_lookup_cache.invalidate()
        return
    key = f"{slug}:{episode_id}"
    episode_lookup_cache.invalidate(key)
