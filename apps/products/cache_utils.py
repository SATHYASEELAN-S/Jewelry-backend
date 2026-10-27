import logging
import random 
import time
import hashlib
from urllib.parse import urlencode

from django.core.cache import cache
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

LIST_VERSION_KEY = "products:list:version"
LIST_TTL = 60 * 15
DETAIL_TTL = 60 * 60

def safe_get(key, default=None):
    try:
        return cache.get(key, default)
    except RedisError:
        logger.warning("Cache read failed for %s", key, exc_info=True)
        return default
    
def safe_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except RedisError:
        logger.warning("Cache write failed for %s", key, exc_info=True)

def safe_delete(key):
    try:
        cache.delete(key)
    except RedisError:
        logger.warning("Cache delete failed for %s", key, exc_info=True)

def get_list_version():
    version = safe_get(LIST_VERSION_KEY)
    if version is None:
        version = time.time_ns()
        safe_set(LIST_VERSION_KEY, version, None)
    return version
 
def list_cache_key(request):
    params = sorted(
        (k,v) for k, values in request.query_params.lists() for v in values
    )
    digest = hashlib.sha256(urlencode(params).encode()).hexdigest()
     
    return f"products:list:v{get_list_version()}:{digest}"

def bump_list_version():
    safe_set(LIST_VERSION_KEY, time.time_ns(), None)
    
def with_jitter(ttl):
    # small random extra time so popular keys don't all expire together
    return ttl + random.randint(0,60)

def detail_cache_key(slug):
    return f"products:detail:{slug}"