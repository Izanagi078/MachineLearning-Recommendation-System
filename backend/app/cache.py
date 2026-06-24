"""
cache.py — In-memory LRU cache layer with TTL support and selective invalidation.
Provides thread-safe decorators for FastAPI routers.
"""
import time
import functools
import threading
from collections import OrderedDict

class SimpleLRUCache:
    def __init__(self, maxsize=128, ttl=300):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            val, expiry = self.cache[key]
            if time.time() > expiry:
                del self.cache[key]
                return None
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return val

    def set(self, key, value):
        with self.lock:
            expiry = time.time() + self.ttl
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.maxsize:
                # Evict oldest (least recently used)
                self.cache.popitem(last=False)
            self.cache[key] = (value, expiry)

    def clear(self):
        with self.lock:
            self.cache.clear()

# Global cache registry for invalidating by namespace
_registries = {}

def cache_dec(name, maxsize=128, ttl=300):
    """
    Thread-safe LRU Cache decorator with TTL.
    Ignores non-hashable arguments like request or db sessions to prevent crashes.
    """
    if name not in _registries:
        _registries[name] = SimpleLRUCache(maxsize=maxsize, ttl=ttl)
    
    cache = _registries[name]
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build key from hashable arguments only
            # Skip FastAPI-specific request object or SQLAlchemy db session
            hashable_args = []
            for arg in args:
                # Skip request (has 'scope' attribute) or SQLAlchemy DB Session (has 'bind' attribute)
                if hasattr(arg, "scope") or hasattr(arg, "bind"):
                    continue
                hashable_args.append(arg)
                
            hashable_kwargs = {}
            for k, v in kwargs.items():
                if k in ("request", "db"):
                    continue
                hashable_kwargs[k] = v
                
            key = (tuple(hashable_args), tuple(sorted(hashable_kwargs.items())))
            
            cached_val = cache.get(key)
            if cached_val is not None:
                return cached_val
            
            val = func(*args, **kwargs)
            cache.set(key, val)
            return val
        return wrapper
    return decorator

def invalidate_cache(name):
    """Clears all entries in a specific cache namespace."""
    if name in _registries:
        _registries[name].clear()

def invalidate_all_caches():
    """Clears all entries across all cache namespaces."""
    for cache in _registries.values():
        cache.clear()
