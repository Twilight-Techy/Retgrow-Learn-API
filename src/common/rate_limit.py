# src/common/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory storage (resets on restart).
# For production with multiple workers, switch to Redis:
#   limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
