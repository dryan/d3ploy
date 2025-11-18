"""
Configuration constants.
"""

RECOMMENDED_CACHES = {
    "text/html": 0,
    "application/json": 0,
    "application/xml": 0,
    "text/xml": 0,
    "image/x-icon": 86400,  # 1 day
    "default": 31536000,  # 1 year for everything else (assuming hashed filenames)
}
