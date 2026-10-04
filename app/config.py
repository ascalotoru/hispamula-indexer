import os


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


BASE_URL = _env("HISPAMULA_BASE_URL", "https://www.hispamula.org")
USERNAME = _env("HISPAMULA_USER", "")
PASSWORD = _env("HISPAMULA_PASSWORD", "")

REQUEST_DELAY = float(_env("HISPAMULA_REQUEST_DELAY", "1.0"))
CACHE_TTL = int(_env("HISPAMULA_CACHE_TTL", "600"))
TIMEOUT = float(_env("HISPAMULA_TIMEOUT", "30.0"))
USER_AGENT = _env("HISPAMULA_USER_AGENT", "hispamula-indexer/0.1")

# Máximo de títulos procesados por búsqueda (evita N+1 desbocado).
MAX_RESULTS = int(_env("HISPAMULA_MAX_RESULTS", "25"))
