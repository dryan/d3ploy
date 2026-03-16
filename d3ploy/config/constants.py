"""
Configuration constants.
"""

# Cache durations in seconds
NO_CACHE = 0
ONE_DAY = 86400
ONE_YEAR = 31536000

RECOMMENDED_CACHES = {
    "text/html": NO_CACHE,
    "text/css": ONE_YEAR,
    "text/javascript": ONE_YEAR,
    "application/json": ONE_YEAR,
    "application/manifest+json": ONE_DAY,
    "image/*": ONE_YEAR,
    "font/*": ONE_YEAR,
}
